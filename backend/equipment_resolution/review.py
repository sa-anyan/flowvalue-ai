"""One equipment resolution register for deterministic studies and Monte Carlo."""

from backend.orchestration.sizing import derive_size

from .scope import confirmed, expand


def review(report, plan, results=None, *, expanded=False):
    if not expanded:
        report, plan = expand(report, plan)
    proposals = {r.get("equipment_key"): r for r in plan.get("equipment", [])}
    lines = (
        (results or {}).get("stages", {}).get("equipment", {}).get("result") or {}
    ).get("equipment", [])
    by_key = {r.get("parsed_source", {}).get("equipment_key"): r for r in lines}
    rows = []
    for entity in report["entities"]:
        if entity["kind"] != "equipment":
            continue
        key = entity["key"]
        proposal = proposals.get(key, {})
        line = by_key.get(key, {})
        alias = proposal.get("scope_decision") == "alias"
        accepted_alias = alias and confirmed(proposal)
        method = (
            "manual_user_price"
            if proposal.get("manual_price")
            else "engineering_analogy"
            if (proposal.get("external_quote") or {}).get("method")
            == "engineering_analogy"
            else "documented_benchmark"
            if proposal.get("external_quote")
            else "direct_correlation"
            if proposal.get("curve_id")
            else None
        )
        priced = line.get("amount") is not None
        status = (
            {
                "manual_user_price": "PRICED — USER",
                "engineering_analogy": "PRICED — ANALOGY",
                "documented_benchmark": "PRICED — BENCHMARK",
                "direct_correlation": "PRICED — MODEL",
            }.get(method, "UNRESOLVED")
            if priced
            else "UNRESOLVED"
        )
        issues = list(line.get("issues", []))
        size, unit, sizing = None, None, None
        if line:
            sizing = line.get("parsed_source", {}).get("sizing")
            estimate = (line.get("calculation") or {}).get("estimate") or {}
            size, unit = (
                estimate.get("size", proposal.get("size")),
                estimate.get("size_unit", proposal.get("size_unit")),
            )
        elif not alias:
            try:
                size, unit, sizing = derive_size(proposal, report)
            except (ValueError, TypeError, KeyError, ArithmeticError) as exc:
                issues.append(str(exc))
        rows.append(
            {
                "equipment_key": key,
                "tag": entity["identifier"],
                "parent_equipment_key": entity.get("parent_equipment_key"),
                "stream_keys": entity.get("stream_keys", []),
                "interpretation": "confirmed_alias"
                if accepted_alias
                else "proposed_alias"
                if alias
                else proposal.get("asset_relationship", "registered_asset"),
                "alias_of": proposal.get("alias_of"),
                "quantity": proposal.get("quantity", 1),
                "quantity_rationale": proposal.get(
                    "quantity_rationale",
                    "Unspecified: suffix conventions are not evidence",
                ),
                "status": status,
                "cost_method": method,
                "selected_model": proposal.get("curve_id"),
                "candidate_models": proposal.get("candidate_curve_ids", []),
                "size": size,
                "size_unit": unit,
                "sizing": sizing,
                "rationale": proposal.get(
                    "rationale", "No engineering selection available"
                ),
                "source": entity.get("values", [])
                + ([entity["id_evidence"]] if entity.get("id_evidence") else []),
                "issues": list(dict.fromkeys(issues)),
                "confidence": "User-approved assumption; uncalibrated"
                if proposal.get("manual_price")
                else "Preliminary, not independently validated",
                "purchased_cost": line.get("equipment_cost"),
                "installed_cost": line.get("equipment_and_installation_cost"),
                "requires_user_input": not accepted_alias and (not priced or alias),
            }
        )
    counted = [r for r in rows if r["interpretation"] != "confirmed_alias"]
    quantities_valid = all(
        isinstance(r["quantity"], (int, float))
        and not isinstance(r["quantity"], bool)
        and r["quantity"] >= 1
        and float(r["quantity"]).is_integer()
        for r in counted
    )
    return {
        "items": rows,
        "registered_records": len(rows),
        "confirmed_aliases": len(rows) - len(counted),
        "physical_asset_count": sum(int(r["quantity"]) for r in counted)
        if quantities_valid
        else None,
        "scope_status": "needs_review"
        if any(r["interpretation"] == "proposed_alias" for r in rows)
        else "registered_scope_only",
        "priced_records": sum(r["status"].startswith("PRICED") for r in counted),
        "costable_records": len(counted),
        "requires_user_input": sum(r["requires_user_input"] for r in counted),
        "notice": "Counts cover registered and explicitly split assets only. Quantity and project completeness require engineering review. Missing prices are not zero.",
    }
