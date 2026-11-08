"""Approved batch execution is the existing stage pipeline, not a second engine."""

from unittest.mock import patch
import pytest
from backend.tests.test_isolated_stages import study
from backend.blocks.execution import run_stage, fresh, view
from backend.blocks.stage_workflow import approve, approved, queue, run, ORDER
from backend.blocks.engineering_data.edits import save_edit
from backend.revenue.authority import update


def test_requires_review_before_batch(study):
    store, key = study
    run_stage(store, key, "engineering_data")
    with pytest.raises(ValueError, match="approve"):
        queue(store, key)


def test_approval_is_source_bound_and_edits_invalidate_it(study):
    store, key = study
    state = run_stage(store, key, "engineering_data")
    state = approve(store, key, state["revision"])
    assert approved(state) and view(state)["engineering_data_approved"]
    state = save_edit(
        store,
        key,
        state["revision"],
        {"action": "add", "tag": "TK-EXTRA", "name": "User tank"},
    )
    assert not approved(state) and not view(state)["engineering_data_approved"]


def test_approve_rejects_missing_data_and_stale_revision(study):
    store, key = study
    with pytest.raises(ValueError, match="Extract"):
        approve(store, key, store.get(key)["revision"])
    state = run_stage(store, key, "engineering_data")
    with pytest.raises(ValueError, match="reload"):
        approve(store, key, state["revision"] - 1)


def test_all_stages_use_existing_runners_and_saved_revenue_approval(study):
    store, key = study
    state = run_stage(store, key, "engineering_data")
    state = update(store, key, state["revision"], approve=True)
    approve(store, key, state["revision"])
    queue(store, key)
    with patch(
        "backend.blocks.engineering_data.runner.calculate",
        side_effect=AssertionError("Do not re-extract"),
    ):
        state = run(store, key)
    assert state["stage_workflow"]["status"] == "complete", state["stage_runs"]
    assert [x["stage"] for x in state["stage_workflow"]["completed"]] == list(ORDER)
    assert all(fresh(state, s) for s in ORDER)
    assert not view(state)["running"]
    assert all(not state["stage_runs"][s]["use_ai"] for s in ORDER)


def test_batch_never_auto_approves_revenue_or_hides_partial_results(study):
    store, key = study
    state = run_stage(store, key, "engineering_data")
    approve(store, key, state["revision"])
    queue(store, key)
    state = run(store, key)
    assert fresh(state, "equipment") and fresh(state, "capex")
    assert state["stage_runs"]["revenue"]["status"] == "data_required"
    assert not state.get("revenue_approval")
    assert state["stage_workflow"]["status"] == "needs_review"
    assert len(state["stage_workflow"]["completed"]) == 5


def test_polling_stays_active_between_stages(study):
    store, key = study
    state = run_stage(store, key, "engineering_data")
    state = approve(store, key, state["revision"])
    state = queue(store, key)
    state["running"] = False
    assert view(state)["running"]


def test_economics_group_reuses_fresh_equipment_and_refreshes_finance(study):
    from backend.blocks.stage_workflow import ECONOMIC_ORDER

    store, key = study
    state = run_stage(store, key, "engineering_data")
    state = update(store, key, state["revision"], approve=True)
    state = run_stage(store, key, "equipment")
    approve(store, key, state["revision"])
    before = store.get(key)["stage_runs"]["equipment"]["output_hash"]
    queue(store, key, economic_only=True)
    with patch(
        "backend.blocks.equipment.runner.calculate",
        side_effect=AssertionError("Do not rerun valid equipment"),
    ):
        state = run(store, key)
    assert state["stage_workflow"]["order"] == list(ECONOMIC_ORDER)
    assert state["stage_workflow"]["status"] == "complete"
    assert state["stage_runs"]["equipment"]["output_hash"] == before
    assert all(fresh(state, s) for s in ECONOMIC_ORDER)


def test_all_economic_api_triggers_use_the_same_group():
    from backend.api.app import run_individual_stage, Rerun

    with patch(
        "backend.api.app.submit_stage_group", return_value={"id": "test"}
    ) as submit:
        for stage in ("capex", "opex", "revenue"):
            assert run_individual_stage("test", stage, Rerun()) == {"id": "test"}
            assert submit.call_args.kwargs == {"economic_only": True}
        assert submit.call_count == 3


def test_group_preserves_approved_revenue_when_ai_is_requested(study):
    store, key = study
    state = run_stage(store, key, "engineering_data")
    state = update(store, key, state["revision"], approve=True)
    state = run_stage(store, key, "equipment")
    approve(store, key, state["revision"])
    queue(store, key, economic_only=True)
    calls = []

    def capture(store, key, stage, *, use_ai, provider=None):
        calls.append((stage, use_ai))
        return run_stage(store, key, stage, use_ai=False)

    with patch("backend.blocks.stage_workflow.run_stage", side_effect=capture):
        result = run(store, key, use_ai=True)
    assert dict(calls) == {
        "capex": True,
        "revenue": False,
        "opex": True,
        "financial": True,
    }
    assert result["stage_workflow"]["status"] == "complete"
