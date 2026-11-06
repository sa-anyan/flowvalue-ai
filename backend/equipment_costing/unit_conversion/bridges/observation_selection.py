"""Choose direct cell observations over conflicting AI interpretations, with audit.

This never changes observations. Competing direct readings remain unresolved.
Equivalent duplicate readings can share a calculation basis without counting twice.
"""

import math


def select_observation(candidates, unit, convert, choice=None):
    if choice:
        if not isinstance(choice, dict):
            raise ValueError("Explicit source choice must be a structured selection")
        selected = next(
            (v for v in candidates if v["id"] == choice.get("measurement_id")), None
        )
        if selected is None or not str(choice.get("rationale", "")).strip():
            raise ValueError(
                "Explicit source choice needs an available matching observation and rationale"
            )
        return selected, {
            "policy": "explicit_provisional_source_choice",
            "selected": selected,
            "rationale": choice["rationale"],
            "alternatives_retained": [
                v for v in candidates if v["id"] != selected["id"]
            ],
            "notice": "Selected scenario basis, not a correction or validation of conflicting source data.",
        }
    if not candidates:
        return None, None
    if len(candidates) == 1:
        return candidates[0], None
    direct = [
        v
        for v in candidates
        if v.get("status") == "verified"
        and v.get("sheet")
        and v.get("cell")
        and not str(v.get("id", "")).startswith("ai-evidence:")
    ]
    pool = direct or candidates
    values = [convert(v["value"], v["unit"], unit) for v in pool]
    if any(v is None or not math.isfinite(v) for v in values) or not all(
        math.isclose(v, values[0], rel_tol=1e-9, abs_tol=1e-9) for v in values
    ):
        raise ValueError(
            "Conflicting equally supported observations; choose a source basis explicitly"
        )
    selected = pool[0]
    return selected, {
        "policy": (
            "direct_cell_over_inferred_interpretation"
            if len(direct) < len(candidates) and direct
            else "equivalent_duplicate_readings"
        ),
        "selected": selected,
        "alternatives_retained": [v for v in candidates if v["id"] != selected["id"]],
        "notice": "Calculation basis selected without altering source data. Conflicting interpretations remain available for review; this is not engineering validation.",
    }
