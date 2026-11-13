"""Entry-page revenue set-up writes approvable sales lines without AI."""

import pytest

from backend.blocks.execution import run_stage
from backend.revenue.setup import apply
from backend.tests.test_autopilot import _study


def test_setup_approves_and_revenue_calculates_without_ai(tmp_path):
    import backend.api.app as api

    original = api.store
    try:
        store, key = _study(tmp_path)
        from backend.blocks.cashflow.schedule import apply_policy, make_policy

        state = store.get(key)
        state["analysis_schedule"] = make_policy(20, 2)
        state["plan"]["operating_economics"] = apply_policy(state["plan"].get("operating_economics", {}), state["analysis_schedule"])
        state = store.put(state, state["revision"])
        stream = next(e for e in state["stage_outputs"]["engineering_data"]["report"]["entities"]
                      if e["kind"] == "material")
        out = apply(store, key, state["revision"], {"currency": "USD", "price_period": "2026",
                    "sales": [{"stream_key": stream["key"], "name": "Water", "unit_price": 0.5, "quantity_unit": "kg"}]})
        assert out["approved"], out["questions"]
        assert "We sell Water" in out["state"]["revenue_description"]
        state = run_stage(store, key, "revenue", use_ai=False)
        assert state["stage_runs"]["revenue"]["status"] == "ready"
        missing = apply(store, key, state["revision"], {"sales": [{"stream_key": stream["key"], "name": "Water", "unit_price": None}],
                                                       "price_period": "2026"})
        assert not missing["approved"]
        with pytest.raises(ValueError):
            apply(store, key, missing["state"]["revision"], {"sales": [{"stream_key": "nope", "unit_price": 1}], "price_period": "2026"})
    finally:
        api.store = original
