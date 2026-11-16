"""Approved revenue edits refresh saved economics without AI or another button."""

import copy
import threading

from fastapi.testclient import TestClient

import backend.api.app as api
from backend.blocks.execution import run_stage
from backend.blocks.stage_workflow import approve
from backend.equipment_costing.cost_to_future.operating_prices import translate_operating_prices
from backend.tests.test_isolated_stages import study
from backend.tests.test_revenue_rates import request


def test_revenue_parent_and_yearly_price_bases_are_translated_together():
    original = {"price_basis": {"currency": "USD", "price_period": "2026-09"},
                "commercial_lines": [{"id": "fee", "price_basis": {"currency": "USD", "price_period": "2026"},
                                      "years": [{"year": 1, "rate": 1, "quantity": 100}]}]}
    before = copy.deepcopy(original)
    changed, audit = translate_operating_prices(original, target_basis=original["price_basis"],
                                                policy={"target_period": "2026-09"})
    parent = changed["commercial_lines"][0]
    assert parent["price_basis"] == parent["years"][0]["price_basis"] == original["price_basis"]
    assert parent["years"][0]["rate"] == "1"
    assert any(row.get("source_period") == "2026" for row in audit)
    assert original == before


def test_approved_revenue_save_queues_one_deterministic_recalculation(study, monkeypatch):
    store, key = study
    monkeypatch.setattr('backend.blocks.stage_workflow._brainstorm', lambda *args: None)
    run_stage(store, key, "engineering_data")
    approve(store, key, store.get(key)["revision"])
    run_stage(store, key, "equipment")
    run_stage(store, key, "capex")
    jobs = []
    class Held:
        def submit(self, fn, *args): jobs.append((fn, args))
    monkeypatch.setattr(api, "store", store)
    monkeypatch.setattr(api, "executor", Held())
    gate = threading.Lock()
    monkeypatch.setattr(api, "lock", gate)
    # Auto calculation must not restart background research.
    monkeypatch.setattr('backend.blocks.stage_workflow._brainstorm', lambda *args: (_ for _ in ()).throw(AssertionError("No AI on recalculation")))
    payload = request(store.get(key)).model_dump()
    client = TestClient(api.app)
    try:
        response = client.post(f'/api/assessments/{key}/revenue-rates', json=payload)
        assert response.status_code == 200, response.text
        assert response.json()['running'] is True
        assert len(jobs) == 1
        fn, args = jobs.pop()
        fn(*args)
        saved = store.get(key)
        assert not saved['running']
        assert saved['stage_runs']['revenue']['status'] == 'ready'
        assert saved['stage_runs']['opex']['status'] == 'ready'
        assert saved['results']['stages']['opex']['result']['complete'] is True
    finally:
        if gate.locked(): gate.release()
