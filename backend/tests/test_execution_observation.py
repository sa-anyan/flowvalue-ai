from copy import deepcopy
from datetime import datetime, timezone
import json
from types import SimpleNamespace

import pytest

from backend.blocks import execution
from backend.blocks.models import DataRequired, Product
from backend.orchestration.calculation_receipts import semantic_digest
from backend.revenue.authority import update
from backend.tests.test_isolated_stages import study


class RecordingStore:
    def __init__(self, initial):
        self.state = deepcopy(initial)
        self.writes = []

    def get(self, key):
        return deepcopy(self.state)

    def put(self, state, expected):
        assert expected == self.state["revision"]
        self.state = deepcopy(dict(state, revision=expected + 1))
        self.writes.append(deepcopy(self.state))
        return deepcopy(self.state)

    def workbook(self, key):
        return b"fixture"


@pytest.fixture
def fixed_clock(monkeypatch):
    instant = datetime(2026, 1, 1, tzinfo=timezone.utc)
    monkeypatch.setattr(execution, "datetime", SimpleNamespace(now=lambda tz: instant))
    monkeypatch.setattr(execution, "time", SimpleNamespace(monotonic=lambda: 1))


def fresh_stage(state, stage, payload):
    state["stage_outputs"][stage] = payload
    state["stage_runs"][stage] = {
        "status": "ready", "input_hash": execution.input_fingerprint(state, stage),
        "output_hash": execution._digest(payload),
    }


@pytest.mark.parametrize("outcome", ["ready", "partial", "failed", "blocked", "runner_blocked"])
def test_observation_preserves_stage_and_storage(fixed_clock, monkeypatch, outcome):
    state = execution.initialize({"id": "fixture", "revision": 0, "plan": {}})
    if outcome != "blocked":
        fresh_stage(state, "engineering_data", {"report": {"entities": []}})
        fresh_stage(state, "revenue", {"revenue": {"value": "20"}})
    calls = []

    def runner(ctx):
        calls.append(tuple(ctx.upstream))
        if outcome == "failed":
            raise RuntimeError("fixture failure")
        if outcome == "runner_blocked":
            raise DataRequired("fixture needs inputs")
        return Product({"amount": "12.50"}, {"years": {"1": "12.50"}},
                       complete=outcome != "partial")

    monkeypatch.setattr(execution, "get_runner", lambda block: runner)
    baseline, observed = RecordingStore(state), RecordingStore(state)
    assert execution.run_stage(baseline, "fixture", "opex") == execution.run_stage(
        observed, "fixture", "opex", observation_collector=(events := []).append,
        observation_scenario_id="prototype",
    )
    assert baseline.writes == observed.writes
    event, = events
    assert event.attempt_id == event.dispatch.attempt_id
    assert event.scope.scenario_id == "prototype"
    assert event.outcome == ("blocked" if outcome == "runner_blocked" else outcome)
    assert event.emitted_methods_json == event.source_observation_ids == ()
    assert event.consumed_upstream == ()
    assert [name for name, _ in event.dispatch.supplied_upstream] == (
        [] if outcome == "blocked" else ["engineering_data", "revenue"]
    )
    assert len(calls) == (0 if outcome == "blocked" else 2)
    assert event.complete is ({"ready": True, "partial": False}.get(outcome))
    assert (event.result_digest is not None) == (outcome in {"ready", "partial"})


def test_observer_failure_logs_without_changing_persistence(fixed_clock, monkeypatch, caplog):
    state = execution.initialize({"id": "fixture", "revision": 0, "plan": {}})
    monkeypatch.setattr(execution, "get_runner", lambda _: lambda ctx: Product({"amount": 1}))

    def fail(_):
        raise RuntimeError("internal callback detail")

    baseline, observed = RecordingStore(state), RecordingStore(state)
    assert execution.run_stage(baseline, "fixture", "engineering_data") == execution.run_stage(
        observed, "fixture", "engineering_data", observation_collector=fail,
    )
    assert baseline.writes == observed.writes
    assert "B09 execution observation failed in publish_observation (RuntimeError)" in caplog.text
    assert "internal callback detail" not in caplog.text


def test_financial_inputs_and_display_ledger_are_observed_separately(study, fixed_clock, monkeypatch):
    from backend.blocks.financial import runner

    store, key = study
    state = execution.run_stage(store, key, "engineering_data")
    update(store, key, state["revision"], approve=True)
    for stage in ("equipment", "capex", "revenue", "opex"):
        state = execution.run_stage(store, key, stage)

    calculate = runner.calculate
    products = []

    def once(ctx):
        product = calculate(ctx)
        products.append(product)
        return product

    monkeypatch.setattr(runner, "calculate", once)
    baseline = RecordingStore(state)
    expected = execution.run_stage(baseline, key, "financial")
    events = []
    actual = execution.run_stage(store, key, "financial", observation_collector=events.append)
    assert len(products) == 2
    assert actual == expected == store.get(key)
    product = products[-1]
    assert product.payload.keys() == {"financial_inputs"}
    assert len(product.result["ledger"]) == 22
    event, = events
    assert event.handoff_digest == semantic_digest(product.payload)
    assert event.result_digest == semantic_digest(product.result)
    assert event.handoff_digest != event.result_digest
    assert event.financial_ledger_digest == semantic_digest(product.result["ledger"])
    assert event.effective_inputs == (("financial_inputs", semantic_digest(product.payload["financial_inputs"])),)
    assert event.consumed_upstream == ("capex", "opex", "revenue")


def test_dispatch_is_frozen_and_only_explicit_sizing_evidence_is_reported(fixed_clock, monkeypatch):
    state = execution.initialize({"id": "fixture", "revision": 0, "plan": {}})
    fresh_stage(state, "engineering_data", {"report": {"entities": []}})
    emitted = {
        "method_id": "vessel_hold_up", "method_version": "1.0.0",
        "implementation_fingerprint": "sha256:fixture",
        "fingerprint_scheme": "test", "execution_layer": "native",
    }
    upstream_digest = semantic_digest(state["stage_outputs"]["engineering_data"])

    def runner(ctx):
        ctx.upstream["engineering_data"]["report"]["mutated_by_fixture"] = True
        return Product({"equipment": [{"parsed_source": {"sizing": {
            "calculation": {"engineering_method": emitted},
            "source_measurements": [{"observation_id": "observed:1"}, {"id": "local-only"}],
        }}}]}, {"total": "12.50"})

    monkeypatch.setattr(execution, "get_runner", lambda _: runner)
    events = []
    execution.run_stage(RecordingStore(state), "fixture", "equipment", observation_collector=events.append)
    event, = events
    assert event.dispatch.supplied_upstream == (("engineering_data", upstream_digest),)
    assert event.source_observation_ids == ("observed:1",)
    assert tuple(map(json.loads, event.emitted_methods_json)) == (emitted,)


def test_dispatch_capture_failure_leaves_runner_and_store_alone(fixed_clock, monkeypatch, caplog):
    state = execution.initialize({"id": "fixture", "revision": 0, "plan": {}})
    monkeypatch.setattr(execution, "get_runner", lambda _: lambda ctx: Product({"amount": 1}))

    def fail(*args):
        raise ValueError("unavailable evidence")

    monkeypatch.setattr(execution, "capture_dispatch", fail)
    baseline, observed = RecordingStore(state), RecordingStore(state)
    events = []
    assert execution.run_stage(baseline, "fixture", "engineering_data") == execution.run_stage(
        observed, "fixture", "engineering_data", observation_collector=events.append,
    )
    assert baseline.writes == observed.writes
    assert events == []
    assert "B09 execution observation failed" in caplog.text
