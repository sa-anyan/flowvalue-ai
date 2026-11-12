"""Read-only views of the executed sizing audit stored on each equipment row."""

from copy import deepcopy


def sizing_trace(row):
    source = row.get("parsed_source") or {}
    sizing = source.get("sizing") or {}
    nodes = (sizing, sizing.get("calculation") or {}, sizing.get("equation") or {})
    methods = [
        deepcopy(node["engineering_method"])
        for node in nodes
        if isinstance(node.get("engineering_method"), dict)
        and node["engineering_method"]
    ]
    warnings = dict.fromkeys(
        warning for node in nodes
        for warning in node.get("applicability_warnings", [])
    )
    for node in nodes:
        if node.get("volume_basis"):
            warnings[node["volume_basis"]] = None
            if node.get("scope"):
                warnings[node["scope"]] = None
    return {
        "equipment_key": source.get("equipment_key"),
        "status": "versioned" if methods else "unversioned",
        "engineering_methods": methods,
        "applicability_notes": list(warnings),
    }


def project_sizing_traces(state):
    stages = (state.get("results") or {}).get("stages") or {}
    equipment = ((stages.get("equipment") or {}).get("result") or {}).get("equipment")
    if not equipment:
        return state
    return {**state, "equipment_sizing_traces": [sizing_trace(row) for row in equipment]}
