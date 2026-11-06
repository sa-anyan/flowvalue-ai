"""CAPEX-only execution; never runs engineering or equipment costing."""

from backend.equipment_costing.models import is_scoped_capital


from backend.blocks.models import Product
from backend.blocks.shared import canonical, proposal, plain
from backend.equipment_costing.total_cost.calculator import EquipmentCostTotal
from .calculation import calculate_capital


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
