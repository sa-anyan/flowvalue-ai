"""P6 M6.5 deterministic 2D connection proposal selection.

All outputs are proposals, never verified physical pipework.
"""


def proposed_links(report):
    """Select only uniquely resolved, non-conflicting directed associations."""
    equipment = {
        entity["key"] for entity in report.get("entities", [])
        if entity.get("kind") == "equipment"
    }
    links = []
    for stream in report.get("entities", []):
        if stream.get("kind") == "equipment":
            continue
        relations = [
            connection for connection in report.get("connections", [])
            if connection.get("stream_key") == stream.get("key")
        ]
        endpoints = {}
        for role in ("source", "destination"):
            candidates = [
                edge for edge in relations
                if edge.get("role") == role
                and edge.get("equipment_key") in equipment
                and edge.get("status") != "unresolved"
            ]
            keys = {edge["equipment_key"] for edge in candidates}
            # Ambiguity anywhere in the endpoint evidence must remain visible.
            all_role = [edge for edge in relations if edge.get("role") == role]
            if len(keys) != 1 or any(
                edge.get("status") == "unresolved" for edge in all_role
            ):
                break
            endpoints[role] = (next(iter(keys)), candidates)
        if len(endpoints) != 2:
            continue
        source, source_evidence = endpoints["source"]
        destination, destination_evidence = endpoints["destination"]
        if source == destination:
            continue
        links.append({
            "stream_key": stream["key"],
            "source_equipment_key": source,
            "destination_equipment_key": destination,
            "evidence_ids": list(dict.fromkeys(
                evidence_id
                for edge in [*source_evidence, *destination_evidence]
                for evidence_id in edge.get("evidence_ids", [])
            )),
            "status": "proposed_unverified",
            "physical_connection_verified": False,
        })
    return links
