"""OPEX-only execution; consumes saved CAPEX/revenue when factors require them."""

from backend.blocks.models import Product, DataRequired
from backend.blocks.shared import (
    operating_proposal,
    basis_and_schedule,
    canonical,
    plain,
    translate_inputs,
)
from backend.capex.models import CapexResult
from backend.revenue.models import RevenueResult
from .input_builder import _costs_for_year, _opex
from backend.opex.annual_phasing import phase_fixed_costs


def calculate(ctx):
    config, meta = operating_proposal(ctx, "opex")
    # Reference defaults fill only what is still missing (no AI, no network).
    from backend.opex.reference_defaults import for_study

    capital = (ctx.state.get("results", {}).get("stages", {}).get("capex", {}) or {}).get("result") or {}
    cells = (ctx.upstream.get("engineering_data") or ctx.state.get("stage_outputs", {}).get("engineering_data") or {}).get("source_cells")
    config, _ = for_study(config, ctx.report, cells, capital, (ctx.state.get("plan") or {}).get("cost_translation"))
    original = config
    try:
        config, audit = translate_inputs(ctx, config, "opex")
        basis, hours, ramp = basis_and_schedule(ctx, config)
    except (ValueError, TypeError, KeyError) as exc:
        raise DataRequired(
            str(exc), updates={"plan": {"operating_economics": original}}
        ) from exc
    cap = (
        canonical(CapexResult, ctx.upstream["capex"]["capital"])
        if "capex" in ctx.upstream
        else None
    )
    revenue = (
        canonical(RevenueResult, ctx.upstream["revenue"]["revenue"])
        if "revenue" in ctx.upstream
        else None
    )
    if revenue and revenue.basis != basis:
        raise DataRequired(
            "Revenue and OPEX need a common currency and price period for sales-dependent expenses.",
            updates={"plan": {"operating_economics": original}},
        )
    years, details = {}, {}
    complete = True
    for year, fraction in ramp.items():
        costs, detail = _costs_for_year(
            ctx.report, config, basis, hours, fraction, year, partial=True
        )
        annual = (
            next((r.sales_revenue for r in revenue.annual if r.year == year), None)
            if revenue
            else None
        )
        if revenue and revenue.avoided_costs:
            from backend.revenue.economic_savings.avoided_costs import apply_savings

            costs = apply_savings(costs, revenue.avoided_costs, year)
        result = _opex(cap, basis, costs, annual, allow_partial=True)
        result = phase_fixed_costs(result, config, year)
        years[str(year)], details[str(year)] = plain(result), detail
        complete = (
            complete
            and result.annual_cash_opex is not None
            and not detail["pending_items"]
        )
    first = next(iter(years.values()))
    display = {
        "status": "calculated_preliminary" if complete else "partial",
        "complete": complete,
        "currency": basis.currency,
        "price_period": basis.price_period,
        "years": years,
        "first_year_cash_opex": first["annual_cash_opex"] if complete else None,
        "first_year_fixed_opex": first["cash_fixed"],
        "first_year_variable_opex": first["cash_variable"],
        "known_cash_opex_subtotal": first["resolved_cash_subtotal"],
        "first_year_lines": first["lines"],
        "operating_detail": {"annual_hours": str(hours), "years": plain(details)},
    }
    return Product(
        display,
        {"years": years, "complete": complete, "config": config},
        {"plan": {"operating_economics": original}},
        complete=complete,
    )
