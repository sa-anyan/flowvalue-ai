"""Background analyst: parallel per-stage research from upload, saved stage by stage."""

import threading
import time

from backend.blocks import analyst
from backend.blocks.opex import brainstorm
from backend.tests.test_opex_brainstorm import LABOUR, _extracted


class Fake:
    """A provider that answers per stage; optional gates hold a stage back."""

    model = "fake"

    def __init__(self, gates=None, fail=()):
        self.calls, self.gates, self.fail = [], gates or {}, set(fail)
        self.lock, self.active, self.peak = threading.Lock(), 0, 0

    def generate(self, *, instructions, context, schema):
        stage = context["stage"]
        with self.lock:
            self.calls.append(stage)
            self.active += 1
            self.peak = max(self.peak, self.active)
        try:
            if stage in self.gates:
                self.gates[stage].wait(5)
            else:
                time.sleep(0.4)  # long enough that all five calls overlap
            if stage in self.fail:
                raise RuntimeError("model timeout")
            factors = []
            if stage == "capex":
                ranges = context["published_factor_ranges"]
                factors = [{"id": r["id"], "fraction": r["minimum"], "position": "low", "reasoning": ["compact layout"]}
                           for r in ranges]
                factors.append({"id": ranges[0]["id"], "fraction": 99.0, "position": "high", "reasoning": ["bad"]})
            return {"summary": f"{stage} summary", "factors": factors, "questions": [],
                    "points": [{"title": "Layout", "text": "Compact plot", "why": ["short transfers"],
                                "would_change_if": ["remote tie-in"], "evidence": ["T-1", "nonsense-id"]}]}
        finally:
            with self.lock:
                self.active -= 1


def _wait(store, key, stages, timeout=10):
    end = time.time() + timeout
    while time.time() < end:
        saved = (store.get(key).get("analyst") or {}).get("stages") or {}
        if all(s in saved for s in stages):
            return saved
        time.sleep(0.05)
    raise AssertionError(f"analyst stages not saved: {stages}")


def _quiet_opex(monkeypatch):
    monkeypatch.setattr(brainstorm, "_propose", lambda *a: ({"labour": LABOUR}, {"model": "fake"}))


def test_all_stages_start_at_once_and_save_independently(tmp_path, monkeypatch):
    store, key = _extracted(tmp_path)
    _quiet_opex(monkeypatch)
    gate = threading.Event()
    fake = Fake(gates={"financial": gate})
    started = analyst.kick(store, key, provider=fake)
    assert set(started) == set(analyst.STAGES)
    # Four stages are saved while financial is still being researched.
    saved = _wait(store, key, ("equipment", "capex", "opex", "revenue"))
    assert "financial" not in saved
    assert analyst.status(key, store.get(key))["financial"]["status"] == "running"
    gate.set()
    saved = _wait(store, key, analyst.STAGES)
    assert fake.peak == 5  # all five calls were in flight together
    assert saved["capex"]["summary"] == "capex summary"
    assert saved["equipment"]["points"][0]["evidence"] == ["T-1"]  # unknown ids removed
    # The structured OPEX inputs ran too, before any approval.
    for _ in range(100):
        if (store.get(key).get("opex_brainstorm") or {}).get("status") == "ready":
            break
        time.sleep(0.05)
    assert store.get(key)["plan"]["operating_economics"]["labour"][0]["role"] == "Electricians"


def test_saves_and_stage_runs_never_restart_the_analyst(tmp_path, monkeypatch):
    store, key = _extracted(tmp_path)
    _quiet_opex(monkeypatch)
    fake = Fake()
    analyst.kick(store, key, provider=fake)
    _wait(store, key, analyst.STAGES)
    calls = len(fake.calls)
    state = store.get(key)
    state["plan"]["capex"]["selected_factors"]["piping"] = 0.2  # a user edit
    state.setdefault("results", {})["stages"] = {"capex": {"result": {"total_capex": 1}}}
    store.put(state, state["revision"])
    assert analyst.kick(store, key, provider=fake) == []
    assert len(fake.calls) == calls


def test_quick_answers_rerun_only_the_stages_that_read_them(tmp_path, monkeypatch):
    store, key = _extracted(tmp_path)
    _quiet_opex(monkeypatch)
    fake = Fake()
    analyst.kick(store, key, provider=fake)
    _wait(store, key, analyst.STAGES)
    state = store.get(key)
    state["project_context"] = {"location": "Ghana", "project_type": "retrofit"}
    store.put(state, state["revision"])
    started = analyst.kick(store, key, provider=fake)
    assert "equipment" not in started and {"capex", "opex", "financial"} <= set(started)


def test_capex_positions_apply_inside_the_range_and_never_over_the_user(tmp_path, monkeypatch):
    store, key = _extracted(tmp_path)
    _quiet_opex(monkeypatch)
    state = store.get(key)
    kind, ranges = analyst._capex_ranges(state)
    user_pick = ranges[1]["id"]
    state.setdefault("plan", {})["capex"] = {"model_id": "garrett", "process_type": kind,
                                             "factor_selection": "midpoint",
                                             "selected_factors": {user_pick: ranges[1]["maximum"]}}
    store.put(state, state["revision"])
    analyst.kick(store, key, provider=Fake(), stages=("capex",))
    saved = _wait(store, key, ("capex",))
    capex = store.get(key)["plan"]["capex"]
    assert capex["selected_factors"][user_pick] == ranges[1]["maximum"]  # the user's value stays
    assert user_pick not in saved["capex"]["applied"]
    first = ranges[0]["id"]
    assert capex["selected_factors"][first] == ranges[0]["minimum"] and first in saved["capex"]["applied"]
    assert all(f["fraction"] != 99.0 for f in saved["capex"]["factors"])  # out of range dropped


def test_one_failed_stage_does_not_hold_back_the_others(tmp_path, monkeypatch):
    store, key = _extracted(tmp_path)
    _quiet_opex(monkeypatch)
    analyst.kick(store, key, provider=Fake(fail={"revenue"}))
    saved = _wait(store, key, analyst.STAGES)
    assert saved["revenue"]["status"] == "failed" and "timeout" in saved["revenue"]["error"]
    assert all(saved[s]["status"] == "ready" for s in analyst.STAGES if s != "revenue")


def test_no_ai_means_no_analyst(tmp_path, monkeypatch):
    store, key = _extracted(tmp_path)
    monkeypatch.setattr(brainstorm, "ai_available", lambda: False)
    assert analyst.kick(store, key) == []
    assert analyst.status(key, store.get(key)) == {}


def test_capex_settings_written_by_the_analyst_are_valid_capex_inputs(tmp_path, monkeypatch):
    """Analyst bookkeeping stays in its own record: the CAPEX engine must accept every key."""
    from dataclasses import fields

    from backend.capex.models import CapexInputs

    store, key = _extracted(tmp_path)
    _quiet_opex(monkeypatch)
    analyst.kick(store, key, provider=Fake(), stages=("capex",))
    saved = _wait(store, key, ("capex",))
    capex = store.get(key)["plan"]["capex"]
    accepted = {f.name for f in fields(CapexInputs)} | {"model_id", "delivery_basis"}  # popped by the runner
    assert set(capex) <= accepted, set(capex) - accepted
    assert saved["capex"]["applied_values"] and set(saved["capex"]["applied"]) == set(saved["capex"]["applied_values"])
