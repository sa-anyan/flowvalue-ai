"""Equipment-only execution; consumes a previously run engineering register."""

from backend.equipment_costing.models import is_scoped_capital


import copy
from backend.blocks.models import Product
from backend.blocks.shared import plain
from backend.equipment_resolution.identity import identity_register
from backend.equipment_resolution.scope import expand
from .calculation import calculate_equipment
from backend.equipment_matching.service import match_report, apply_matches


def prepare(ctx):
    plan = copy.deepcopy(ctx.plan)
    from .quantity import equipment_quantity

    tags = {
        e["key"]: e["identifier"]
        for e in ctx.report.get("entities", [])
        if e.get("kind") == "equipment"
    }
    for row in plan.get("equipment", []):
        if "quantity" not in row and row.get("equipment_key") in tags:
            count, basis = equipment_quantity(row, tags[row["equipment_key"]])
            row.update(quantity=count, quantity_origin=basis)
            row.setdefault(
                "quantity_rationale",
                (
                    "Two equal units under the founder AB convention"
                    if count == 2
                    else "Single equipment default"
                ),
            )
    updates = {}
    issues = []
    matching = None
    from backend.equipment_resolution.duplicates import reconcile

    # Match against the same merged stream evidence that sizing will consume.
    report, plan, duplicate_review = reconcile(ctx.report, plan)
    from backend.blocks.progress import step
    from backend.equipment_matching.library_preference import user_selected_model

    extracted = {e["key"] for e in report.get("entities", []) if e.get("kind") == "equipment"}
    chosen = {r["equipment_key"] for r in plan.get("equipment", []) if user_selected_model(r)}
    # Quick match: when the user has confirmed a model for every item, an AI
    # rematch would only be shown for review and is skipped to save time.
    all_confirmed = bool(extracted) and extracted <= chosen
    if all_confirmed and ctx.use_ai:
        issues.append("AI model matching skipped: you confirmed a model for every item.")
    if ctx.use_ai and not all_confirmed and "equipment" not in ctx.state.get("locked", []):
        step("Matching equipment to models (AI)")
        matching = match_report(
            report,
            ctx.state.get("process_description", ctx.state.get("description", "")),
            ctx.store,
            ctx.provider,
        )
        matched = apply_matches(plan.get("equipment", []), matching)
        by_key = {row["equipment_key"]: row for row in matched}
        # Keep excluded rows so the user can restore them later.
        plan["equipment"] = [
            by_key.pop(row["equipment_key"], row) for row in plan.get("equipment", [])
        ] + list(by_key.values())
        updates["plan"] = {"equipment": plan["equipment"]}
        issues.extend(
            "Equipment matching batch unavailable: " + b.get("reason", "unknown")
            for b in matching["batches"]
            if b["status"] == "unavailable"
        )
    report, plan = expand(report, plan)
    from backend.equipment_costing.unit_conversion.bridges.automatic import resolve

    step("Sizing equipment" + (" (AI proposes missing inputs)" if ctx.use_ai else ""))
    plan, input_resolution = resolve(
        report,
        plan,
        ctx.state.get("process_description") or ctx.state.get("description", ""),
        ctx.store,
        ctx.provider,
        use_ai=ctx.use_ai,
        # A saved edit locks the equipment section. The lock protects what the
        # user saved: the resolver never touches rows with saved inputs, sizes,
        # prices or scope decisions, so an explicit AI run may still propose
        # sizing for rows that have none. AI re-matching and price repair stay
        # blocked by the lock.
        locked=False if ctx.use_ai else "equipment" in ctx.state.get("locked", []),
    )
    if plan.get("equipment") != ctx.plan.get("equipment"):
        updates["plan"] = {"equipment": plan["equipment"]}
    return report, plan, updates, issues, matching, input_resolution, duplicate_review


def calculate(ctx):
    report, plan, updates, issues, matching, input_resolution, duplicate_review = (
        prepare(ctx)
    )
    from backend.blocks.progress import step

    step("Calculating equipment costs")
    total, rows = calculate_equipment(report, plan, plan.get("cost_translation"))
    if ctx.use_ai and "equipment" not in ctx.state.get("locked", []):
        step("Checking unpriced items (AI)")
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
    for line in result.get("equipment", []):
        sizing = (line.get("parsed_source") or {}).get("sizing") or {}
        for warning in (sizing.get("equation") or {}).get("warnings", []):
            message = "Thermal sizing: " + warning
            if message not in line["issues"]:
                line["issues"].append(message)
    result["identity_register"] = identity_register(
        ctx.report, report, plan, duplicate_review, ctx.plan
    )
    result["duplicate_review"] = duplicate_review
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
        and not (
            is_scoped_capital(
                e.cost_scope, e.calculation.evidence if e.calculation else None
            )
            and e.amount is not None
        )
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
