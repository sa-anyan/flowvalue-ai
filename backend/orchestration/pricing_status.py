"""Separate equipment identity, candidate matching, sizing and price coverage."""


def annotate(result, report, plan):
    proposals = {p["equipment_key"]: p for p in plan.get("equipment", [])}
    counts = {"priced": 0, "unpriced": 0, "alias_proposals": 0}
    queue = []
    for row in result.get("equipment", []):
        key = row.get("parsed_source", {}).get("equipment_key")
        p = proposals.get(key, {})
        candidates = list(
            dict.fromkeys(
                [
                    *p.get("candidate_curve_ids", []),
                    *([row["curve_id"]] if row.get("curve_id") else []),
                ]
            )
        )
        priced = row.get("equipment_cost") is not None
        alias = p.get("scope_decision") == "alias"
        counts["priced" if priced else "unpriced"] += 1
        counts["alias_proposals"] += int(alias)
        issues = row.get("issues", [])
        sizing = row.get("parsed_source", {}).get("sizing")
        status = {
            "identification": "registered",
            "cost_method": "PRICED — USER"
            if priced and p.get("manual_price")
            else "PRICED — ANALOGY"
            if priced
            and (p.get("external_quote") or {}).get("method") == "engineering_analogy"
            else "PRICED — BENCHMARK"
            if priced and p.get("external_quote")
            else "PRICED — MODEL"
            if priced
            else "UNRESOLVED",
            "matching": "selected"
            if row.get("curve_id")
            else "candidate_available"
            if candidates
            else "unresolved",
            "candidate_curve_ids": candidates,
            "selected_curve_id": row.get("curve_id"),
            "sizing": "calculated"
            if sizing
            else "direct_input"
            if p.get("size") is not None
            else "needs_review",
            "pricing": "assumption_based_estimate"
            if priced
            else "alias_review"
            if alias
            else "unpriced",
            "scope_decision": p.get("scope_decision", "include"),
            "alias_of": p.get("alias_of"),
            "rationale": p.get("rationale", "No engineering selection returned"),
            "blockers": issues if not priced else [],
            "sizing_evidence": sizing,
            "next_action": "review_assumptions"
            if priced
            else "confirm_alias"
            if alias
            else "review_sizing"
            if candidates
            else "offer_opt_in_model_research",
        }
        row["decision"] = status
        if not priced:
            queue.append(
                {
                    "equipment_tag": row["equipment_tag"],
                    "action": status["next_action"],
                    "reason": status["rationale"],
                    "issues": issues,
                }
            )
    result["pricing_coverage"] = {
        **counts,
        "scope": "tag records; aliases and AB quantities require confirmation",
        "complete": counts["unpriced"] == 0,
        "review_queue": queue,
    }
