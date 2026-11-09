"""Whole-model validation before any ledger or investment result is issued."""

import json
from decimal import Decimal

from ..assumptions.calculator import value
from ..financial_schedules.calculator import build_timeline


def validate(inputs):
    errors = []
    a = inputs.assumptions
    try:
        json.dumps(json.loads(inputs.upstream_snapshots_json), allow_nan=False)
    except (ValueError, TypeError):
        errors.append("Invalid saved upstream provenance JSON")

    def require(test, message):
        if not test:
            errors.append(message)

    require(
        bool(inputs.id and inputs.actor and inputs.change_reason),
        "Scenario identity, actor and change rationale required",
    )
    require(
        type(inputs.revision) is int and inputs.revision > 0,
        "Positive scenario revision required",
    )
    require(
        a.price_mode in {"real", "nominal"}, "Select real or nominal price convention"
    )
    require(
        a.discount_convention in {"discrete_end", "continuous_end", "garrett_uniform"},
        "Unsupported discount convention",
    )
    require(bool(a.currency and a.source), "Currency and assumption source required")
    require(
        isinstance(a.currency, str)
        and len(a.currency) == 3
        and a.currency.isalpha()
        and a.currency.isupper(),
        "Project currency must be an explicit uppercase three-letter code",
    )
    require(
        type(a.financial_base_year) is int and 1900 <= a.financial_base_year <= 9999,
        "Explicit financial base year required",
    )
    try:
        inflation = value(a.inflation, "fraction/year", minimum=Decimal(-1))
        require(inflation > -1, "Inflation must exceed -100%")
        for rate in (
            a.project_discount_rate,
            a.equity_discount_rate,
            a.mirr_finance_rate,
            a.mirr_reinvestment_rate,
        ):
            v = value(rate, "fraction/year", minimum=None)
            require(
                a.discount_convention != "discrete_end" or v > -1,
                "Discrete rates must exceed -100%",
            )
        value(a.tax.max_loss_offset, maximum=Decimal(1))
        value(a.tax.depreciation_cogs_fraction, maximum=Decimal(1))
        require(
            bool(a.tax.jurisdiction and a.tax.source),
            "Explicit tax jurisdiction/policy source required",
        )
        require(
            a.tax.loss_expiry_years is None
            or type(a.tax.loss_expiry_years) is int
            and a.tax.loss_expiry_years >= 0,
            "Loss expiry must be explicit nonnegative years or unlimited None",
        )
        for flag in (
            a.tax.carry_losses,
            a.tax.interest_deductible,
            a.tax.closure_deductible,
            a.tax.disposal_gains_taxable,
            a.debt.balloon_at_shutdown,
        ):
            require(type(flag) is bool, "Policy flags must be boolean")
        periods = build_timeline(a)
    except (ValueError, TypeError, AttributeError, OverflowError) as exc:
        errors.append(str(exc))
        return tuple(errors)
    years = set(range(len(periods)))
    payment_end = (
        a.construction_years
        if a.capital_payment_end_year is None
        else a.capital_payment_end_year
    )
    require(
        type(payment_end) is int
        and payment_end in years
        and payment_end >= a.construction_years,
        "Explicit capital payment window must cover construction within the project horizon",
    )
    credits = a.tax.annual_nonrefundable_credits
    require(
        len({x.year for x in credits}) == len(credits)
        and all(x.year in years for x in credits),
        "Tax credit years invalid or duplicated",
    )
    require(
        not credits or bool(a.tax.credit_policy_source),
        "Explicit credit policy and eligibility source required; no automatic policy qualification",
    )
    rates = dict(a.tax.annual_rates)
    require(
        all(type(year) is int for year, _ in a.tax.annual_rates),
        "Tax model years must be integers, not booleans or strings",
    )
    require(
        len(rates) == len(a.tax.annual_rates) and set(rates) == years,
        "Explicit unique tax rates required for every financial year including year zero",
    )
    try:
        for rate in rates.values():
            value(rate, maximum=Decimal(1))
    except (ValueError, TypeError) as exc:
        errors.append(str(exc))
    require(
        a.debt.equity_mode in {"residual_equity", "specified_equity"},
        "Declare residual or specified equity funding",
    )
    require(
        a.debt.equity_mode != "residual_equity" or not a.debt.equity_contributions,
        "Residual equity and manual equity contributions cannot be combined",
    )
    require(
        len({x.year for x in a.debt.equity_contributions})
        == len(a.debt.equity_contributions),
        "Duplicate equity contribution years",
    )
    require(
        all(
            type(x.year) is int and x.year in years for x in a.debt.equity_contributions
        ),
        "Equity contribution outside timeline",
    )
    ids = set()
    for capital in inputs.capital:
        require(
            bool(capital.id) and capital.id not in ids,
            "Duplicate or missing capital item ID",
        )
        ids.add(capital.id)
        require(
            capital.kind
            in {
                "direct",
                "indirect",
                "offsite",
                "startup",
                "replacement",
                "sustaining",
                "expansion",
            },
            "Unsupported capital category",
        )
        require(
            capital.startup_treatment in {"capitalized", "expensed"},
            "Explicit startup treatment required",
        )
        require(
            capital.kind == "startup" or capital.startup_treatment == "capitalized",
            "Only startup may be expensed through the capital schedule",
        )
        require(
            capital.kind != "startup"
            or capital.startup_treatment != "expensed"
            or capital.depreciation.method == "none",
            "Expensed startup cannot also be depreciated",
        )
        require(
            type(capital.disposal_year) is int and capital.disposal_year in years,
            "Capital disposal year invalid",
        )
        require(
            all(type(s.year) is int and s.year in years for s in capital.spend),
            "Capital spend year invalid",
        )
        require(
            all(s.year <= capital.disposal_year for s in capital.spend),
            "Capital cannot be spent after asset disposal",
        )
        if capital.kind in {"direct", "indirect", "offsite"}:
            require(
                all(
                    type(payment_end) is int and s.year <= payment_end
                    for s in capital.spend
                ),
                "Initial construction capital outside construction spending window",
            )
    operations = {o.year: o for o in inputs.operations}
    require(
        len(operations) == len(inputs.operations), "Duplicate financial operation year"
    )
    require(set(operations) <= years, "Operation outside project timeline")
    active = {p.year for p in periods if p.operating_fraction > 0}
    require(
        active <= set(operations),
        "Missing annual Revenue/OPEX input for an active financial period",
    )
    product_units = {}
    for operation in inputs.operations:
        require(bool(operation.source), "Operation source required")
        require(
            len({p.id for p in operation.products}) == len(operation.products),
            "Duplicate annual product ID",
        )
        for p in operation.products:
            require(
                bool(p.id and p.unit and p.source),
                "Product identity, units and source required",
            )
            require(
                p.sold <= p.saleable <= p.produced,
                "Production, saleable and sales quantities inconsistent",
            )
            require(
                p.revenue_category
                in {
                    "product_sales",
                    "processing_services",
                    "capacity_availability",
                    "infrastructure_usage",
                    "environmental_attributes",
                    "other_contractual_income",
                },
                "Unknown revenue category",
            )
            if p.sold == 0 and p.revenue_category == "product_sales":
                require(
                    p.revenue.amount in (None, Decimal(0)),
                    "Revenue without sales quantity",
                )
            require(
                p.id not in product_units or product_units[p.id] == p.unit,
                "Product units change between financial years",
            )
            product_units[p.id] = p.unit
            if operation.year not in active:
                require(
                    p.produced == 0 and p.sold == 0 and p.revenue.amount == 0,
                    "Production/sales before first production or after shutdown",
                )
    return tuple(dict.fromkeys(errors))
