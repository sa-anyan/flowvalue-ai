"""Background OPEX brainstorm: starts on approval, fills gaps, never overwrites."""

import threading
from io import BytesIO

import openpyxl

from backend.blocks.execution import run_stage
from backend.blocks.opex import brainstorm
from backend.blocks.stage_workflow import approve
from backend.opex.reference_defaults import propose
from backend.orchestration.store import Store

LABOUR = [{"id": "electricians", "role": "Electricians", "category": "operating_labor", "behavior": "fixed",
           "headcount_fte": 6, "annual_base_salary": 70000, "allocation_fraction": 1,
           "rationale": "AI: two per shift for electrolyser stacks", "uncertainty": "AI estimate"}]


def _workbook():
    book = openpyxl.Workbook()
    sheet = book.active
    sheet.title = "Balance"
    sheet.append(["Stream ID", "Description", "Mass flow (kg/h)", "Temperature (C)", "Pressure (bar)"])
    sheet.append(["S-1", "Feed water to Storage Tank T-1", 1000, 25, 1])
    sheet.append(["S-2", "Water from Storage Tank T-1 to Pump P-1", 1000, 25, 1])
    sheet.append(["S-3", "Water leaving Pump P-1", 1000, 25, 4])
    data = BytesIO()
    book.save(data)
    return data.getvalue()


def _extracted(tmp_path):
    from fastapi.testclient import TestClient

    import backend.api.app as api

    store = Store(tmp_path / "a.sqlite")
    original, api.store = api.store, store
    try:
        key = TestClient(api.app).post("/api/assessments", files={"file": ("b.xlsx", _workbook())}).json()["id"]
    finally:
        api.store = original
    run_stage(store, key, "engineering_data", use_ai=False)
    return store, key


class Now:
    """Runs submitted work at once so the test can inspect the result."""

    def submit(self, fn, *args):
        fn(*args)


def test_merge_fills_labour_and_refines_reference_defaults_only():
    config, _ = propose({}, {"entities": [], "connections": []})
    config["garrett_factors"]["supervision"] = {"fraction": 0.12, "rationale": "User-selected factor", "origin": "user"}
    ai = {
        "labour": LABOUR,
        "garrett_factors": {
            "maintenance": {"fraction": 0.04, "rationale": "AI: clean water service"},  # inside 2–10 %
            "taxes_insurance": {"fraction": 0.5, "rationale": "AI: out of range"},  # outside its range
            "supervision": {"fraction": 0.2, "rationale": "AI tries to replace the user"},
        },
    }
    merged, added = brainstorm.merge(config, ai)
    assert merged["labour"][0]["headcount_fte"] == 6 and merged["labour"][0]["origin"] == "ai"
    assert merged["garrett_factors"]["maintenance"]["fraction"] == 0.04
    assert merged["garrett_factors"]["maintenance"]["origin"] == "ai"
    assert merged["garrett_factors"]["taxes_insurance"]["origin"] == "reference_default"  # AI value rejected
    assert merged["garrett_factors"]["supervision"] == config["garrett_factors"]["supervision"]
    assert "labour.electricians" in added and "garrett_factors.supervision" not in added
    assert merged["value_owners"]["labour.electricians"] == "ai"
    # The labour question is answered; it no longer appears.
    assert all(q["id"] != "operating_labor" for q in merged["reference_defaults"]["questions"])


def test_merge_never_replaces_user_or_earlier_ai_lists():
    user = {"labour": [{"id": "ops", "role": "Operators", "headcount_fte": 3, "origin": "user"}]}
    merged, added = brainstorm.merge(user, {"labour": LABOUR})
    assert merged["labour"] == user["labour"] and added == []
    earlier = {"labour": [dict(LABOUR[0], origin="ai")]}
    merged, added = brainstorm.merge(earlier, {"labour": [dict(LABOUR[0], headcount_fte=9)]})
    assert merged["labour"][0]["headcount_fte"] == 6 and added == []


def test_brainstorm_starts_on_approval_and_saves_into_the_gaps(tmp_path, monkeypatch):
    store, key = _extracted(tmp_path)
    calls = []

    def fake(state, store_, provider):
        calls.append(state["id"])
        return {"labour": LABOUR}, {"model": "test"}

    monkeypatch.setattr(brainstorm, "_propose", fake)
    monkeypatch.setattr(brainstorm, "ai_available", lambda: True)
    started = threading.Event()
    real_kick = brainstorm.kick
    monkeypatch.setattr(brainstorm, "kick", lambda s, k, *a, **kw: (started.set(), real_kick(s, k, provider=object(), executor=Now()))[1])
    state = approve(store, key, store.get(key)["revision"])
    assert started.is_set() and calls == [key]
    state = store.get(key)
    record = state["opex_brainstorm"]
    assert record["status"] == "ready" and record["added"] == ["labour.electricians"]
    assert state["plan"]["operating_economics"]["labour"][0]["role"] == "Electricians"
    # Same approved data: no second AI call.
    assert brainstorm.kick(store, key, provider=object(), executor=Now()) is False
    assert calls == [key]


