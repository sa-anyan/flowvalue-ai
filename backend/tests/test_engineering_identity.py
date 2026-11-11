from copy import deepcopy
from io import BytesIO

import openpyxl
import pytest

from backend.equipment_resolution.duplicates import reconcile
from backend.equipment_resolution.identity import identity_register
from backend.equipment_resolution.scope import expand
from backend.ingestion.balance.models import BalanceReport
from backend.ingestion.workbook_pipeline import parse_workbook
from backend.orchestration.store import Store
from backend.tests.test_nottingham_parser import workbook


def observation_ids(report):
    return {
        value.observation_id
        for entity in report.entities
        for value in [entity.id_evidence, *entity.values]
    }


def test_source_content_revision_and_observations():
    content = workbook()
    first = parse_workbook(content, "original.xlsx")
    repeated = parse_workbook(content, "renamed.xlsx")
    assert first.sha256 == repeated.sha256
    assert [e.key for e in first.entities] == [e.key for e in repeated.entities]
    assert observation_ids(first) == observation_ids(repeated)
    assert None not in observation_ids(first)
    book = openpyxl.load_workbook(BytesIO(content))
    book.active["F11"] = 30
    edited = BytesIO()
    book.save(edited)
    successor = parse_workbook(
        edited.getvalue(), "original.xlsx", previous_source_sha256=first.sha256
    )
    assert successor.sha256 != first.sha256
    assert successor.previous_source_sha256 == first.sha256
    assert observation_ids(first).isdisjoint(observation_ids(successor))
    with pytest.raises(ValueError, match="own predecessor"):
        parse_workbook(content, "original.xlsx", previous_source_sha256=first.sha256)


def entity(key, tag):
    return {
        "key": key, "kind": "equipment", "identifier": tag,
        "id_evidence": {"id": f"legacy-{key}", "observation_id": f"obs-{key}"},
    }


def test_convention_retains_provenance_without_assigning_physical_identity():
    source = {"entities": [entity("a", "P-101"), entity("b", "P-101"), entity("c", "V-1")]}
    plan = {"equipment": [{"equipment_key": "a", "quantity": 2}]}
    effective, prepared, review = reconcile(source, plan)
    original = deepcopy((source, effective, prepared, review))
    result = identity_register(source, effective, prepared, review, plan)["equipment"]
    assert [e["key"] for e in effective["entities"]] == ["a", "c"]
    assert [row["equipment_key"] for row in result] == ["a", "b", "c"]
    assert [row["status"] for row in result] == ["ambiguous", "ambiguous", "unresolved"]
    assert all(row["physical_asset_id"] is None for row in result)
    assert result[1]["observation_ids"] == ["obs-b"]
    assert prepared["equipment"][0]["quantity"] == 2
    assert (source, effective, prepared, review) == original


def test_reviewed_aliases_share_a_single_asset_but_keep_record_keys():
    source = {"entities": [entity("a", "P-1"), entity("b", "Pump One"), entity("c", "P-01")]}
    plan = {"equipment": [
        {"equipment_key": "a", "quantity": 1},
        *[
            {
                "equipment_key": key, "scope_decision": "alias", "alias_of": "a",
                "alias_confirmation": {"status": "user_confirmed", "rationale": "Reviewed equipment ledger"},
            }
            for key in ("b", "c")
        ],
    ]}
    effective, expanded = expand(source, plan)
    rows = identity_register(source, effective, expanded, [], plan)["equipment"]
    assert [row["equipment_key"] for row in rows] == ["a", "b", "c"]
    assert all(row["status"] == "resolved" and row["physical_asset_id"] == "a" for row in rows)
    assert set(rows[0]["aliases"]) == {"P-1", "Pump One", "P-01"}
    assert all(row["review"]["rationale"] for row in rows)


