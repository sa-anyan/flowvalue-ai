"""Save & go: one Save runs the study in the background; user inputs are never refused."""

import time

import pytest
from fastapi.testclient import TestClient

import backend.api.app as api
from backend.blocks import launch
from backend.orchestration.store import Store
from backend.tests.test_autopilot import _workbook


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "store", Store(tmp_path / "a.sqlite"))
    monkeypatch.setattr(api._opex_brainstorm, "ai_available", lambda: False)  # no real AI in tests
    return TestClient(api.app)


def _upload(client):
    return client.post("/api/assessments", files={"file": ("plant.xlsx", _workbook())},
                       data={"analysis_years": "20", "construction_years": "2"}).json()["id"]


def _wait(key, timeout=60):
    end = time.time() + timeout
    while time.time() < end and launch.running(key):
        time.sleep(0.05)
    assert not launch.running(key)


def _stream(client, key, name="Water leaving Pump P-1"):
    state = api.store.get(key)
    report = state["stage_outputs"]["engineering_data"]["report"]
    return next(e["key"] for e in report["entities"] if e["kind"] == "material"
                and any(name in str(v.get("original_value")) for v in e["values"]))


def _sale(client, key, **extra):
    return {"revision": api.store.get(key)["revision"], "currency": "USD", "price_period": "2026-09",
            "sales": [{"name": "Water", "stream_key": _stream(client, key), "component": None,
                       "unit_price": 0.002, "quantity_unit": "kg", **extra}]}


def test_one_save_reads_approves_and_runs_every_stage(client):
    key = _upload(client)
    assert client.post(f"/api/assessments/{key}/launch", json={"use_ai": False}).json()["started"]
    _wait(key)
    state = api.store.get(key)
    assert state["launch"]["status"] == "finished"
    assert state["engineering_approval"]["by"] == launch.VERSION and state["engineering_approval"]["provisional"]
    assert set(state["stage_runs"]) >= {"engineering_data", "equipment", "capex", "revenue", "opex", "financial"}
    assert state["running"] is False
    assert state["ai_background_enabled"] is False


def test_revenue_saved_while_busy_is_queued_then_applied(client):
    key = _upload(client)
    client.post(f"/api/assessments/{key}/launch", json={"use_ai": False})
    _wait(key)
    with api.lock:  # a background step holds the study
        out = client.post(f"/api/assessments/{key}/revenue-setup", json=_sale(client, key)).json()
        assert out["queued"] is True and launch.pending(key) == ["revenue_setup"]
        assert client.get(f"/api/assessments/{key}").json()["inbox"] == ["revenue_setup"]
        launch.drain(api.store, key)  # what the chain does between steps
    sales = api.store.get(key)["plan"]["operating_economics"]["sales"]
    assert sales[0]["name"] == "Water" and launch.pending(key) == []


def test_a_bad_revenue_choice_is_refused_at_once_even_while_busy(client):
    key = _upload(client)
    client.post(f"/api/assessments/{key}/launch", json={"use_ai": False})
    _wait(key)
    bad = _sale(client, key, unit_price=-1)
    with api.lock:
        response = client.post(f"/api/assessments/{key}/revenue-setup", json=bad)
    assert response.status_code == 422 and "negative" in response.json()["detail"]
    assert launch.pending(key) == []


def test_upload_and_quick_answers_are_never_refused_while_another_run_holds_the_lock(client):
    first = _upload(client)
    with api.lock:
        second = client.post("/api/assessments", files={"file": ("b.xlsx", _workbook())})
        assert second.status_code == 202
        out = client.post(f"/api/assessments/{first}/project-context", json={"location": "Ghana"}).json()
        assert out["queued"] is True and launch.pending(first) == ["project_context"]


def test_busy_save_is_delivered_even_without_a_launch_thread(client):
    key = _upload(client)
    with api.lock:
        response = client.post(f"/api/assessments/{key}/project-context", json={"location": "Ghana"})
        assert response.status_code == 200 and response.json()["queued"]
        assert launch.pending(key) == ["project_context"]
    end = time.time() + 5
    while time.time() < end and launch.pending(key):
        time.sleep(.02)
    assert api.store.get(key)["project_context"]["location"] == "Ghana"
    assert launch.pending(key) == []


def test_revenue_that_arrives_after_the_revenue_step_is_calculated(monkeypatch, tmp_path):
    """Order: inputs applied after the revenue step trigger revenue, OPEX and financial again."""
    from backend.blocks import autopilot, execution, stage_workflow

    store = Store(tmp_path / "b.sqlite")
    state = {"id": "k", "revision": 0, "filename": "x.xlsx", "plan": {}, "stage_runs": {}}
    store.db  # noqa: B018 -- the table exists once the store is created
    with store.db() as db:
        import json
        db.execute("INSERT INTO assessments (id, revision, state) VALUES (?,?,?)", ("k", 0, json.dumps(state)))
    calls = []

    def fake_run_stage(store_, key, stage, **kw):
        calls.append(stage)
        if stage == "revenue" and calls.count("revenue") == 1:
            launch.put("k", "revenue_setup", {"sales": []})  # the user saves during the revenue step
        return store_.get(key)

    monkeypatch.setattr(execution, "run_stage", fake_run_stage)
    monkeypatch.setattr(execution, "fresh", lambda *a: True)
    monkeypatch.setattr(stage_workflow, "approved", lambda *a: True)
    monkeypatch.setattr(autopilot, "_pick_models", lambda s: [])
    monkeypatch.setitem(launch.HANDLERS, "revenue_setup", lambda *a: None)
    launch.run(store, "k", use_ai=False)
    assert calls == ["engineering_data", "equipment", "capex", "revenue", "opex", "financial",
                     "revenue", "opex", "financial"]
    assert store.get("k")["launch"]["status"] == "finished"
