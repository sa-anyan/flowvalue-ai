"""Sole annual financial engine: explicit upstream schedules -> one ledger -> metrics."""

from dataclasses import replace
from decimal import Decimal, DecimalException, localcontext

from .assumptions.calculator import money_at, value
from .capital_investment.calculator import capital_schedule
from .cash_flow.calculator import cash_flows, discount
from .depreciation.calculator import asset_schedule
from .financial_schedules.calculator import build_timeline
from .financing.calculator import debt_schedule, dscr
from .investment_metrics.calculator import calculate_metrics
from .models import AnnualLedger, FinancialInputs, FinancialResult, Money
from .operating_costs.calculator import calculate_costs
from .profit_loss.calculator import profit_loss
from .reconciliation.validator import reconcile
from .taxation.calculator import calculate_tax
from .validation.validator import validate
from .working_capital.calculator import working_capital_schedule

ZERO = Decimal(0)


def calculate_financials(inputs):
    if not isinstance(inputs, FinancialInputs):
        raise TypeError("FinancialInputs required")
    from .registry import get_model
    from .snapshots import freeze_inputs, snapshot_id

    model = get_model(inputs.model_id)
    with localcontext() as context:
        context.prec = 40
        errors = validate(inputs)
        warnings = [
            "Preliminary annual model; cash spending is at explicit year points; dates prorate active production only. Tax/depreciation policies require jurisdictional review.",
            "Construction interest is paid/expensed, not rolled into debt or capitalized; one non-revolving term facility supported.",
            "Selected depreciation is shared by book and tax in this preliminary model; separate book/tax bases and deferred taxes are not implemented.",
        ]
        if inputs.assumptions.debt.equity_mode == "residual_equity":
            warnings.append(
                "Residual equity funding is an explicit unlimited-funding assumption, not a financing commitment."
            )
        try:
            ledger = () if errors else _ledger(inputs, warnings)
            if ledger:
                errors = reconcile(ledger)
            metrics = () if errors else calculate_metrics(ledger, inputs.assumptions)
        except (
            ValueError,
            TypeError,
            KeyError,
            DecimalException,
            OverflowError,
        ) as exc:
            errors = tuple(errors) + (str(exc),)
            ledger = ()
            metrics = ()
        return FinancialResult(
            inputs.model_id,
            snapshot_id(inputs),
            "needs_review" if errors else "calculated_preliminary",
            ledger if not errors else (),
            metrics,
            tuple(errors),
            tuple(dict.fromkeys(warnings)),
            freeze_inputs(inputs),
            (model["source"],) + inputs.source_references,
            inputs.assumptions.currency,
            inputs.assumptions.price_mode,
            inputs.assumptions.financial_base_year,
            inputs.assumptions.discount_convention,
        )


