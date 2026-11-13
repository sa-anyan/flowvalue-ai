"""Project record and reviewed asset identity without affecting costing scope."""

from collections import Counter

from backend.equipment_resolution.duplicates import token
from backend.equipment_resolution.scope import confirmed


def identity_register(source, expanded, plan, duplicate_review, original_plan):
    """Keep original records even when the costing convention excludes them."""
    records = {
        e["key"]: e
        for report in (source, expanded)
        for e in report.get("entities", [])
        if e["kind"] == "equipment"
    }
    tags = Counter(token(e["identifier"]) for e in records.values())
    proposals = {row["equipment_key"]: row for row in plan.get("equipment", [])}
    original_proposals = {row["equipment_key"]: row for row in original_plan.get("equipment", [])}
    active = {e["key"] for e in expanded.get("entities", [])}
    conflicts = {
        key
        for entry in duplicate_review
        for key in (entry["equipment_key"], entry["retained_equipment_key"])
    }
    mappings = {}
    for key, row in proposals.items():
        target = row.get("alias_of")
        if (
            key in active
            and target in active
            and row.get("scope_decision") == "alias"
            and confirmed(row)
            and proposals.get(target, {}).get("quantity") == 1
        ):
            mappings[key] = (
                target, row.get("alias_confirmation") or row["scope_confirmation"]
            )
    for target, confirmation in list(mappings.values()):
        mappings.setdefault(target, (target, confirmation))
    for key in active:
        entity = records.get(key)
        row = proposals.get(key, {})
        if entity and entity.get("parent_equipment_key") and row.get("asset_id"):
            parent = entity["parent_equipment_key"]
            parent_row = original_proposals.get(parent, {})
            if confirmed(parent_row):
                mappings[key] = (
                    key,
                    parent_row.get("alias_confirmation")
                    or parent_row["scope_confirmation"],
                )
    aliases = {}
    for key, (target, _) in mappings.items():
        aliases.setdefault(target, []).append(records[key]["identifier"])
    result = []
    for key, entity in records.items():
        evidence = [entity.get("id_evidence") or {}, *entity.get("values", [])]
        target, review = mappings.get(key, (None, None))
        tag = entity["identifier"]
        collision = (
            key in conflicts
            or (bool(token(tag)) and tags[token(tag)] > 1)
            or any(v.get("property") == "identifier" for v in evidence[1:])
        )
        result.append(
            {
                "equipment_key": key,
                "display_tag": tag,
                "physical_asset_id": target,
                "status": "resolved" if target else "ambiguous" if collision else "unresolved",
                "aliases": list(dict.fromkeys(aliases.get(target, []))),
                "observation_ids": list(dict.fromkeys(
                    v["observation_id"] for v in evidence if v.get("observation_id")
                )),
                "legacy_evidence_ids": list(dict.fromkeys(v["id"] for v in evidence if v.get("id"))),
                "review": review,
            }
        )
    return {
        "source_sha256": source.get("sha256"),
        "parser_version": source.get("parser_version"),
        "equipment": result,
    }


def project_assessment_identity(response, saved=None):
    """Add legacy identity to a response, without writing or recalculating."""
    from copy import deepcopy

    from backend.ingestion.observation_identity import project_report_evidence

    response = deepcopy(response)
    saved = response if saved is None else saved

    def reports(state):
        return (
            state.get("scoped_report"),
            state.get("effective_report"),
            (state.get("stage_outputs", {}).get("engineering_data") or {}).get("report"),
            (state.get("parsed") or {}).get("report"),
        )

    for report in reports(response):
        if report:
            project_report_evidence(report)
    source = next((report for report in reports(saved) if report), {})
    source = deepcopy(source)
    project_report_evidence(source)
    equipment = (response.get("results") or {}).get("stages", {}).get("equipment")
    historical = ((saved.get("results") or {}).get("stages", {}).get("equipment") or {}).get("result")
    result = (equipment or {}).get("result")
    if isinstance(result, dict) and "identity_register" in result:
        return response
    if isinstance(historical, dict) and "identity_register" in historical:
        register = deepcopy(historical["identity_register"])
    else:
        entities = {
            e["key"]: e for e in source.get("entities", [])
            if e.get("kind") == "equipment" and e.get("key")
        }
        unkeyed = []
        priced = historical if isinstance(historical, dict) else result
        for line in (priced or {}).get("equipment", []):
            parsed = line.get("parsed_source") or {}
            key = parsed.get("equipment_key") or line.get("equipment_key")
            if key:
                entities.setdefault(key, {
                    "key": key,
                    "kind": "equipment",
                    "identifier": line.get("equipment_tag", ""),
                    "values": deepcopy(parsed.get("evidence") or []),
                })
            else:
                unkeyed.append({
                    "equipment_key": None,
                    "display_tag": line.get("equipment_tag", ""),
                    "physical_asset_id": None,
                    "status": "unresolved",
                    "aliases": [],
                    "observation_ids": [],
                    "legacy_evidence_ids": [],
                    "review": None,
                    "identity_limitation": "historical_equipment_key_unavailable",
                })
        source["entities"] = list(entities.values())
        project_report_evidence(source)
        if not (entities or unkeyed):
            return response
        register = identity_register(
            source, source, {}, (priced or {}).get("duplicate_review") or [], {}
        )
        register["equipment"].extend(unkeyed)
    if isinstance(result, dict):
        result["identity_register"] = register
    elif isinstance(equipment, dict):
        equipment["identity_register"] = register
    else:
        response["identity_register"] = register
    return response
