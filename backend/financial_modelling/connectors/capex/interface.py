"""Pure canonical CAPEX import; no equipment/installed/module additions."""

from decimal import Decimal

from backend.capex.models import CapexResult

from ...models import CapitalItem, Money


def capital_from_result(
    result,
    *,
    price_year,
    spend,
    depreciation_policies,
    disposal_year,
    disposal_proceeds,
    startup_treatment,
):
    if (
        not isinstance(result, CapexResult)
        or result.issues
        or any(
            v is None
            for v in (
                result.direct_costs,
                result.indirect_costs,
                result.plant_cost,
                result.fixed_capital,
                result.startup_expenses,
                result.working_capital,
                result.total_capex,
                result.currency,
            )
        )
    ):
        raise ValueError("Complete canonical CAPEX result required")
    direct, indirect = result.direct_costs, result.indirect_costs
    if abs(direct + indirect - result.plant_cost) > Decimal("1e-12") * max(
        1, result.plant_cost
    ):
        raise ValueError("CAPEX direct/indirect components do not reconcile")
    offsite = result.fixed_capital - result.plant_cost
    if offsite < 0:
        raise ValueError("Invalid canonical fixed capital / plant scope")
    amounts = {
        "direct": direct,
        "indirect": indirect,
        "offsite": offsite,
        "startup": result.startup_expenses,
    }
    if sum(amounts.values(), Decimal(0)) + result.working_capital != result.total_capex:
        raise ValueError("CAPEX components and working capital do not reconcile")
    source = (
        "Canonical CAPEX "
        + result.model_id
        + "; "
        + str(result.period)
        + "; fixed capital/startup/WC kept separate"
    )
    items = tuple(
        CapitalItem(
            key,
            key,
            Money(amount, result.currency, price_year, source),
            spend,
            depreciation_policies[key],
            disposal_year,
            disposal_proceeds[key],
            startup_treatment if key == "startup" else "capitalized",
            "base",
        )
        for key, amount in amounts.items()
        if amount != 0
    )
    return items, Money(
        result.working_capital,
        result.currency,
        price_year,
        source + "; working capital only",
    )
