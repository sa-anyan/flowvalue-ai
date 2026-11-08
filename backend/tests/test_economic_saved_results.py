from unittest.mock import patch
from backend.tests.test_isolated_stages import study
from backend.blocks.execution import run_stage, refresh


def test_capex_stale_and_failed_rerun_retain_last_saved_result(study):
    store, key = study
    run_stage(store, key, "engineering_data")
    run_stage(store, key, "equipment")
    state = run_stage(store, key, "capex")
    original = state["results"]["stages"]["capex"]["result"]
    state["plan"]["capex"]["factor_selection"] = "maximum"
    refresh(state)
    assert state["results"]["stages"]["capex"]["result"] == original
    assert state["results"]["stages"]["capex"]["result_is_stale"]
    store.put(state, state["revision"])
    with patch(
        "backend.blocks.capex.runner.calculate",
        side_effect=ValueError("Proposal temporarily unavailable"),
    ):
        state = run_stage(store, key, "capex")
    assert state["results"]["stages"]["capex"]["result"] == original
    assert state["stage_runs"]["capex"]["status"] == "data_required"
