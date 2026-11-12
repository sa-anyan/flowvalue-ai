"""Live stage progress and quick-match-aware equipment runs."""

import threading

from backend.blocks import progress


def test_progress_is_reported_and_finished():
    token = progress.begin("study-1", "equipment")
    progress.step("Proposing sizing inputs (AI)", 4, 28)
    live = progress.get("study-1")
    assert live["running"] and live["stage"] == "equipment" and (live["done"], live["total"]) == (4, 28)
    progress.end("study-1", token)
    assert progress.get("study-1")["running"] is False


def test_nested_stage_keeps_the_outer_run_open():
    outer = progress.begin("study-2", "engineering_data")
    inner = progress.begin("study-2", "equipment")
    assert inner is None and progress.get("study-2")["stage"] == "equipment"
    progress.end("study-2", inner)
    assert progress.get("study-2")["running"] is True
    progress.end("study-2", outer)
    assert progress.get("study-2")["running"] is False


def test_step_outside_a_run_is_ignored_and_threads_are_separate():
    progress.step("nothing running")  # no error
    seen = {}

    def worker():
        token = progress.begin("study-3", "capex")
        progress.step("Calculating")
        seen["step"] = progress.get("study-3")["step"]
        progress.end("study-3", token)

    t = threading.Thread(target=worker)
    t.start()
    t.join()
    assert seen["step"] == "Calculating" and progress.get("unknown") == {"running": False}


def test_progress_endpoint(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    import backend.api.app as api

    client = TestClient(api.app)
    assert client.get("/api/assessments/nope/progress").json() == {"running": False}
    token = progress.begin("study-4", "equipment")
    body = client.get("/api/assessments/study-4/progress").json()
    progress.end("study-4", token)
    assert body["running"] and body["stage"] == "equipment"


def test_equipment_run_skips_ai_matching_when_every_model_is_confirmed(monkeypatch):
    import backend.blocks.equipment.runner as runner

    called = []
    monkeypatch.setattr(runner, "match_report", lambda *a, **k: called.append(1) or {"matches": [], "batches": []})

    class Ctx:
        use_ai = True
        provider = None
        store = None
        report = {"entities": [{"key": "equipment:1", "kind": "equipment", "identifier": "P-1", "values": []}]}
        state = {"locked": [], "description": ""}
        plan = {"equipment": [{"equipment_key": "equipment:1", "curve_id": "G296-122",
                               "model_selection": {"origin": "user", "curve_id": "G296-122"}}]}

    monkeypatch.setattr("backend.equipment_costing.unit_conversion.bridges.automatic.resolve",
                        lambda report, plan, *a, **k: (plan, []))
    _, _, _, issues, matching, _, _ = runner.prepare(Ctx())
    assert called == [] and matching is None
    assert any("you confirmed a model for every item" in i for i in issues)


def test_model_reference_without_inputs_is_not_treated_as_user_inputs():
    from backend.equipment_costing.unit_conversion.bridges.automatic import _has_saved_inputs

    assert not _has_saved_inputs(None)
    assert not _has_saved_inputs({"model_id": "G296-122", "enabled": False})  # written by a model choice
    assert _has_saved_inputs({"model_id": "G296-122", "enabled": False, "method": "pump_power"})
    assert _has_saved_inputs({"enabled": False, "inputs": {"efficiency": 0.7}})
    assert _has_saved_inputs({"enabled": True})


def test_explicit_ai_run_fills_empty_rows_in_a_locked_section(monkeypatch):
    import backend.blocks.equipment.runner as runner

    seen = {}

    def fake_resolve(report, plan, *a, **k):
        seen.update(k)
        return plan, []

    monkeypatch.setattr("backend.equipment_costing.unit_conversion.bridges.automatic.resolve", fake_resolve)
    monkeypatch.setattr(runner, "match_report", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no rematch")))

    class Ctx:
        use_ai = True
        provider = None
        store = None
        report = {"entities": [{"key": "equipment:1", "kind": "equipment", "identifier": "P-1", "values": []}]}
        state = {"locked": ["equipment"], "description": ""}
        plan = {"equipment": [{"equipment_key": "equipment:1", "curve_id": "G296-122"}]}

    runner.prepare(Ctx())
    assert seen["use_ai"] is True and seen["locked"] is False  # sizing may fill empty rows
    Ctx.use_ai = False
    runner.prepare(Ctx())
    assert seen["locked"] is True


def test_resolver_preserves_saved_inputs_even_when_unlocked():
    from backend.equipment_costing.unit_conversion.bridges.automatic import resolve

    report = {"entities": [{"key": "equipment:1", "kind": "equipment", "identifier": "P-1", "values": []}]}
    plan = {"equipment": [{"equipment_key": "equipment:1", "curve_id": "G296-122", "size": 5.0},
                          {"equipment_key": "equipment:1x", "manual_price": {"amount": 1}}]}
    out, audits = resolve(report, plan, "", None, None, use_ai=False, locked=False)
    assert out["equipment"][0]["size"] == 5.0
    assert audits[0]["status"] == "preserved_existing_inputs"
