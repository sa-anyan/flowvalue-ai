"""Saved Box edits invoke fresh commercial AI without rerunning the full study."""
import copy
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.orchestration.revenue_workflow import reinterpret_revenue
from backend.orchestration.service import new_assessment
from backend.orchestration.store import Store
from backend.revenue.advisor import RevenueAIError
from backend.tests.test_revenue_authority import ready, BOX


def test_entry_and_saved_box_produce_the_same_commercial_draft():
    from backend.orchestration.revenue_workflow import execute_revenue
    report, config, _ = ready()
    response = {"sections": [{"section": "operating_economics", "value_json": json.dumps(config)}], "questions": []}
    with tempfile.TemporaryDirectory() as folder:
        store = Store(Path(folder) / "test.db")
        state = new_assessment(store, b"fixture", "fixture.xlsx", "Process context", BOX, workflow="revenue")
        state.update(parsed={"report": report, "source_cells": []}, running=False)
        state = store.put(state, state["revision"])
        with patch("backend.orchestration.revenue_workflow.review", return_value=(report, {"questions": []}, [], {"status": "reviewed"})), patch("backend.orchestration.revenue_workflow.propose", return_value=(response, {"model": "fake"})) as proposal:
            initial = execute_revenue(store, state, use_ai=True, provider=object())
            edited = reinterpret_revenue(store, copy.deepcopy(initial), provider=object())
        assert not initial.get("error")
        assert not edited.get("error")
        assert initial["plan"]["operating_economics"] == edited["plan"]["operating_economics"]
        assert initial["revenue_questions"] == edited["revenue_questions"]
        assert not initial.get("revenue_approval") and not edited.get("revenue_approval")
        for call in proposal.call_args_list:
            assert call.kwargs["force_refresh"] is True
            assert call.args[0]["revenue_box"] == BOX
            assert call.args[0]["revenue_edit"] is True


def state_for(store):
    report, config, _ = ready()
    state = new_assessment(store, b"fixture", "fixture.xlsx", "Process context", BOX, workflow="revenue")
    state.update(running=False, parsed={"report": report, "source_cells": []},
                 plan={"operating_economics": config, "capex": {"keep": True}},
                 locked=["operating_economics", "capex"],
                 results={"stages": {"revenue": {"result": {"old": True}}}})
    return store.put(state, state["revision"])


def test_reinterpretation_bypasses_cache_and_locks_only_for_commercial_inputs():
    with tempfile.TemporaryDirectory() as folder:
        store = Store(Path(folder) / "test.db")
        state = state_for(store)
        old = copy.deepcopy(state["plan"]["operating_economics"])
        fresh = copy.deepcopy(old)
        fresh["sales"][0]["unit_price"] = 20
        fresh["financial"]["operating_years"] = 1
        fresh["materials"] = [{"unrelated": "must not replace saved costs"}]
        response = {"sections": [{"section": "operating_economics", "value_json": json.dumps(fresh)}], "questions": ["Confirm the proposed buyer"]}
        with patch("backend.orchestration.revenue_workflow.propose", return_value=(response, {"model": "fake", "cached": False})) as proposal, patch("backend.orchestration.service.run", side_effect=AssertionError("No full pipeline")):
            result = reinterpret_revenue(store, state, provider=object())
        assert not result.get("error")
        assert result["plan"]["operating_economics"]["sales"][0]["unit_price"] == 20
        assert result["plan"]["operating_economics"]["financial"] == old["financial"]
        assert result["plan"]["operating_economics"]["materials"] == old["materials"]
        assert result["plan"]["capex"] == {"keep": True}
        assert not result.get("revenue_approval")
        assert result["results"]["stages"]["revenue"]["result"] is None
        assert proposal.call_args.kwargs["force_refresh"] is True
        assert proposal.call_args.kwargs["requested_sections"] == ("revenue",)
        assert proposal.call_args.args[3] == ["capex"]


def test_failed_ai_keeps_previous_inputs_and_releases_running_state():
    with tempfile.TemporaryDirectory() as folder:
        store = Store(Path(folder) / "test.db")
        state = state_for(store)
        old = copy.deepcopy(state["plan"])
        with patch("backend.orchestration.revenue_workflow.propose", side_effect=RevenueAIError("OpenAI unavailable")):
            result = reinterpret_revenue(store, state, provider=object())
        assert not result["running"]
        assert result["plan"] == old
        assert result["revenue_description"] == BOX
        assert result["error"] == "OpenAI unavailable"


def test_save_endpoint_queues_ai_but_approval_does_not():
    from backend.api import app as api
    with tempfile.TemporaryDirectory() as folder:
        store = Store(Path(folder) / "test.db")
        state = state_for(store)
        with patch.object(api, "store", store), patch.object(api, "submit") as submit:
            client = TestClient(api.app)
            response = client.post(f'/api/assessments/{state["id"]}/revenue-authority', json={
                "revision": state["revision"], "revenue_description": BOX, "reinterpret": True,
            })
            assert response.status_code == 200
            assert response.json()["running"] is True
            submit.assert_called_once_with(state["id"], use_ai=True, refresh_revenue=True)
            bad = client.post(f'/api/assessments/{state["id"]}/revenue-authority', json={
                "revision": response.json()["revision"], "approve": True, "reinterpret": True,
            })
            assert bad.status_code == 422
