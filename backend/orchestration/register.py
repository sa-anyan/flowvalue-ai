"""Value-by-value assumption lineage, inherited from the reviewed stage proposal."""


def register(plan, metadata):
    rows = []

    def walk(value, path, inherited):
        if isinstance(value, dict):
            context = dict(inherited)
            for key in ("unit", "rationale", "source", "uncertainty", "status"):
                if key in value and not isinstance(value[key], (dict, list)):
                    context[key] = value[key]
            for key, item in value.items():
                walk(item, path + [key], context)
        elif isinstance(value, list):
            for i, item in enumerate(value):
                walk(item, path + [str(i)], inherited)
        else:
            rows.append(dict(path=".".join(path), value=value, **inherited))

    for section, value in plan.items():
        meta = metadata.get(section, {})
        inherited = {
            "origin": meta.get("origin", "unresolved"),
            "unit": meta.get("units", ""),
            "rationale": meta.get("rationale", "No assumption supplied"),
            "evidence_ids": meta.get("evidence_ids", []),
            "uncertainty": meta.get("uncertainty", "Unresolved"),
            "status": meta.get("status", "unresolved"),
        }
        walk(value, [section], inherited)
    return rows


def mark_ai(value, *, evidence_ids=()):
    """Keep engineering interpretations useful; distinguish assumptions from source facts.

    Source-backed values are preserved only with references to actual evidence.
    AI decisions are not silently promoted to user approval.
    """
    if isinstance(value, list):
        return [mark_ai(v, evidence_ids=evidence_ids) for v in value]
    if not isinstance(value, dict):
        return value
    result = {k: mark_ai(v, evidence_ids=evidence_ids) for k, v in value.items()}
    if "value" in result and "unit" in result:
        supported = result.get("status") == "source_supported" and any(
            key and key in str(result.get("source", "")) for key in evidence_ids
        )
        if not supported:
            result["status"] = "llm_estimate"
            if not result.get("source"):
                result["source"] = "AI engineering scenario; see assumption register"
    if "reviewed" in result:
        result["reviewed"] = False
    # Preserve interpreted boundary, names and proposed quality instead of blanking them.
    if result.get("specification_status") == "confirmed" and not result.get("reviewed"):
        result["specification_status"] = "provisional"
    return result