def test_ai_failure_is_recorded_and_changes_nothing(tmp_path, monkeypatch):
    store, key = _extracted(tmp_path)
    approve(store, key, store.get(key)["revision"])
    before = store.get(key)["plan"].get("operating_economics")

    def broken(*_):
        raise RuntimeError("timeout")

    monkeypatch.setattr(brainstorm, "_propose", broken)
    assert brainstorm.kick(store, key, provider=object(), executor=Now()) is True
    state = store.get(key)
    assert state["opex_brainstorm"]["status"] == "failed" and "timeout" in state["opex_brainstorm"]["error"]
    assert state["plan"].get("operating_economics") == before


def test_no_ai_means_no_background_job(tmp_path, monkeypatch):
    store, key = _extracted(tmp_path)
    monkeypatch.setattr(brainstorm, "ai_available", lambda: False)
    approve(store, key, store.get(key)["revision"])
    assert "opex_brainstorm" not in store.get(key)
    assert brainstorm.status(key, store.get(key)) is None


def test_locked_operating_economics_is_never_touched(tmp_path, monkeypatch):
    store, key = _extracted(tmp_path)
    approve(store, key, store.get(key)["revision"])
    state = store.get(key)
    state["locked"] = ["operating_economics"]
    store.put(state, state["revision"])
    monkeypatch.setattr(brainstorm, "_propose", lambda *a: ({"labour": LABOUR}, {}))
    assert brainstorm.kick(store, key, provider=object(), executor=Now()) is False
    assert "labour" not in (store.get(key)["plan"].get("operating_economics") or {})


def test_api_reports_live_status_while_running(tmp_path, monkeypatch):
    store, key = _extracted(tmp_path)
    approve(store, key, store.get(key)["revision"])
    gate = threading.Event()

    def slow(*_):
        gate.wait(5)
        return {"labour": LABOUR}, {}

    monkeypatch.setattr(brainstorm, "_propose", slow)
    assert brainstorm.kick(store, key, provider=object()) is True
    assert brainstorm.status(key, store.get(key))["status"] == "running"
    gate.set()
    for _ in range(100):
        if (store.get(key).get("opex_brainstorm") or {}).get("status") == "ready":
            break
        threading.Event().wait(0.05)
    assert store.get(key)["opex_brainstorm"]["status"] == "ready"
    assert brainstorm.status(key, store.get(key))["status"] == "ready"


def test_a_read_taken_just_before_the_save_still_says_running(tmp_path, monkeypatch):
    """A fast (cached) AI reply must not leave the page with nothing to poll for."""
    store, key = _extracted(tmp_path)
    approve(store, key, store.get(key)["revision"])
    stale = store.get(key)  # read before the brainstorm saves
    monkeypatch.setattr(brainstorm, "_propose", lambda *a: ({"labour": LABOUR}, {}))
    assert brainstorm.kick(store, key, provider=object(), executor=Now()) is True
    assert brainstorm.status(key, stale)["status"] == "running"
    assert brainstorm.status(key, store.get(key))["status"] == "ready"


def test_ai_materials_list_replaces_reference_feeds_and_lists_the_rest_as_not_costed():
    config = {
        "materials": [
            {"id": "ref-feed-3", "name": "Wastewater influent", "stream_key": "s3", "origin": "reference_default"},
            {"id": "ref-feed-6", "name": "Sucrose feed", "stream_key": "s6", "origin": "reference_default"},
        ],
        "reference_defaults": {"questions": [{"id": "ref-feed-3", "question": "price?"},
                                             {"id": "ref-feed-6", "question": "price?"}]},
        "value_owners": {"materials.ref-feed-3": "reference_default", "materials.ref-feed-6": "reference_default"},
    }
    ai = {"materials": [{"id": "sucrose", "name": "Sucrose", "stream_key": "s6", "unit_price": 0.5}]}
    merged, added = brainstorm.merge(config, ai)
    assert [m["id"] for m in merged["materials"]] == ["sucrose"]
    assert [n["stream_key"] for n in merged["reference_defaults"]["not_costed"]] == ["s3"]
    assert merged["reference_defaults"]["questions"] == []
    assert "materials.ref-feed-3" not in merged["value_owners"]
    # An empty AI list keeps the reference feeds (nothing reviewed, nothing dropped).
    kept, _ = brainstorm.merge(config, {"materials": []})
    assert len(kept["materials"]) == 2
