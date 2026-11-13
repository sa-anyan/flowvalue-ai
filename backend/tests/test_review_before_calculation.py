"""Review drafts are independent of numerical execution and retain user lineage."""

import copy
from unittest.mock import patch
import pytest
from backend.tests.test_isolated_stages import study
from backend.blocks.engineering_workflow import queue, run
from backend.blocks.execution import fresh, run_stage
from backend.blocks.engineering_data.edits import save_edit
from backend.blocks.preparation import prepare_stage


def test_entry_prepares_without_pricing_then_explicit_run_prices(study):
    store, key = study
    queue(store, key)
    with patch(
        "backend.blocks.equipment.runner.calculate_equipment",
        side_effect=AssertionError("No price before review"),
    ):
        state = run(store, key, prepare_only=True)
    assert fresh(state, "engineering_data")
    assert set(state["stage_outputs"]) == {"engineering_data"}
    assert state["equipment_preparation"]["status"] == "ready"
    assert state["plan"]["equipment"]
    assert not state["running"]
    state = run_stage(store, key, "equipment")
    assert fresh(state, "equipment"), state["stage_runs"]["equipment"]
    assert any(
        e["equipment_cost"] is not None
        for e in state["results"]["stages"]["equipment"]["result"]["equipment"]
    )


def test_register_edits_persist_without_replacing_workbook(study):
    store, key = study
    state = run_stage(store, key, "engineering_data")
    source = copy.deepcopy(state["parsed"]["report"])
    state = save_edit(
        store,
        key,
        state["revision"],
        {"action": "add", "tag": "TK-USER", "name": "User storage tank"},
    )
    added = next(
        e for e in state["effective_report"]["entities"] if e["identifier"] == "TK-USER"
    )
    assert added["values"][0]["workbook"] == "User input"
    assert state["parsed"]["report"] == source
    state = save_edit(
        store,
        key,
        state["revision"],
        {
            "action": "update",
            "equipment_key": added["key"],
            "tag": "TK-USER",
            "name": "Edited storage tank",
        },
    )
    edited = next(e for e in state["effective_report"]["entities"] if e["key"] == added["key"])
    assert edited["values"][-1]["observation_id"] == added["values"][-1]["observation_id"]
    assert edited["values"][-1]["observation_revision"] == 2
    state = run_stage(store, key, "engineering_data")
    replayed = next(e for e in state["effective_report"]["entities"] if e["key"] == added["key"])
    assert replayed == edited
    assert replayed["values"][-1]["normalized_value"] == "Edited storage tank"
    state = save_edit(
        store,
        key,
        state["revision"],
        {"action": "remove", "equipment_key": added["key"]},
    )
    state = run_stage(store, key, "engineering_data")
    assert not any(
        e["key"] == added["key"] for e in state["effective_report"]["entities"]
    )
    assert state["parsed"]["report"] == source


def test_register_rejects_duplicates_and_old_revisions(study):
    store, key = study
    state = run_stage(store, key, "engineering_data")
    tag = next(
        e["identifier"]
        for e in state["effective_report"]["entities"]
        if e["kind"] == "equipment"
    )
    with pytest.raises(ValueError, match="already exists"):
        save_edit(
            store,
            key,
            state["revision"],
            {"action": "add", "tag": tag, "name": "Duplicate"},
        )
    with pytest.raises(ValueError, match="reload"):
        save_edit(
            store,
            key,
            state["revision"] - 1,
            {"action": "add", "tag": "NEW", "name": "New"},
        )


def test_capex_preparation_does_not_run_calculations(study):
    store, key = study
    run_stage(store, key, "engineering_data")
    before = run_stage(store, key, "equipment")
    with patch(
        "backend.blocks.preparation.proposal",
        return_value=({"capex": {"model_id": "garrett"}}, {}),
    ), patch(
        "backend.blocks.capex.runner.calculate",
        side_effect=AssertionError("Do not calculate"),
    ):
        after = prepare_stage(store, key, "capex")
    assert after["plan"]["capex"] == {"model_id": "garrett"}
    assert after["stage_outputs"] == before["stage_outputs"]
    assert after["plan"]["operating_economics"] == before["plan"]["operating_economics"]
    assert after["stage_preparations"]["capex"]["status"] == "ready"


def test_opex_preparation_preserves_revenue_and_does_not_price(study):
    store, key = study
    before = run_stage(store, key, "engineering_data")
    config = copy.deepcopy(before["plan"]["operating_economics"])
    config["garrett_factors"] = {}
    with patch(
        "backend.blocks.preparation.operating_proposal", return_value=(config, {})
    ), patch(
        "backend.blocks.opex.runner.calculate",
        side_effect=AssertionError("Do not calculate"),
    ):
        after = prepare_stage(store, key, "opex")
    assert after["stage_outputs"] == before["stage_outputs"]
    for field in ["sales", "commercial_lines"]:
        assert after["plan"]["operating_economics"].get(field) == before["plan"][
            "operating_economics"
        ].get(field)


def test_api_defaults_to_review_and_cost_factor_catalogues():
    from backend.api.app import EngineeringRun, cost_factor_catalogue

    assert EngineeringRun().prepare_only is True
    assert cost_factor_catalogue("capex", "garrett", "mixed")
    assert cost_factor_catalogue("opex", "garrett", "mixed")


def test_opex_retains_proposed_draft_when_calculation_dependencies_are_missing(study):
    from backend.blocks.models import DataRequired

    store, key = study
    before = run_stage(store, key, "engineering_data")
    config = copy.deepcopy(before["plan"]["operating_economics"])
    config["garrett_factors"] = {
        "maintenance": {"fraction": 0.04, "rationale": "Draft review"}
    }
    missing = DataRequired(
        "Run CAPEX before calculating",
        ["capex"],
        {"plan": {"operating_economics": config}},
    )
    with patch("backend.blocks.preparation.operating_proposal", side_effect=missing):
        after = prepare_stage(store, key, "opex")
    assert (
        after["plan"]["operating_economics"]["garrett_factors"]
        == config["garrett_factors"]
    )
    assert after["stage_outputs"] == before["stage_outputs"]
