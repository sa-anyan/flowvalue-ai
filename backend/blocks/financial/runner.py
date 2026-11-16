"""Financial-only execution. Consumes saved results, never runs upstream engines."""

from backend.blocks.models import Product, DataRequired
from backend.blocks.shared import canonical, plain, translate_inputs
from backend.capex.models import CapexResult
from backend.opex.models import OpexResult
from backend.revenue.models import RevenueResult
from backend.financial_modelling.connectors.operating_economics import (
    prepare_study_financials,
)
from backend.financial_modelling import calculate_financials


def calculate(ctx):
    if not ctx.upstream["capex"].get("complete") or not ctx.upstream["opex"].get(
        "complete"
    ):
        raise DataRequired(
            "Data required: complete the missing CAPEX/OPEX items and run those stages before calculating financial metrics.",
            ("capex", "opex"),
        )
    capex = canonical(CapexResult, ctx.upstream["capex"]["capital"])
    revenue = canonical(RevenueResult, ctx.upstream["revenue"]["revenue"])
    if (revenue.basis.currency, revenue.basis.price_period) != (capex.currency, capex.period):
        raise DataRequired("CAPEX and Revenue need a common currency and price period before calculating financial metrics.")
    opex = {
        int(y): canonical(OpexResult, value)
        for y, value in ctx.upstream["opex"]["years"].items()
    }
    from .proposal import prepare

    proposed_config, changed = prepare(ctx)
    config, audit = translate_inputs(ctx, proposed_config, "financial")
    required = ("depreciation_years", "discount_rate", "tax_rate", "salvage_fraction",
                "working_capital_recovery_fraction", "closure_allowance", "rationale")
    policy = config.get("financial") or {}
    missing = [key.replace("_", " ") for key in required if policy.get(key) is None or policy.get(key) == ""]
    if missing:
        raise DataRequired("Review missing financial planning assumptions: " + ", ".join(missing) + ".")
    inputs = prepare_study_financials(
        project_id=ctx.state["id"],
        config=config,
        capex=capex,
        revenue=revenue,
        opex_by_year=opex,
    )
    result = calculate_financials(inputs)
    return Product(
        plain(result),
        {"financial_inputs": plain(inputs)},
        {"plan": {"operating_economics": proposed_config}} if changed else {},
        complete=not result.issues,
        issues=result.issues,
    )
