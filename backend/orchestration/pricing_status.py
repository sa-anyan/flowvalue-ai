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
    # A reference is visible numerically but never changes the canonical cost lines.
    by_key = {
        r.get("parsed_source", {}).get("equipment_key"): r
        for r in result.get("equipment", [])
    }
    resolved_aliases = set()
    for row in result.get("equipment", []):
        key = row.get("parsed_source", {}).get("equipment_key")
        proposal = proposals.get(key, {})
        price = proposal.get("manual_price") or {}
        row["cost_status"] = (
            price.get("cost_status", "catalogue_estimate")
            if row.get("equipment_cost") is not None
            else "unresolved"
        )
        if row.get("equipment_cost") is not None and price.get("cost_status"):
            row["status"] = price["cost_status"]
        if not row.get("parsed_source", {}).get("confirmed_alias"):
            continue
        target = by_key.get(proposal.get("alias_of"), {})
        if target.get("equipment_cost") is None:
            continue
        estimate = (target.get("calculation") or {}).get("estimate") or {}
        row.update(
            status="alias_reference",
            cost_status="alias_reference",
            additional_purchase_cost=0,
            reference_cost={
                "equipment_key": proposal["alias_of"],
                "equipment_tag": target["equipment_tag"],
                "purchase_cost": target["equipment_cost"],
                "installed_cost": target.get("equipment_and_installation_cost"),
                "currency": estimate.get("currency"),
                "price_period": estimate.get("period"),
                "additional_cost": 0,
            },
        )
        row["decision"].update(
            pricing="alias_reference",
            cost_method="alias_reference",
            matching="canonical_reference",
            blockers=[],
            next_action="review_provisional_alias",
        )
        resolved_aliases.add(row["equipment_tag"])
    coverage = result["pricing_coverage"]
    coverage["alias_references"] = len(resolved_aliases)
    coverage["unpriced"] -= len(resolved_aliases)
    coverage["resolved_records"] = coverage["priced"] + len(resolved_aliases)
    coverage["complete"] = coverage["unpriced"] == 0
    coverage["review_queue"] = [
        r
        for r in coverage["review_queue"]
        if r["equipment_tag"] not in resolved_aliases
    ]
    if resolved_aliases and coverage["complete"]:
        from math import fsum

        purchased = [
            r for r in result["equipment"] if r.get("equipment_cost") is not None
        ]
        bases = {
            ((r.get("calculation") or {}).get("estimate") or {}).get("currency", "")
            + ":"
            + ((r.get("calculation") or {}).get("estimate") or {}).get("period", "")
            for r in purchased
        }
        if len(bases) == 1:
            result["equipment_cost_total"] = fsum(
                r["equipment_cost"] for r in purchased
            )
            result["status"] = "calculated_preliminary"
            result["alias_notice"] = (
                "Confirmed scenario aliases reference priced assets and contribute no additional purchased cost. Installation completeness remains separate."
            )