def _ledger(inputs, warnings):
    a = inputs.assumptions
    periods = build_timeline(a)
    capital, capital_totals = capital_schedule(inputs.capital, periods, a)
    assets = {
        item.id: asset_schedule(
            item,
            ZERO
            if item.kind == "startup" and item.startup_treatment == "expensed"
            else capital_totals[item.id],
            periods,
            a,
        )
        for item in inputs.capital
    }
    wc = working_capital_schedule(a.working_capital, periods, a)
    debts = debt_schedule(a.debt, periods, a)
    operations = {o.year: o for o in inputs.operations}
    tax_rates = dict(a.tax.annual_rates)
    specified = {
        x.year: money_at(x.money, periods[x.year].calendar_year, a)
        for x in a.debt.equity_contributions
    }
    project_lots, equity_lots = (), ()
    rows = []
    project_cumulative = ZERO
    equity_cumulative = ZERO
    for period in periods:
        y = period.year
        operation = operations.get(y)
        products = operation.products if operation else ()
        products = tuple(
            replace(
                p,
                revenue=Money(
                    money_at(
                        p.revenue,
                        period.calendar_year,
                        a,
                        p.price_treatment,
                        p.escalation,
                    ),
                    a.currency,
                    a.financial_base_year
                    if a.price_mode == "real"
                    else period.calendar_year,
                    "Normalized from " + p.revenue.source,
                ),
                price_treatment="actual",
                escalation=None,
            )
            for p in products
        )
        revenue = sum((p.revenue.amount for p in products), ZERO)
        costs, fixed, variable, cash_cogs, unclassified = calculate_costs(
            operation, period, a
        )
        if unclassified:
            warnings.append(
                "Gross profit unavailable where cash expense classification is incomplete."
            )
        spent = capital[y]
        startup = sum(
            (
                amount
                for key, kind, amount in spent
                if kind == "startup"
                and next(i for i in inputs.capital if i.id == key).startup_treatment
                == "expensed"
            ),
            ZERO,
        )
        capex = sum((amount for _, _, amount in spent), ZERO) - startup
        depreciation = sum((schedule[y] for schedule, _ in assets.values()), ZERO)
        proceeds, gain = ZERO, ZERO
        for item in inputs.capital:
            if item.disposal_year == y:
                sale = money_at(
                    item.disposal_proceeds,
                    period.calendar_year,
                    a,
                    item.disposal_price_treatment,
                    item.disposal_escalation,
                )
                proceeds += sale
                gain += sale - assets[item.id][1]
        closure = (
            money_at(
                a.closure_cost,
                period.calendar_year,
                a,
                a.closure_price_treatment,
                a.closure_escalation,
            )
            if y == periods[-1].year
            else ZERO
        )
        opening_wc, working_change, recovery, closing_wc, required_delta = wc[y]
        debt = debts[y]
        ebitda, ebit, pbt, _ = profit_loss(
            revenue,
            fixed,
            variable,
            startup,
            closure,
            depreciation,
            debt.interest,
            gain,
            ZERO,
        )
        taxable_operating = (
            ebit
            + (closure if not a.tax.closure_deductible else ZERO)
            + (gain if a.tax.disposal_gains_taxable else ZERO)
        )
        rate = value(tax_rates[y], maximum=Decimal(1))
        offset = value(a.tax.max_loss_offset, maximum=Decimal(1))
        credit = sum(
            (
                money_at(c.money, period.calendar_year, a)
                for c in a.tax.annual_nonrefundable_credits
                if c.year == y
            ),
            ZERO,
        )
        project_tax = calculate_tax(
            taxable_operating,
            project_lots,
            y,
            rate,
            a.tax.carry_losses,
            offset,
            a.tax.loss_expiry_years,
            credit,
        )
        equity_tax = calculate_tax(
            taxable_operating - (debt.interest if a.tax.interest_deductible else ZERO),
            equity_lots,
            y,
            rate,
            a.tax.carry_losses,
            offset,
            a.tax.loss_expiry_years,
            credit,
        )
        project_lots, equity_lots = project_tax.carry_lots, equity_tax.carry_lots
        net_income = pbt - equity_tax.tax
        project_recurring = revenue - fixed - variable - project_tax.tax
        project_point = -capex - startup - closure + proceeds - working_change
        equity_recurring = revenue - fixed - variable - debt.interest - equity_tax.tax
        equity_point = project_point + debt.draw - debt.principal
        operating, investing, fcff, fcfe = cash_flows(
            net_income,
            depreciation,
            gain,
            working_change,
            capex,
            proceeds,
            debt.draw,
            debt.principal,
            project_recurring,
            project_point,
        )
        if a.debt.equity_mode == "residual_equity":
            equity_in = max(ZERO, -fcfe)
        else:
            equity_in = specified.get(y, ZERO)
            if equity_in + fcfe < -Decimal("1e-15"):
                raise ValueError("Specified equity funding shortfall in year " + str(y))
        equity_out = max(ZERO, fcfe + equity_in)
        financing = debt.draw - debt.principal + equity_in - equity_out
        cash_closing = operating + investing + financing
        project_cumulative += fcff
        equity_cumulative += fcfe
        cfads = ebitda - equity_tax.tax - required_delta
        coverage = dscr(cfads, debt.interest + debt.principal)
        cogs = (
            None
            if unclassified
            else cash_cogs
            + depreciation * value(a.tax.depreciation_cogs_fraction, maximum=Decimal(1))
        )
        rows.append(
            AnnualLedger(
                period,
                products,
                costs,
                tuple(spent),
                revenue,
                fixed,
                variable,
                cogs,
                None if cogs is None else revenue - cogs,
                startup,
                closure,
                ebitda,
                depreciation,
                ebit,
                gain,
                debt.interest,
                pbt,
                equity_tax.tax,
                net_income,
                project_tax.tax,
                sum((v for _, v in project_lots), ZERO),
                sum((v for _, v in equity_lots), ZERO),
                capex,
                proceeds,
                opening_wc,
                working_change,
                recovery,
                closing_wc,
                debt,
                cfads,
                coverage,
                operating,
                investing,
                financing,
                fcff,
                fcfe,
                equity_in,
                equity_out,
                cash_closing,
                project_recurring,
                project_point,
                equity_recurring,
                equity_point,
                project_cumulative,
                equity_cumulative,
                discount(
                    project_recurring,
                    project_point,
                    value(a.project_discount_rate, "fraction/year", minimum=None),
                    y,
                    a.discount_convention,
                ),
                discount(
                    equity_recurring,
                    equity_point,
                    value(a.equity_discount_rate, "fraction/year", minimum=None),
                    y,
                    a.discount_convention,
                ),
                project_tax.credit_used,
                equity_tax.credit_used,
            )
        )
    if debts[periods[-1].year].closing > Decimal("1e-15"):
        raise ValueError("Debt remains outstanding at shutdown")
    return tuple(rows)
