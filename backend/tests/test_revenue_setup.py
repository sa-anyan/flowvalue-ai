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


def test_a_stream_without_a_usable_flow_is_refused_with_a_clear_reason():
    from backend.revenue.setup import _check_flow

    stream = {"key": "material:x", "identifier": "18", "kind": "material", "values": [
        {"property": "description", "original_value": "Fermented Mash to Distillation"},
        {"property": "mass_flow", "original_value": "#REF!", "normalized_value": None},
        {"property": "component_mass_flow", "component": "Fibre", "original_value": "#REF!", "normalized_value": None},
    ]}
    report = {"entities": [stream], "connections": []}
    with pytest.raises(ValueError) as error:
        _check_flow(report, stream, None, "kg")
    message = str(error.value)
    assert message.startswith("Stream 18 (Fermented Mash to Distillation) has no usable mass flow")
    assert "#REF!" in message
    with pytest.raises(ValueError, match="Fibre in stream 18"):
        _check_flow(report, stream, "Fibre", "kg")


def test_two_components_of_one_stream_are_sold_without_double_counting():
    from backend.revenue.setup import _review_shared_streams

    stream = {"key": "s13", "identifier": "13", "kind": "material",
              "values": [{"property": "description", "original_value": "Treated Water"}]}
    report = {"entities": [stream]}
    sales = [{"name": "Lignin", "stream_key": "s13", "component": "Lignin"},
             {"name": "Water", "stream_key": "s13", "component": "Water"}]
    _review_shared_streams(report, sales)
    assert all("Different components" in s["shared_stream_review"]["basis"] for s in sales)
    whole = [{"name": "Treated water", "stream_key": "s13", "component": None},
             {"name": "Lignin", "stream_key": "s13", "component": "Lignin"}]
    with pytest.raises(ValueError, match="already includes Lignin"):
        _review_shared_streams(report, whole)
