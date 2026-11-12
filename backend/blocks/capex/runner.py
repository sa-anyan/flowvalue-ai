"""CAPEX-only execution; never runs engineering or equipment costing."""

from backend.equipment_costing.models import is_scoped_capital


from backend.blocks.models import Product
from backend.blocks.shared import canonical, proposal, plain
from backend.equipment_costing.total_cost.calculator import EquipmentCostTotal
from .calculation import calculate_capital


def _estimate_class(ctx, plan, total, unpriced):
    """M3.5: propose an AACE class for review; never certifies it."""
    from backend.blocks.stage_workflow import approved
    from backend.capex.estimate_class import propose_estimate_class

    try:
        return _propose(ctx, plan, total, unpriced, approved, propose_estimate_class)
    except ValueError as exc:
        # Bad review input must not block CAPEX; it is shown for correction.
        return {"status": "invalid_input", "error": str(exc), "requires_review": True}


def _propose(ctx, plan, total, unpriced, approved, propose_estimate_class):
    # Editable plan section "estimate_class":
    # {"design_maturity": {...}, "new_technology": bool, "review": {...}}
    review_inputs = plan.get("estimate_class") or {}
    return propose_estimate_class(
        design_maturity=review_inputs.get("design_maturity"),
        balance_approved=approved(ctx.state),
        equipment_lines=plain(total.equipment),
        unpriced=unpriced,
        capex_method=plan.get("capex", {}).get("model_id", "garrett"),
        new_technology=bool(review_inputs.get("new_technology")),
        review=review_inputs.get("review"),
    )


def calculate(ctx):
    total = canonical(EquipmentCostTotal, ctx.upstream["equipment"]["total"])
    plan = dict(ctx.plan)
    updates = {}
    if ctx.use_ai and "capex" not in ctx.state.get("locked", []):
        values, meta = proposal(ctx, ("capex",))
        if "capex" in values:
            plan["capex"] = values["capex"]
            updates["plan"] = {"capex": values["capex"]}
    priced = [
        e
        for e in total.equipment
        if e.amount is not None
        and (
            e.equipment_cost is not None
            or is_scoped_capital(
                e.cost_scope, e.calculation.evidence if e.calculation else None
            )
        )
    ]
    capital, artifacts = calculate_capital(
        priced,
        total,
        plan,
        ctx.state.get("description", ""),
        plan.get("cost_translation"),
    )
    result = plain(capital)
    unpriced = ctx.upstream["equipment"].get("unpriced", [])
    result.update(
        complete=not unpriced and capital.total_capex is not None,
        unpriced_equipment=unpriced,
        estimate_class=_estimate_class(ctx, plan, total, unpriced),
    )
    return Product(
        result,
        {
            "capital": plain(capital),
            "complete": result["complete"],
            "screening_comparisons": artifacts.get("screening_comparisons", []),
        },
        updates,
        complete=result["complete"],
    )
