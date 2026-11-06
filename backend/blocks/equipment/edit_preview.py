"""Immediate, equipment-scoped Python pricing previews after a saved edit.

Full-stage totals remain stale until the explicit all-equipment run. Never call
matching, assumption generation or another economics stage from this path.
"""

import copy
from backend.orchestration.codec import plain
from .calculation import calculate_equipment


def update_saved_prices(state, previous):
    report = state.get("stage_outputs", {}).get("equipment", {}).get("report")
    if not report:
        report = (
            state.get("stage_outputs", {}).get("engineering_data", {}).get("report")
        )
    stage = (state.get("results") or {}).get("stages", {}).get("equipment", {})
    result = stage.get("result")
    if not report or not result:
        return
    changed = [
        r
        for r in state["plan"].get("equipment", [])
        if r != previous.get(r.get("equipment_key"))
    ]
    if not changed:
        return
    keys = {r["equipment_key"] for r in changed}
    # Retain all stream evidence; restrict the costing loop to edited equipment.
    scoped = copy.deepcopy(report)
    scoped["entities"] = [
        e
        for e in scoped["entities"]
        if e.get("kind") != "equipment" or e["key"] in keys
    ]
    plan = {**state["plan"], "equipment": changed}
    total, _ = calculate_equipment(scoped, plan, plan.get("cost_translation"))
    updates = {
        r["parsed_source"]["equipment_key"]: r for r in plain(total)["equipment"]
    }
    for index, old in enumerate(result.get("equipment", [])):
        key = (old.get("parsed_source") or {}).get("equipment_key")
        if key in updates:
            result["equipment"][index] = {
                **old,
                **updates[key],
                "saved_edit_preview": True,
            }
    stage["saved_edit_preview"] = sorted(updates)
    stage["result_is_stale"] = True
    stage["issues"] = [
        "Edited equipment prices updated with Python. Run all equipment to reconcile totals and coverage."
    ]
