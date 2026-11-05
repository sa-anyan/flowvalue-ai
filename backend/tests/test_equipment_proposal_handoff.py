"""Regression for the live AI response envelope that prevented all pricing."""

import copy
from unittest.mock import patch

import pytest

from backend.blocks.equipment.proposal import equipment_rows
from backend.blocks.execution import run_stage
from backend.tests.test_isolated_stages import study  # noqa: F401 -- pytest fixture


@pytest.mark.parametrize("wrapped", [False, True])
def test_real_equipment_calculator_accepts_both_ai_envelopes(study, wrapped):
    store, key = study
    state = run_stage(store, key, "engineering_data")
    rows = copy.deepcopy(state["plan"]["equipment"])
    value = {"equipment": rows} if wrapped else rows
    # Legacy transport normalisation remains supported independently; the new
    # matcher has its own strict structured-output contract.
    accepted, issues = equipment_rows(value, state["parsed"]["report"])
    state["plan"]["equipment"] = accepted
    store.put(state, state["revision"])
    result = run_stage(store, key, "equipment", use_ai=False)
    assert result["stage_runs"]["equipment"]["status"] == "ready"
    assert any(
        e["equipment_cost"] is not None
        for e in result["results"]["stages"]["equipment"]["result"]["equipment"]
    )
    assert set(result["stage_outputs"]) == {"engineering_data", "equipment"}


def test_invalid_individual_rows_do_not_discard_valid_equipment(study):
    store, key = study
    state = run_stage(store, key, "engineering_data")
    rows = copy.deepcopy(state["plan"]["equipment"])
    value = {"equipment": ["not a row", {"equipment_key": "unknown"}, *rows]}
    # Legacy transport normalisation remains supported independently; the new
    # matcher has its own strict structured-output contract.
    accepted, issues = equipment_rows(value, state["parsed"]["report"])
    state["plan"]["equipment"] = accepted
    store.put(state, state["revision"])
    result = run_stage(store, key, "equipment", use_ai=False)
    assert result["stage_runs"]["equipment"]["status"] == "ready"
    assert len(issues) == 2
    assert any(
        e["equipment_cost"] is not None
        for e in result["results"]["stages"]["equipment"]["result"]["equipment"]
    )


@pytest.mark.parametrize(
    "value", [None, "equipment", {"equipment": "not a list"}, {"unexpected": []}]
)
def test_invalid_top_level_shape_has_clear_error(value):
    with pytest.raises(ValueError, match="Equipment proposal"):
        equipment_rows(value, {"entities": []})


def test_duplicate_key_cannot_create_duplicate_proposal():
    row = {"equipment_key": "e1"}
    rows, issues = equipment_rows(
        [row, row], {"entities": [{"kind": "equipment", "key": "e1"}]}
    )
    assert rows == [row] and len(issues) == 1
