"""Equipment-only execution; consumes a previously run engineering register."""

import copy
from backend.blocks.models import Product
from backend.blocks.shared import plain
from backend.equipment_resolution.scope import expand
from .calculation import calculate_equipment
from backend.equipment_matching.service import match_report, apply_matches


def calculate(ctx):
    plan = copy.deepcopy(ctx.plan)
    updates = {}
    issues = []
    matching = None
    if ctx.use_ai and "equipment" not in ctx.state.get("locked", []):
        matching = match_report(
            ctx.report,
            ctx.state.get("process_description", ctx.state.get("description", "")),
            ctx.store,
            ctx.provider,
        )
        plan["equipment"] = apply_matches(plan.get("equipment", []), matching)
        updates["plan"] = {"equipment": plan["equipment"]}
        issues.extend(
            "Equipment matching batch unavailable: " + b.get("reason", "unknown")
            for b in matching["batches"]
            if b["status"] == "unavailable"
        )
    report, plan = expand(ctx.report, plan)
    from backend.equipment_costing.unit_conversion.bridges.automatic import resolve

    plan, input_resolution = resolve(
        report,
        plan,
        ctx.state.get("process_description") or ctx.state.get("description", ""),
        ctx.store,
        ctx.provider,
        use_ai=ctx.use_ai,
        locked="equipment" in ctx.state.get("locked", []),
    )
    if plan.get("equipment") != ctx.plan.get("equipment"):
        updates["plan"] = {"equipment": plan["equipment"]}
    total, rows = calculate_equipment(report, plan, plan.get("cost_translation"))
    if ctx.use_ai and "equipment" not in ctx.state.get("locked", []):
        from backend.equipment_costing.unit_conversion.bridges.automatic import (
            repair_pricing,
        )

        repaired, pricing_audit = repair_pricing(
            report,
            plan,
            total,
            ctx.state.get("process_description") or ctx.state.get("description", ""),
            ctx.store,
            ctx.provider,
        )
        input_resolution.extend(pricing_audit)
        if repaired != plan:
            plan = repaired
            updates["plan"] = {"equipment": plan["equipment"]}
            total, rows = calculate_equipment(
                report, plan, plan.get("cost_translation")
            )
    result = plain(total)
    result["input_resolution"] = input_resolution
    result["matching_register"] = matching or {
        "matches": [
            p["matching"] for p in plan.get("equipment", []) if p.get("matching")
        ],
        "notice": "Saved conceptual matches; Python calculation does not invoke an LLM.",
    }
    from backend.orchestration.pricing_status import annotate

    annotate(result, report, plan)
    from backend.equipment_resolution.review import review

    result["resolution_register"] = review(
        report, plan, {"stages": {"equipment": {"result": result}}}, expanded=True
    )
    unpriced = [
        e.equipment_tag
        for e in total.equipment
        if e.equipment_cost is None
        and not (e.parsed_source or {}).get("confirmed_alias")
    ]
    return Product(
        result,
        {
            "total": plain(total),
            "sizing_rows": rows,
            "report": report,
            "unpriced": unpriced,
        },
        updates,
        complete=not unpriced,
        issues=tuple(issues),
    )
