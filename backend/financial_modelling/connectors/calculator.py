"""Prepare one financial input bundle from existing canonical engine results."""

import json
from dataclasses import asdict, replace

from ..assumptions.calculator import money_at
from ..financial_schedules.calculator import build_timeline
from ..models import DatedMoney, FinancialInputs
from .capex.interface import capital_from_result
from .interface import operations_from_results


def prepare_financial_inputs(
    *,
    project_id,
    assumptions,
    capex_result,
    opex_by_revenue_year,
    revenue_result,
    year_map,
    price_year,
    capital_spend,
    depreciation_policies,
    disposal_proceeds,
    startup_treatment,
    working_capital_funding_year,
    classifications=None,
    activities_by_year=None,
    selling_cost_reconciliation="",
    working_capital_override_reason="",
    operating_price_years=None,
):
    periods = build_timeline(assumptions)
    if working_capital_funding_year not in range(len(periods)):
        raise ValueError("Explicit working-capital funding year required")
    capital, wc = capital_from_result(
        capex_result,
        price_year=price_year,
        spend=capital_spend,
        depreciation_policies=depreciation_policies,
        disposal_year=periods[-1].year,
        disposal_proceeds=disposal_proceeds,
        startup_treatment=startup_treatment,
    )
    expected_bases = {
        "purchased_equipment": capex_result.purchased_equipment,
        "fixed_capital": capex_result.fixed_capital,
        "plant_including_startup_excluding_working_capital": capex_result.fixed_capital
        + capex_result.startup_expenses,
    }
    for opex in opex_by_revenue_year.values():
        for line in opex.lines:
            if line.calculation_base in expected_bases and (
                opex.basis.currency != capex_result.currency
                or line.base_amount != expected_bases[line.calculation_base]
            ):
                raise ValueError(
                    "Stale or incompatible OPEX capital-factor base: align the canonical CAPEX base/currency upstream"
                )
    plan = assumptions.working_capital
    if not plan.requirements:
        plan = replace(
            plan,
            requirements=(DatedMoney(working_capital_funding_year, wc),),
            source=plan.source
            + "; canonical CAPEX working-capital amount imported once",
        )
    else:
        first = min(plan.requirements, key=lambda x: x.year)
        calendar = periods[first.year].calendar_year
        if (
            first.year != working_capital_funding_year
            or money_at(first.money, calendar, assumptions)
            != money_at(wc, calendar, assumptions)
        ) and not working_capital_override_reason.strip():
            raise ValueError(
                "Financial WC differs from canonical CAPEX; explicit override reason required"
            )
    assumptions = replace(assumptions, working_capital=plan)
    operations = operations_from_results(
        revenue_result,
        opex_by_revenue_year,
        year_map=year_map,
        price_year=price_year
        if operating_price_years is None
        else operating_price_years,
        classifications=classifications,
        activities_by_year=activities_by_year,
        selling_cost_reconciliation=selling_cost_reconciliation,
    )
    provenance = {
        "capex": asdict(capex_result),
        "opex": {str(k): asdict(v) for k, v in opex_by_revenue_year.items()},
        "revenue": asdict(revenue_result),
        "selling_cost_reconciliation": selling_cost_reconciliation,
        "working_capital_override_reason": working_capital_override_reason,
    }
    return FinancialInputs(
        project_id,
        assumptions,
        capital,
        operations,
        source_references=(
            "Canonical CAPEX/OPEX/Revenue snapshots saved in upstream_snapshots_json",
        ),
        upstream_snapshots_json=json.dumps(
            provenance, default=str, sort_keys=True, allow_nan=False
        ),
    )