def test_snapshot_round_trip_and_legacy_keys(tmp_path):
    content = workbook()
    report = parse_workbook(content, "original.xlsx").model_dump(mode="json")
    store = Store(tmp_path / "assessments.sqlite")
    legacy = deepcopy(report)
    legacy.pop("previous_source_sha256")
    for entry in legacy["entities"]:
        for evidence in [entry["id_evidence"], *entry["values"]]:
            evidence.pop("observation_id")
    for payload in (report, legacy):
        identities = identity_register(payload, payload, {}, [], {})
        state = store.create({"parsed": {"report": payload}, "stages": {
            "equipment": {"result": {"identity_register": identities}}
        }}, content)
        saved = store.load(store.version(state["id"], "baseline"))
        assert saved["parsed"] == state["parsed"]
        assert saved["stages"] == state["stages"]
        assert store.workbook(saved["id"]) == content
        model = BalanceReport.model_validate(saved["parsed"]["report"])
        assert [e.key for e in model.entities] == [e["key"] for e in payload["entities"]]
        if payload is legacy:
            assert all(e.id_evidence.observation_id is None for e in model.entities)
            assert all(row["status"] == "unresolved" for row in identities["equipment"])


def test_equipment_stage_projects_identity_without_changing_priced_quantity():
    from backend.blocks.equipment.runner import calculate
    from backend.blocks.models import Context
    from backend.tests.test_equipment_resolution import price
    from backend.tests.test_monte_carlo import complete_state

    state = complete_state()
    report = state["parsed"]["report"]
    row = state["plan"]["equipment"][0]
    row.update(manual_price=price(), quantity=2)
    equipment = next(e for e in report["entities"] if e["key"] == row["equipment_key"])
    equipment["id_evidence"] = {"id": "v1", "observation_id": "observation:example"}
    product = calculate(Context(state, report, {}, None))

    receipt = product.result["identity_register"]["equipment"][0]
    assert receipt["equipment_key"] == row["equipment_key"]
    assert receipt["observation_ids"] == ["observation:example"]
    assert receipt["physical_asset_id"] is None
    assert receipt["status"] == "unresolved"
    assert product.result["equipment_cost_total"] == 20000
    assert product.result["equipment"][0]["parsed_source"]["equipment_count"] == 2
    assert "identity_register" not in product.payload



def test_reviewed_split_retains_distinct_asset_ids_with_same_display_tag():
    source = {"entities": [entity("parent", "P-1")]}
    plan = {"equipment": [{
        "equipment_key": "parent",
        "scope_confirmation": {
            "status": "user_confirmed_distinct",
            "rationale": "Two assets independently confirmed from equipment ledger",
        },
        "physical_assets": [
            {"asset_id": "east", "equipment_tag": "P-1", "quantity": 1},
            {"asset_id": "west", "equipment_tag": "P-1", "quantity": 1},
        ],
    }]}
    effective, expanded = expand(source, plan)
    rows = identity_register(source, effective, expanded, [], plan)["equipment"]
    assert rows[0]["equipment_key"] == "parent"
    assert rows[0]["physical_asset_id"] is None
    assert [row["physical_asset_id"] for row in rows[1:]] == ["parent::east", "parent::west"]
    assert all(row["status"] == "resolved" for row in rows[1:])
    assert all(row["observation_ids"] == ["obs-parent"] for row in rows[1:])
    assert [row["quantity"] for row in expanded["equipment"]] == [1, 1]



