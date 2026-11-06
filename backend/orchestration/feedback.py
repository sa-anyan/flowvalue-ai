"""Compact deterministic validation feedback for one bounded engineering correction."""

from backend.equipment_costing.models import priced_record


def equipment_feedback(result):
    stage = result["stages"].get("equipment", {})
    lines = (stage.get("result") or {}).get("equipment", [])
    failed = [
        {
            "equipment_tag": r["equipment_tag"],
            "curve_id": r["curve_id"],
            "candidate_curve_ids": r.get("decision", {}).get("candidate_curve_ids", []),
            "issues": r["issues"],
            "sizing": (r.get("parsed_source") or {}).get("sizing"),
            "sizing_issue": (r.get("parsed_source") or {}).get("sizing_issue"),
        }
        for r in lines
        if (r.get("curve_id") or r.get("decision", {}).get("candidate_curve_ids"))
        and r.get("decision", {}).get("scope_decision") != "alias"
        and (
            not priced_record(r)
            or ((r.get("calculation") or {}).get("evidence") or {}).get(
                "deferred_scope_factors"
            )
        )
    ]
    if not failed:
        return None
    return {
        "engineering_errors": failed,
        "capex_status": result["stages"].get("capex", {}).get("status"),
        "instruction": "Correct these Python-reported selection/unit/scope/extrapolation errors. Preserve defensible assumptions and do not stack installation/module alternatives. Declare both input and target gallon basis for gallon-coordinate assumptions. Use a suitable physical-capacity model or explicit justified exponent for extrapolation; never clamp engineering capacity. No invented physical values.",
    }
