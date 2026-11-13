"""Equipment-only execution; consumes a previously run engineering register."""

from backend.equipment_costing.models import is_scoped_capital


import copy
from backend.blocks.models import Product
from backend.blocks.shared import plain
from backend.equipment_resolution.identity import identity_register
from backend.equipment_resolution.scope import expand
from .calculation import calculate_equipment
from backend.equipment_matching.service import match_report, apply_matches


def workbook_parameters_for(ctx, report):
    """{equipment_key: [workbook-stated parameter values]} from the parsed source cells."""
    from backend.equipment_costing.unit_conversion.bridges.workbook_parameters import for_items, scan
    from backend.equipment_matching.deterministic import head_family

    upstream = (getattr(ctx, "upstream", None) or {}).get("engineering_data") or {}
    stored = (ctx.state.get("stage_outputs") or {}).get("engineering_data") or {}
    cells = (upstream.get("source_cells") or stored.get("source_cells")
             or (ctx.state.get("parsed") or {}).get("source_cells") or [])
    items = [{"key": e["key"], "tag": e.get("identifier"),
              "names": [str(v.get("normalized_value") or v.get("original_value") or "")
                        for v in e.get("values", []) if v.get("property") in {"name", "type"}]}
             for e in report.get("entities", []) if e.get("kind") == "equipment"]
    from backend.blocks.progress import step

    step("Searching the workbook for sizing parameters")
    return for_items(scan(cells), items, head_family)


# Record-valued fields of an equipment row. A cleared field may arrive as null
# (e.g. after a model change); downstream code reads these as dicts.
RECORD_FIELDS = ("unit_conversion", "sizing", "costing_options", "manual_price", "external_quote",
                 "matching", "matching_attempt", "model_selection", "previous_costing_inputs")


def without_empty_records(rows):
    """Drop record fields saved as null, so a cleared field means 'absent'."""
    return [{k: v for k, v in row.items() if not (k in RECORD_FIELDS and v is None)} for row in rows]


def prepare(ctx):
    plan = copy.deepcopy(ctx.plan)
    plan["equipment"] = without_empty_records(plan.get("equipment", []))
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
    chosen = {r["equipment_key"] for r in plan.get("equipment", [])
              if user_selected_model(r) or (r.get("model_selection") or {}).get("origin") == "autopilot"}
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
    # Python first: values the workbook states for sizing parameters, scoped to
    # each item, are handed to the sizing AI to use and cite before assuming.
    sizing_report = report
    if ctx.use_ai:
        sizing_report = {**report, "_workbook_parameters": workbook_parameters_for(ctx, report)}
    plan, input_resolution = resolve(
        sizing_report,
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
    # Headline: purchased equipment plus installed packages / unit capital
    # (both are equipment cost; CAPEX applies its factors to purchased only).
    packages = [r.get("amount") for r in result.get("equipment", [])
                if r.get("equipment_cost") is None and r.get("amount") is not None
                and is_scoped_capital(r.get("cost_scope"), (r.get("calculation") or {}).get("evidence"))]
    if result.get("equipment_cost_total") is not None:
        result["packages_total"] = sum(packages) if packages else 0.0
        result["equipment_total_with_packages"] = result["equipment_cost_total"] + result["packages_total"]
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
