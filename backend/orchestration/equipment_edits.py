"""Equipment PATCH semantics: retain unedited rows/fields, clear only explicit nulls.

Lists inside a row (e.g. derivation bindings) are deliberately replaced when
supplied; mappings merge recursively. Source measurements are never modified.
"""

import copy


def _merge(before, patch):
    if isinstance(before, dict) and isinstance(patch, dict):
        result = copy.deepcopy(before)
        for key, value in patch.items():
            result[key] = _merge(result.get(key), value)
        return result
    return copy.deepcopy(patch)


def merge_equipment_edits(previous, edits):
    if not isinstance(edits, list):
        raise ValueError("Equipment edits must be an array of keyed equipment records")
    keys = []
    for row in edits:
        if (
            not isinstance(row, dict)
            or not isinstance(row.get("equipment_key"), str)
            or not row["equipment_key"].strip()
        ):
            raise ValueError("Every equipment edit requires an equipment_key")
        keys.append(row["equipment_key"])
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate equipment edits are not allowed")
    patches = {r["equipment_key"]: r for r in edits}
    result = [_merge(row, patches.pop(row["equipment_key"], {})) for row in previous]
    result.extend(copy.deepcopy(list(patches.values())))
    return result
