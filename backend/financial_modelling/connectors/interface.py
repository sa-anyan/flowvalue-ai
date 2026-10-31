"""Compose existing output adapters; never invoke the upstream engines implicitly."""

from ..models import Operation
from .opex.interface import costs_from_result
from .revenue.interface import sales_from_result


def operations_from_results(
    revenue_result,
    opex_by_revenue_year,
    *,
    year_map,
    price_year,
    activities_by_year=None,
    classifications=None,
    selling_cost_reconciliation="",
):
    if len(set(year_map.values())) != len(year_map):
        raise ValueError("Revenue-to-financial year mapping must be one-to-one")
    if set(year_map) != {r.year for r in revenue_result.annual}:
        raise ValueError("Map every Revenue operating year explicitly")
    activities_by_year = activities_by_year or {}
    for revenue_year in year_map:
        annual = next(r for r in revenue_result.annual if r.year == revenue_year)
        opex = opex_by_revenue_year[revenue_year]
        if opex.basis.currency != revenue_result.basis.currency:
            raise ValueError("Align OPEX revenue-factor currency with Revenue upstream")
        for saving in revenue_result.avoided_costs:
            matches = [line for line in opex.lines if line.id == saving.target_opex_id]
            if len(matches) != 1 or ("avoided cost " + saving.id + ":") not in matches[0].rationale:
                raise ValueError("Revenue economic savings have not been reconciled with their OPEX owner")
        for line in opex.lines:
            if (
                line.calculation_base == "annual_revenue"
                and line.base_amount != annual.sales_revenue
            ):
                raise ValueError(
                    "Stale OPEX sales-based factors: recalculate OPEX using the matching Revenue year before handoff"
                )
    return tuple(
        Operation(
            financial_year,
            sales_from_result(
                revenue_result,
                revenue_year,
                price_year=price_year[financial_year]
                if isinstance(price_year, dict)
                else price_year,
                selling_cost_reconciliation=selling_cost_reconciliation,
            ),
            costs_from_result(
                opex_by_revenue_year[revenue_year],
                price_year=price_year[financial_year]
                if isinstance(price_year, dict)
                else price_year,
                classifications=classifications,
            ),
            activities_by_year.get(financial_year, ()),
            "Canonical Revenue/OPEX handoff; already annualized actual amounts",
        )
        for revenue_year, financial_year in sorted(year_map.items())
    )