def test_legacy_api_reopen_projects_identity_without_rewriting_history(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from backend.api import app as api

    store = Store(tmp_path / "legacy.sqlite")
    monkeypatch.setattr(api, "store", store)
    legacy_entities = [entity("a", "P-101"), entity("b", "P-101"), entity("c", "V-1")]
    for equipment in legacy_entities:
        equipment["id_evidence"].pop("observation_id")
    stage = {"equipment": [
        {"equipment_tag": "P-101", "equipment_cost": 20000,
         "parsed_source": {"equipment_key": "a", "equipment_count": 2}},
        {"equipment_tag": "Unkeyed", "equipment_cost": None},
    ], "equipment_cost_total": 20000}
    saved = store.create({
        "parsed": {"report": {"entities": legacy_entities}},
        "results": {"stages": {
            "equipment": {"result": stage},
            "capex": {"result": {"total_capex": 32000}},
        }},
    }, b"legacy")
    version = store.version(saved["id"], "Legacy")
    with store.db() as db:
        original = db.execute("SELECT state FROM versions WHERE id = ?", (version,)).fetchone()
    client = TestClient(api.app)
    opened = client.post(f"/api/versions/{version}/open")
    assert opened.status_code == 200
    payload = opened.json()
    history = client.get(f"/api/assessments/{payload['id']}?historical=true").json()
    assert history == payload
    result = payload["results"]["stages"]["equipment"]["result"]
    rows = result.pop("identity_register")["equipment"]
    assert [(row["equipment_key"], row["status"]) for row in rows] == [
        ("a", "ambiguous"), ("b", "ambiguous"), ("c", "unresolved"), (None, "unresolved")
    ]
    assert rows[-1]["identity_limitation"] == "historical_equipment_key_unavailable"
    assert all(row["physical_asset_id"] is None and row["review"] is None for row in rows)
    assert result == stage
    assert payload["results"]["stages"]["capex"]["result"]["total_capex"] == 32000
    assert store.get(saved["id"]) == saved
    assert store.get(payload["id"])["results"] == saved["results"]
    with store.db() as db:
        assert db.execute("SELECT state FROM versions WHERE id = ?", (version,)).fetchone() == original


def test_recovery_identity_preserved_across_saved_reads_and_missing_locators():
    from backend.ingestion.observation_identity import project_report_evidence
    from backend.orchestration.workbook_review import VERSION, apply_review
    from backend.tests.test_engineering_review import fixture, response

    parsed = fixture()
    report, _ = apply_review(parsed, response())
    first = next(v for v in report["entities"][0]["values"] if v["property"] == "mass_flow")
    assert first["observation_method"] == VERSION
    assert first["normalized_value"] == 7200
    legacy = deepcopy(report)
    value = next(v for v in legacy["entities"][0]["values"] if v["id"] == first["id"])
    for field in ("observation_id", "observation_method", "sheet", "cell"):
        value.pop(field)
    no_hash = deepcopy(legacy)
    no_hash.pop("sha256")
    project_report_evidence(no_hash)
    missing = next(v for v in no_hash["entities"][0]["values"] if v["id"] == first["id"])
    assert missing["observation_identity_limitation"] == "missing_source_content_identity"
    assert "observation_id" not in missing
    project_report_evidence(legacy)
    project_report_evidence(legacy)
    assert value["observation_id"] == first["observation_id"]
    assert value["observation_method"] is None
    assert "sheet" not in value and "cell" not in value
    parsed["report"]["sha256"] = "b" * 64
    revised, _ = apply_review(parsed, response())
    revised_flow = next(v for v in revised["entities"][0]["values"] if v["property"] == "mass_flow")
    assert revised_flow["observation_id"] != first["observation_id"]


def test_manual_evidence_identity_and_revisions_survive_edit_replay():
    from backend.blocks.engineering_data.edits import apply_edit

    baseline = {"entities": []}
    addition = {"action": "add", "tag": "P-1", "name": "Pump", "equipment_key": "user-equipment:stable"}
    update = {"action": "update", "equipment_key": addition["equipment_key"], "tag": "P-2", "name": "Feed pump"}
    initial, key = apply_edit(baseline, addition)
    revised, _ = apply_edit(initial, update)
    repeated, _ = apply_edit(revised, update)
    replay, _ = apply_edit(apply_edit(baseline, addition)[0], update)
    assert revised == repeated == replay
    assert revised["entities"][0]["key"] == key
    before, after = initial["entities"][0], revised["entities"][0]
    for old, new in zip([before["id_evidence"], *before["values"]], [after["id_evidence"], *after["values"]]):
        assert new["id"] == old["id"] == new["observation_id"]
        assert (old["observation_revision"], new["observation_revision"]) == (1, 2)
        assert new["observation_method"] == "manual-engineering-register-1"
        assert new["workbook"] == "User input" and new["cell"] == "manual"


def test_uncalculated_legacy_identity_does_not_create_calculation_results():
    from backend.equipment_resolution.identity import project_assessment_identity

    saved = {"results": None, "parsed": {"report": {"entities": [entity("a", "P-1")]}}}
    projected = project_assessment_identity(saved)
    assert projected["results"] is None
    assert projected["identity_register"]["equipment"][0]["status"] == "unresolved"
    assert "identity_register" not in saved
