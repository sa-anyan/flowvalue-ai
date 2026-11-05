"""Normalise AI transport envelopes before canonical equipment calculations."""


def equipment_rows(value, report):
    # Both forms have been returned by the existing generic JSON section API.
    if isinstance(value, dict):
        if set(value) != {"equipment"}:
            raise ValueError(
                "Equipment proposal must be a list or an equipment-list object"
            )
        value = value["equipment"]
    if not isinstance(value, list):
        raise ValueError("Equipment proposal must contain a list of equipment rows")

    known = {
        e["key"] for e in report.get("entities", []) if e.get("kind") == "equipment"
    }
    rows, issues, seen = [], [], set()
    for index, row in enumerate(value, 1):
        if not isinstance(row, dict):
            issues.append(
                f"Equipment proposal row {index} is not an object; skipped. Other equipment can still calculate."
            )
            continue
        key = row.get("equipment_key")
        if not isinstance(key, str) or key not in known or key in seen:
            issues.append(
                f"Equipment proposal row {index} has a missing, unknown or duplicate equipment key; skipped."
            )
            continue
        rows.append(row)
        seen.add(key)
    return rows, issues
