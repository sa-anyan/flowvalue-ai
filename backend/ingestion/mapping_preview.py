"""Read-only M6.4 evidence preview. No approval, mutation, or engineering arithmetic."""

from collections import Counter


def preview(report):
    """Return source-to-normalized observations without modifying the parsed report.

    The preview is advisory: source-supported does not mean plant-verified.
    """
    entities = report.get("entities", [])
    observations = []
    for entity in entities:
        for evidence in [entity.get("id_evidence"), *entity.get("values", [])]:
            if not evidence:
                continue
            original = evidence.get("original_value")
            normalized = evidence.get("normalized_value")
            status = evidence.get("status", "unresolved")
            observations.append({
                "entity_key": entity["key"],
                "entity_kind": entity["kind"],
                "entity_identifier": entity["identifier"],
                "case": entity.get("case", ""),
                "evidence_id": evidence["id"],
                "source": {
                    "workbook": evidence.get("workbook"),
                    "sheet": evidence.get("sheet"),
                    "cell": evidence.get("cell"),
                    "property": evidence.get("property"),
                    "component": evidence.get("component"),
                    "value": original,
                    "unit": evidence.get("original_unit"),
                    "formula": evidence.get("formula"),
                    "cached": evidence.get("cached", False),
                },
                "proposed": {
                    "value": normalized,
                    "unit": evidence.get("normalized_unit"),
                    "status": status,
                },
                "needs_review": (
                    status != "verified" or original is None or normalized is None
                ),
            })
    # Only an explicit scoped identity is meaningful; a display tag can repeat.
    duplicates = Counter(
        (entity.get("kind"), entity.get("identifier"), entity.get("case", ""))
        for entity in entities
    )
    return {
        "schema": "p6-m64-readonly-preview-v1",
        "source_sha256": report.get("sha256"),
        "parser_version": report.get("parser_version"),
        "observations": observations,
        "issues": list(report.get("issues", [])),
        "checks": list(report.get("checks", [])),
        "connections": [
            {
                "stream_key": edge.get("stream_key"),
                "equipment_key": edge.get("equipment_key"),
                "role": edge.get("role"),
                "basis": edge.get("basis"),
                "status": edge.get("status"),
                "evidence_ids": list(edge.get("evidence_ids", [])),
                "verified_physical_link": False,
            }
            for edge in report.get("connections", [])
        ],
        "repeated_display_tags": [
            {"kind": kind, "identifier": identifier, "case": case, "count": count}
            for (kind, identifier, case), count in duplicates.items()
            if count > 1
        ],
        "notice": (
            "Read-only source mapping preview. Verified source observations are not "
            "certified plant measurements; connectivity is not independently verified."
        ),
    }
