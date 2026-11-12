"""Separate equipment identity, candidate matching, sizing and price coverage."""

from backend.equipment_costing.models import priced_record


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
        priced = priced_record(row)
        alias = p.get("scope_decision") == "alias"
        counts["priced" if priced else "unpriced"] += 1
        counts["alias_proposals"] += int(alias)
        issues = row.get("issues", [])
        sizing = row.get("parsed_source", {}).get("sizing")
        status = {
            "identification": "registered",
            "cost_method": (
                "PRICED — USER"
                if priced and p.get("manual_price")
                else (
                    "PRICED — ANALOGY"
                    if priced
                    and (p.get("external_quote") or {}).get("method")
                    == "engineering_analogy"
                    else (
                        "PRICED — BENCHMARK"
                        if priced and p.get("external_quote")
                        else "PRICED — MODEL" if priced else "UNRESOLVED"
                    )
                )
            ),
            "matching": (
                "selected"
                if row.get("curve_id")
                else "candidate_available" if candidates else "unresolved"
            ),
            "candidate_curve_ids": candidates,
            "selected_curve_id": row.get("curve_id"),
            "sizing": (
                "calculated"
                if sizing
                else "direct_input" if p.get("size") is not None else "needs_review"
            ),
            "pricing": (
                "assumption_based_estimate"
                if priced
                else "alias_review" if alias else "unpriced"
            ),
            "scope_decision": p.get("scope_decision", "include"),
            "alias_of": p.get("alias_of"),
            "rationale": p.get("rationale", "No engineering selection returned"),
            "blockers": issues if not priced else [],
            "sizing_evidence": sizing,
            "next_action": (
                "review_assumptions"
                if priced
                else (
                    "confirm_alias"
                    if alias
                    else (
                        "review_sizing" if candidates else "offer_opt_in_model_research"
                    )
                )
            ),
        }
        row["decision"] = status
        match = p.get("matching")
        if match:
            status["conceptual_matching"] = match
            status["matching"] = match["match_status"] + " · " + match["match_method"]
            status["rationale"] = match["reason"]
            status["candidate_curve_ids"] = match["candidate_model_ids"]
            if match["match_status"] != "matched":
                status.update(
                    next_action="review_conceptual_match", blockers=[match["reason"]]
                )
            elif not priced:
                status["next_action"] = "supply_sizing_or_select_configuration"
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
            if priced_record(row)
            else "unresolved"
        )
        if row.get("equipment_cost") is not None and price.get("cost_status"):
            row["status"] = price["cost_status"]
        if not row.get("parsed_source", {}).get("confirmed_alias"):
            continue
        target = by_key.get(proposal.get("alias_of"), {})
        if not target:
            continue
        estimate = (target.get("calculation") or {}).get("estimate") or {}
        row.update(
            status="alias_reference",
            cost_status="alias_reference",
            additional_purchase_cost=0,
            reference_cost={
                "equipment_key": proposal["alias_of"],
                "equipment_tag": target["equipment_tag"],
                "purchase_cost": target.get("equipment_cost"),
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
    for row in result["equipment"]:
        key = row.get("parsed_source", {}).get("equipment_key")
        proposal = proposals.get(key, {})
        calculation = row.get("calculation") or {}
        estimate = calculation.get("estimate") or {}
        evidence = calculation.get("evidence") or {}
        escalation = evidence.get("cost_translation") or {}
        priced = priced_record(row)
        if row.get("parsed_source", {}).get("confirmed_alias"):
            label = "ALIAS — NO ADDITIONAL PURCHASE"
        elif not priced:
            label = "UNPRICED — SOURCE REQUIRED"
        elif evidence.get("applicability_status") == "provisional":
            label = "ESTIMATED — PROVISIONAL MODEL SCOPE"
        elif proposal.get("manual_price"):
            label = "USER-PRICED"
        elif proposal.get("external_quote"):
            label = "ESTIMATED — INDEPENDENT ANALOGY"
        elif (
            proposal.get("sizing")
            or estimate.get("extrapolated")
            or any("UNVERIFIED" in issue for issue in row.get("issues", []))
        ):
            label = "ESTIMATED — ENGINEERING ASSUMPTION"
        else:
            label = "CALCULATED — CORRELATION"
        row["pricing_status"] = label
        row["pricing_provenance"] = {
            "equipment_tag": row["equipment_tag"],
            "classification": row.get("parsed_source", {}).get("classification")
            or estimate.get("equipment"),
            "sizing": row.get("parsed_source", {}).get("sizing"),
            "sizing_parameters": (proposal.get("sizing") or {}).get("parameters", {}),
            "model_id": row.get("curve_id"),
            "source": {
                k: estimate.get(k)
                for k in (
                    "source_title",
                    "source_filename",
                    "source_sha256",
                    "printed_page",
                    "pdf_page",
                )
            },
            "source_record": evidence.get("reference"),
            "formula": estimate.get("formula"),
            "original_cost": escalation.get(
                "original_amount", calculation.get("historical_amount")
            ),
            "original_period": escalation.get("source_period", estimate.get("period")),
            "currency": estimate.get("currency"),
            "purchase_cost": row.get("equipment_cost"),
            "installation_cost": row.get("installation_cost"),
            "installed_cost": row.get("equipment_and_installation_cost"),
            "installation_basis": calculation.get("installation"),
            "escalation": escalation,
            "target_period": estimate.get("period"),
            "reference_cost": row.get("reference_cost"),
            "status": label,
            "unpriced_message": (
                "UNPRICED — SUPPLIER QUOTE OR USER PRICE REQUIRED"
                if not priced and not label.startswith("ALIAS")
                else None
            ),
            "notice": "Escalation adjusts an existing estimate; it does not establish an independent equipment cost. CPI is purchasing-power proxy only.",
        }
        row["decision"]["cost_method"] = label
    # M3.7: source-supported / user evidence / assumption-based / unpriced tiers,
    # and the indicative scale of unpriced items (estimate class applied in CAPEX).
    from backend.capex.coverage_tiers import coverage_tiers, unpriced_significance

    canonical = [
        r for r in result["equipment"]
        if not r.get("parsed_source", {}).get("confirmed_alias")
    ]
    tiers = coverage_tiers(canonical)
    for row in canonical:
        match = next((t for t in tiers["lines"] if t["tag"] == row["equipment_tag"]), None)
        if match:
            row["coverage_tier"] = {k: match[k] for k in ("tier", "reasons", "source_caveats")}
    tiers.pop("lines")
    # Held-out finding 3: units the source names but the register lacks.
    from backend.equipment_resolution.register_completeness import check as register_check

    completeness = register_check(report, "", plan)
    coverage["register_completeness"] = completeness
    if completeness["possibly_missing"]:
        coverage["complete"] = False
        tiers["meets_coverage_target_without_assumptions"] = False
        tiers["register_completeness"] = "unconfirmed: " + ", ".join(
            f["label"] for f in completeness["possibly_missing"])
    coverage["tiers"] = tiers
    coverage["unpriced_significance"] = unpriced_significance(canonical)
