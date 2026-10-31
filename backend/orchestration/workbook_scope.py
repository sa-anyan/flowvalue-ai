"""A calculation view of the register; original extraction is never discarded."""

import copy


def calculation_scope(report, decisions):
    sheets = {s["name"] for s in report.get("sheets", [])}
    selected = {}
    for item in decisions:
        if item["sheet"] not in sheets or item["role"] not in {
            "active",
            "supporting",
            "reference",
        }:
            raise ValueError(
                "Scope must reference an actual worksheet and supported role"
            )
        if item["sheet"] in selected:
            raise ValueError("Conflicting worksheet classifications require review")
        selected[item["sheet"]] = item
    active = {k for k, v in selected.items() if v["role"] == "active"}
    if not active:
        raise ValueError("At least one active process worksheet must be selected")
    result = copy.deepcopy(report)
    kept, aliases, fingerprints, identities = [], {}, {}, {}
    for entity in report["entities"]:
        sheet = entity["id_evidence"]["sheet"]
        if sheet not in active:
            continue
        # Only duplicate observations of the SAME source identity are coalesced.
        # Equal tag names in different operating cases are not automatically merged.
        fingerprint = (
            entity["kind"],
            entity.get("case", ""),
            sheet,
            entity["id_evidence"]["cell"],
            entity["identifier"].strip().casefold(),
        )
        if fingerprint in fingerprints:
            aliases[entity["key"]] = fingerprints[fingerprint]["key"]
            target = fingerprints[fingerprint]
            existing = {v["id"] for v in target["values"]}
            target["values"].extend(
                copy.deepcopy(v) for v in entity["values"] if v["id"] not in existing
            )
            continue
        item = copy.deepcopy(entity)
        item["values"] = [v for v in item["values"] if v["sheet"] in active]
        fingerprints[fingerprint] = item
        kept.append(item)
        identity = (
            item["kind"],
            item["identifier"].strip().casefold(),
            item.get("case", ""),
        )
        identities.setdefault(identity, []).append(item)
    notes = []
    for entity in report["entities"]:
        sheet = entity["id_evidence"]["sheet"]
        choice = selected.get(sheet, {})
        if choice.get("role") != "supporting" or entity["key"] not in choice.get(
            "needed_entity_keys", []
        ):
            continue
        identity = (
            entity["kind"],
            entity["identifier"].strip().casefold(),
            entity.get("case", ""),
        )
        matches = identities.get(identity, [])
        if len(matches) != 1:
            notes.append(
                "Supporting record not merged without unique active identity: "
                + entity["identifier"]
            )
            continue
        target = matches[0]
        for value in entity["values"]:
            prop = (value["property"], value.get("component"))
            current = [
                v
                for v in target["values"]
                if (v["property"], v.get("component")) == prop
            ]
            if not current:
                target["values"].append(copy.deepcopy(value))
            elif any(
                (v.get("normalized_value"), v.get("normalized_unit"))
                != (value.get("normalized_value"), value.get("normalized_unit"))
                for v in current
            ):
                notes.append(
                    "Conflicting supporting observation retained outside calculation: "
                    + entity["identifier"]
                    + "/"
                    + value["property"]
                )
    keys = {e["key"] for e in kept}
    for item in kept:
        item["stream_keys"] = list(
            dict.fromkeys(
                aliases.get(k, k)
                for k in item.get("stream_keys", [])
                if aliases.get(k, k) in keys
            )
        )
    result["entities"] = kept
    result["connections"] = [
        dict(
            c,
            stream_key=aliases.get(c["stream_key"], c["stream_key"]),
            equipment_key=aliases.get(c.get("equipment_key"), c.get("equipment_key")),
        )
        for c in report.get("connections", [])
        if aliases.get(c["stream_key"], c["stream_key"]) in keys
        and aliases.get(c.get("equipment_key"), c.get("equipment_key")) in keys
    ]
    result["product_candidates"] = [
        p for p in report.get("product_candidates", []) if p["stream_key"] in keys
    ]
    result["calculation_scope"] = {
        "worksheets": list(selected.values()),
        "aliases": aliases,
        "excluded_entity_count": len(report["entities"]) - len(kept),
        "notes": notes,
    }
    # Do not inherit balance-validation claims for a different physical boundary.
    result["checks"] = [{"name": name, "scope": "Selected calculation worksheets", "status": "unresolved",
                         "message": "Reconfirm the complete physical boundary and source terms for this selected register; worksheet selection is not balance verification.",
                         "residual": None, "unit": None, "evidence_ids": []}
                        for name in ("Overall mass balance", "Component mass balances", "Energy balance")]
    result["scope_notes"] = (
        report.get("scope_notes", [])
        + notes
        + [
            "Calculation view excludes reference worksheets; no independent mass/energy balance verification is implied."
        ]
    )
    return result
