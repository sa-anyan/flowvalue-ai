"""Expand an explicit operating-study policy into the canonical financial handoff."""

import re
from dataclasses import replace
from datetime import date
from decimal import Decimal

from backend.revenue.models import Assumption

from ..models import (
    DebtPlan,
    DepreciationPolicy,
    FinancialAssumptions,
    Money,
    Spend,
    TaxPolicy,
    WorkingCapitalPlan,
)
from .calculator import prepare_financial_inputs


def prepare_study_financials(*, project_id, config, capex, revenue, opex_by_year):
    policy = config["financial"]
    basis_years = re.findall(r"(?<!\d)(?:19|20)\d{2}(?!\d)", capex.period or "")
    if not basis_years:
        raise ValueError(
            "CAPEX reference year is required before a dated financial study"
        )
    year = int(basis_years[0])
    life = int(policy["operating_years"])
    construction = int(policy["construction_years"])
    if (
        life != policy["operating_years"]
        or construction != policy["construction_years"]
        or not 1 <= life <= 50
        or not 0 <= construction <= 10
    ):
        raise ValueError(
            "Use integer operating/construction years within supported planning bounds"
        )
    dep_life = int(policy["depreciation_years"])
    if dep_life != policy["depreciation_years"] or not 1 <= dep_life <= 50:
        raise ValueError("Use an integer depreciation life from 1 to 50 years")
    calendar_year = int(
        policy.get(
            "calendar_start_year", date.fromisoformat(config["assumption_date"]).year
        )
    )
    horizon = life + construction
    source = (
        "AI planning policy, not jurisdictional tax/engineering verification; "
        + policy["rationale"]
    )

    def a(value, unit="fraction"):
        return Assumption(
            Decimal(str(value)),
            unit,
            source,
            "Stored coupled-study assumptions",
            "Unverified editable engineering scenario",
            "llm_estimate",
            config["assumption_date"],
        )

    def money(amount):
        return Money(Decimal(str(amount)), capex.currency, year, source)

    tax = TaxPolicy(
        "Flat-rate planning scenario; jurisdiction not validated",
        tuple((i, a(policy["tax_rate"])) for i in range(horizon + 1)),
        True,
        None,
        a(1),
        False,
        True,
        True,
        a(1),
        source,
    )
    wc = WorkingCapitalPlan(
        (),
        horizon,
        a(policy["working_capital_recovery_fraction"]),
        source + "; imported canonical CAPEX working capital once",
    )
    debt = DebtPlan(
        (),
        a(0, "fraction/year"),
        construction + 1,
        life,
        "equal_principal",
        "end",
        False,
        "residual_equity",
        (),
        source + "; explicitly unlevered study, no debt interest",
    )
    assumptions = FinancialAssumptions(
        date(calendar_year, 1, 1),
        construction,
        date(calendar_year + construction, 1, 1),
        date(calendar_year + construction, 1, 1),
        life,
        capex.currency,
        year,
        "real",
        a(0, "fraction/year"),
        a(policy["discount_rate"], "fraction/year"),
        a(policy["discount_rate"], "fraction/year"),
        "discrete_end",
        a(policy["discount_rate"], "fraction/year"),
        a(policy["discount_rate"], "fraction/year"),
        (),
        tax,
        wc,
        debt,
        money(policy["closure_allowance"]),
        source,
        closure_price_treatment="base",
    )
    weights = [Decimal(str(x)) for x in policy["construction_spend_fractions"]]
    expected = max(construction, 1)
    if len(weights) != expected or any(w < 0 for w in weights) or sum(weights) <= 0:
        raise ValueError(
            "One explicit capital-spend weight per construction year required"
        )
    # Retain original shares; normalization is explicit in financial assumption provenance.
    total = sum(weights)
    fractions = [w / total for w in weights]
    if len(fractions) > 1:
        fractions[-1] = 1 - sum(fractions[:-1])
    spend = tuple(
        Spend(i + 1 if construction else 0, a(f)) for i, f in enumerate(fractions)
    )
    timing = config.get("cashflow_schedule") or {}
    from backend.blocks.cashflow.schedule import validate

    if timing:
        validate(timing, config)

    def dated_spend(shares):
        values = [
            (int(y), Decimal(str(f)))
            for y, f in sorted(shares.items(), key=lambda x: int(x[0]))
            if Decimal(str(f))
        ]
        residual = Decimal(1) - sum((f for _, f in values), Decimal(0))
        if abs(residual) > Decimal("1e-12"):
            raise ValueError("Capital spending must total 100%")
        # Reconcile binary-JSON percentage rounding only; never rescale budgets.
        year, last = values[-1]
        values[-1] = (year, last + residual)
        return tuple(
            Spend(
                y,
                replace(
                    a(f),
                    rationale=(
                        "Explicit project-year share; final Decimal rounding residual "
                        + str(residual)
                        if i == len(values) - 1
                        else "Explicit project-year share"
                    ),
                ),
            )
            for i, (y, f) in enumerate(values)
        )

    if "capital_spend_fractions" in timing:
        spend = dated_spend(timing["capital_spend_fractions"])
        assumptions = replace(
            assumptions,
            capital_payment_end_year=max(
                construction,
                max(
                    int(y)
                    for y, f in timing["capital_spend_fractions"].items()
                    if Decimal(str(f))
                ),
            ),
        )
    amounts = {
        "direct": capex.direct_costs,
        "indirect": capex.indirect_costs,
        "offsite": capex.fixed_capital - capex.plant_cost,
        "startup": capex.startup_expenses,
    }
    land = next(
        (
            line.amount
            for line in capex.lines
            if line.id == "land" and line.amount is not None
        ),
        Decimal(0),
    )
    policies = {}
    proceeds = {}
    for key, amount in amounts.items():
        depreciable = max(Decimal(0), amount - land) if key == "direct" else amount
        fraction = depreciable / amount if amount else Decimal(0)
        salvage = depreciable * Decimal(str(policy["salvage_fraction"]))
        policies[key] = DepreciationPolicy(
            "straight_line",
            construction + 1,
            dep_life,
            a(fraction),
            money(salvage),
            None,
            False,
            (),
            source + "; land excluded from direct depreciation",
            "Planning straight-line full-year policy; not verified tax law",
        )
        proceeds[key] = money(salvage)
    classifications = {
        line.id: (
            "sga"
            if line.category
            in {"administration", "distribution_sales", "research_development"}
            else "cogs"
        )
        for result in opex_by_year.values()
        for line in result.lines
    }
    inputs = prepare_financial_inputs(
        project_id=project_id,
        assumptions=assumptions,
        capex_result=capex,
        opex_by_revenue_year=opex_by_year,
        revenue_result=revenue,
        year_map={i: i + construction for i in range(1, life + 1)},
        price_year=year,
        capital_spend=spend,
        depreciation_policies=policies,
        disposal_proceeds=proceeds,
        startup_treatment="capitalized",
        working_capital_funding_year=timing.get(
            "working_capital_funding_year", construction
        ),
        classifications=classifications,
        selling_cost_reconciliation="Commercial deductions are net revenue adjustments; no duplicate OPEX charge.",
    )
    # Commissioning/start-up is a separate capital component, not recurring OPEX.
    # Keep its total unchanged while placing it at the explicitly selected dates.
    if "startup_spend_fractions" in timing:
        startup_spend = dated_spend(timing["startup_spend_fractions"])
        inputs = replace(
            inputs,
            capital=tuple(
                replace(item, spend=startup_spend) if item.id == "startup" else item
                for item in inputs.capital
            ),
        )
    return inputs
