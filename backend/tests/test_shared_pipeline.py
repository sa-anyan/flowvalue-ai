"""All source ages/formats and public entry points use one active coordinator."""

import copy
from unittest.mock import patch

import pytest

from backend.blocks.execution import MODE, PIPELINE_ID, view
from backend.orchestration.service import execute, new_assessment
from backend.orchestration.store import Store
from backend.tests.test_stage_connections import workbook, plan_for, DESCRIPTION
from backend.orchestration.ingest import parse


@pytest.mark.parametrize("filename", ["Mass Balance Team 8.xlsm", "M&E Charlie.xlsx"])
def test_legacy_and_current_sources_follow_same_fresh_pipeline(tmp_path, filename):
    content = workbook()
    report = parse(content, filename)["report"]
    store = Store(tmp_path / "pipeline.sqlite")
    state = new_assessment(store, content, filename, DESCRIPTION)
    state["plan"] = plan_for(report)
    state = store.put(state, state["revision"])
    with patch(
        "backend.orchestration.service._execute_connected_reference",
        side_effect=AssertionError("No legacy execution"),
    ):
        result = execute(store, state["id"], use_ai=False)
    assert result["execution_mode"] == MODE
    assert set(result["stage_outputs"]) == {"engineering_data", "equipment"}
    for stage in result["stage_runs"].values():
        assert stage["pipeline_id"] == PIPELINE_ID and stage["executed"] is True
    assert any(
        row["equipment_cost"] is not None
        for row in result["results"]["stages"]["equipment"]["result"]["equipment"]
    )


def test_old_results_are_history_not_calculation_inputs(tmp_path):
    content = workbook()
    report = parse(content, "legacy.xlsm")["report"]
    store = Store(tmp_path / "history.sqlite")
    state = new_assessment(store, content, "legacy.xlsm", DESCRIPTION)
    state.update(
        running=False,
        plan=plan_for(report),
        results={
            "stages": {
                "equipment": {"result": {"equipment": [{"equipment_cost": 999999999}]}}
            }
        },
    )
    state = store.put(state, state["revision"])
    before = copy.deepcopy(state["results"])
    with patch(
        "backend.orchestration.current_prices.run",
        side_effect=AssertionError("Views never execute"),
    ):
        from backend.orchestration.current_prices import current_price_view

        opened = current_price_view(state)
    assert opened["execution_notice"] and not opened["results"]["stages"]
    result = execute(store, state["id"])
    actual = result["results"]["stages"]["equipment"]["result"]["equipment"]
    assert actual[0]["equipment_cost"] != 999999999
    versions = store.versions(state["id"])
    assert versions and store.load(versions[0]["id"])["results"] == before


def test_both_http_run_urls_dispatch_same_coordinator(tmp_path):
    from fastapi.testclient import TestClient
    from backend.api import app as api

    store = Store(tmp_path / "http.sqlite")
    state = new_assessment(store, workbook(), "source.xlsx", DESCRIPTION)
    state["running"] = False
    store.put(state, state["revision"])
    tasks = []

    class Executor:
        def submit(self, task):
            tasks.append(task)

    with patch.object(api, "store", store), patch.object(
        api, "executor", Executor()
    ), patch("backend.blocks.engineering_workflow.run", return_value={}) as common:
        client = TestClient(api.app)
        for path in ("run", "engineering/run"):
            response = client.post(
                f"/api/assessments/{state['id']}/{path}", json={"use_ai": False}
            )
            assert (
                response.status_code == 202
                and response.json()["pipeline_id"] == PIPELINE_ID
            )
            tasks.pop()()
            # Mock execution has not cleared the queue marker.
            queued = store.get(state["id"])
            queued.update(running=False)
            store.put(queued, queued["revision"])
        assert common.call_count == 2


def test_historical_http_view_never_recalculates_even_with_currency(tmp_path):
    from fastapi.testclient import TestClient
    from backend.api import app as api

    store = Store(tmp_path / "snapshot.sqlite")
    saved = store.create(
        {"running": False, "plan": {}, "results": {"historical": 123}}, b"source"
    )
    with patch.object(api, "store", store), patch.object(
        api, "currency_view", side_effect=AssertionError("History cannot calculate")
    ):
        result = TestClient(api.app).get(
            f"/api/assessments/{saved['id']}?historical=true&currency=GBP"
        )
    assert result.status_code == 200 and result.json()["results"] == {"historical": 123}
