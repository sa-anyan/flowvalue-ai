"""Explicit asset decisions, independent of tag suffix conventions.

No alias, split or duty/standby quantity is inferred from spelling alone.
Source workbook entities remain immutable; expanded entities are scenario views.
"""

import copy


def confirmed(row):
    decision = row.get("alias_confirmation") or row.get("scope_confirmation") or {}
    return decision.get("status") in {
        "user_confirmed",
        "user_confirmed_for_simulation",
        "user_confirmed_distinct",
    } and bool(str(decision.get("rationale", "")).strip())


def expand(report, plan):
    if not any(
        r.get("physical_assets")
        or (r.get("scope_decision") == "alias" and confirmed(r))
        for r in plan.get("equipment", [])
    ):
        keys = [r.get("equipment_key") for r in plan.get("equipment", [])]
        if len(keys) != len(set(keys)):
            raise ValueError("Conflicting duplicate equipment keys in costing plan")
        return report, plan
    report, plan = copy.deepcopy(report), copy.deepcopy(plan)
    entities = {e["key"]: e for e in report["entities"] if e["kind"] == "equipment"}
    used = set(entities)
    rows, replaced, additions = [], set(), []
    for row in plan.get("equipment", []):
        children = row.get("physical_assets")
        if not children:
            rows.append(row)
            continue
        key = row.get("equipment_key")
        if key not in entities or not confirmed(row):
            raise ValueError(
                "Physical asset splitting requires a registered parent and explicit user confirmation"
            )
        if not isinstance(children, list) or not 2 <= len(children) <= 30:
            raise ValueError("A physical split requires between two and thirty assets")
        replaced.add(key)
        for child in children:
            asset_id = child.get("asset_id")
            if (
                not isinstance(asset_id, str)
                or not asset_id.strip()
                or len(asset_id) > 100
            ):
                raise ValueError("Every split asset needs a stable asset_id")
            child_key = key + "::" + asset_id
            if child_key in used:
                raise ValueError("Duplicate physical asset identifier")
            used.add(child_key)
            tag = child.get("equipment_tag")
            if not isinstance(tag, str) or not tag.strip():
                raise ValueError("Each physical asset needs an explicit display tag")
            entity = copy.deepcopy(entities[key])
            entity.update(key=child_key, identifier=tag, parent_equipment_key=key)
            if "stream_keys" in child:
                if not set(child["stream_keys"]) <= set(
                    entities[key].get("stream_keys", [])
                ):
                    raise ValueError(
                        "Split assets cannot manufacture source stream connections"
                    )
                entity["stream_keys"] = child["stream_keys"]
            # Parent observations are not automatically measurements of every child.
            entity["stream_keys"] = child.get("stream_keys", [])
            evidence_ids = set(child.get("source_value_ids", []))
            source_values = entities[key].get("values", [])
            if not evidence_ids <= {v["id"] for v in source_values}:
                raise ValueError(
                    "Split source values must reference existing parent evidence"
                )
            entity["values"] = [v for v in source_values if v["id"] in evidence_ids]
            entity["status"] = "inferred_user_split"
            if entity.get("id_evidence"):
                entity["id_evidence"]["note"] = (
                    "Parent tag evidence retained; separate child identity is a user-confirmed interpretation, not an additional workbook measurement."
                )
            additions.append(entity)
            rows.append(
                {**child, "equipment_key": child_key, "parent_equipment_key": key}
            )
    report["entities"] = [
        e for e in report["entities"] if e["key"] not in replaced
    ] + additions
    connections, unresolved = [], list(report.get("scope_unresolved_connections", []))
    for connection in report.get("connections", []):
        parent = connection.get("equipment_key")
        if parent not in replaced:
            connections.append(connection)
            continue
        assigned = [
            e
            for e in additions
            if e.get("parent_equipment_key") == parent
            and connection.get("stream_key") in e.get("stream_keys", [])
        ]
        if not assigned:
            unresolved.append({**connection, "status": "unresolved_split_connection"})
        for entity in assigned:
            connections.append(
                {
                    **connection,
                    "equipment_key": entity["key"],
                    "parent_equipment_key": parent,
                    "status": "user_interpreted_source_connection",
                }
            )
    report["connections"] = connections
    report["scope_unresolved_connections"] = unresolved
    plan["equipment"] = rows
    by_key = {r.get("equipment_key"): r for r in rows}
    if len(by_key) != len(rows):
        raise ValueError("Conflicting duplicate equipment keys in costing plan")
    registered = {e["key"] for e in report["entities"] if e["kind"] == "equipment"}
    for row in rows:
        if row.get("scope_decision") != "alias" or not confirmed(row):
            continue
        visited = {row["equipment_key"]}
        target = row.get("alias_of")
        while True:
            if target not in registered or target not in by_key or target in visited:
                raise ValueError("Confirmed alias target missing or cyclic")
            visited.add(target)
            next_row = by_key[target]
            if next_row.get("scope_decision") != "alias":
                break
            if not confirmed(next_row):
                raise ValueError(
                    "Confirmed alias cannot terminate at an unconfirmed alias"
                )
            target = next_row.get("alias_of")
        row["alias_of"] = target
    return report, plan


def equipment_paths(plan):
    """Yield shared-ledger targets, including independently editable split assets."""
    for i, row in enumerate(plan.get("equipment", [])):
        if row.get("physical_assets") and confirmed(row):
            for j, child in enumerate(row["physical_assets"]):
                yield (
                    ["equipment", i, "physical_assets", j],
                    {
                        **child,
                        "equipment_key": row["equipment_key"]
                        + "::"
                        + child["asset_id"],
                    },
                )
        else:
            yield ["equipment", i], row
