"""Explicit user register changes; original workbook observations remain intact."""

import copy
from uuid import uuid4
from backend.ingestion.balance.models import Entity, Evidence
from backend.ingestion.engineering_register import stable_key


def apply_edit(report, edit):
    report = copy.deepcopy(report)
    key = edit.get("equipment_key") or "user-equipment:" + uuid4().hex
    entity = next(
        (e for e in report["entities"] if e["key"] == key and e["kind"] == "equipment"),
        None,
    )
    if edit["action"] == "update" and entity is None:
        raise ValueError("Equipment not found")
    if edit["action"] == "add" and entity is not None:
        raise ValueError("Equipment already exists")
    if edit["action"] == "remove":
        if entity is None:
            raise ValueError("Equipment not found")
        report["entities"] = [e for e in report["entities"] if e["key"] != key]
        report["connections"] = [
            c for c in report.get("connections", []) if c.get("equipment_key") != key
        ]
        return report, key
    tag = str(edit.get("tag") or (entity or {}).get("identifier", "")).strip()
    name = str(edit.get("name") or tag).strip()
    if not tag or len(tag) > 128 or not name:
        raise ValueError("A tag and equipment name are required")
    if any(
        e["kind"] == "equipment"
        and e["identifier"].casefold() == tag.casefold()
        and e["key"] != key
        for e in report["entities"]
    ):
        raise ValueError("That equipment tag already exists")

    existing = {}
    if entity is not None:
        for item in [entity.get("id_evidence") or {}, *entity.get("values", [])]:
            if str(item.get("id", "")).startswith("user-input:"):
                existing.setdefault(item["property"], []).append(item)

    def evidence(prop, value):
        matches = existing.get(prop, [])
        previous = matches[0] if len(matches) == 1 else {}
        stable_id = stable_key("user-input", key, prop)
        record_id = previous.get("id") or stable_id
        revision = previous.get("observation_revision") or 0
        if not revision or previous.get("original_value") != value:
            revision += 1
        receipt = edit.get("observation_receipts", {}).get(prop, {})
        return Evidence(
            id=receipt.get("id", record_id),
            observation_id=receipt.get("observation_id", previous.get("observation_id") or stable_id),
            observation_revision=receipt.get("observation_revision", revision),
            observation_method="manual-engineering-register-1",
            workbook="User input",
            sheet="User register",
            cell="manual",
            property=prop,
            label=prop,
            original_value=value,
            normalized_value=value,
            status="inferred",
            note="Explicit user entry; not extracted from a workbook or independently verified.",
        ).model_dump(mode="json")

    if entity is None:
        entity = Entity(
            key=key,
            kind="equipment",
            identifier=tag,
            table="user-register",
            id_evidence=Evidence.model_validate(evidence("identifier", tag)),
        ).model_dump(mode="json")
        report["entities"].append(entity)
    entity["identifier"] = tag
    if "identifier" in existing:
        entity["id_evidence"] = evidence("identifier", tag)
    entity["values"] = [
        v
        for v in entity.get("values", [])
        if not str(v.get("id", "")).startswith("user-input:")
    ] + [evidence("name", name), evidence("type", name)]
    return report, key


def save_edit(store, key, revision, edit):
    from backend.blocks.execution import fresh, _digest, refresh

    state = store.get(key)
    if state.get("running") or state["revision"] != revision:
        raise ValueError("Assessment changed or is running; reload before editing")
    if not fresh(state, "engineering_data"):
        raise ValueError("Extract engineering data first")
    report, entity_key = apply_edit(
        state["stage_outputs"]["engineering_data"]["report"], edit
    )
    store.version(key, "Before user equipment register edit")
    recorded_edit = {**edit, "equipment_key": entity_key}
    if edit["action"] != "remove":
        entity = next(e for e in report["entities"] if e["key"] == entity_key)
        recorded_edit["observation_receipts"] = {
            evidence["property"]: {
                field: evidence[field]
                for field in ("id", "observation_id", "observation_revision")
            }
            for evidence in [entity["id_evidence"], *entity["values"]]
            if evidence.get("observation_revision")
        }
    state.setdefault("engineering_register_edits", []).append(recorded_edit)
    state["stage_outputs"]["engineering_data"]["report"] = report
    state["stage_runs"]["engineering_data"]["output_hash"] = _digest(
        state["stage_outputs"]["engineering_data"]
    )
    state["effective_report"] = report
    state.pop("scoped_report", None)
    state["results"]["stages"]["engineering_data"]["result"]["equipment_count"] = sum(
        e["kind"] == "equipment" for e in report["entities"]
    )
    if edit["action"] == "remove":
        state["plan"]["equipment"] = [
            r
            for r in state["plan"].get("equipment", [])
            if r.get("equipment_key") != entity_key
        ]
    refresh(state)
    return store.put(state, revision)
