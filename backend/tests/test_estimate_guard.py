"""AI sizing estimates stay stable across runs; disagreement feeds Monte Carlo."""

import copy

import pytest

from backend.blocks.equipment.estimate_guard import TOLERANCE, guard
from backend.equipment_costing.unit_conversion.bridges.automatic import normalize_assumption

REPORT = {
    "entities": [
        {"key": "eq:r1", "kind": "equipment", "identifier": "R-001", "values": []},
        {"key": "st:5", "kind": "material", "identifier": "5",
         "values": [{"property": "mass_flow", "normalized_value": 125127.5, "normalized_unit": "kg/h"}]},
    ],
    "connections": [{"stream_key": "st:5", "equipment_key": "eq:r1", "role": "destination"}],
}


def _row(productivity, status="llm_estimate"):
    return {"equipment_key": "eq:r1", "unit_conversion": {
        "enabled": True, "origin": "llm_selected_python_equation", "model_id": "reactor",
        "inputs": {"volumetric_productivity_kg_m3_h": productivity, "working_fraction": 0.8},
        "input_provenance": {
            "volumetric_productivity_kg_m3_h": {"name": "volumetric_productivity_kg_m3_h", "value": productivity,
                                                "unit": "kg/m3/h", "status": status, "rationale": "AI"},
            "working_fraction": {"name": "working_fraction", "value": 0.8, "unit": "fraction", "status": status},
        }}}


def _size(value, unit="m3"):
    return [{"parsed_source": {"equipment_key": "eq:r1"}, "size": value, "size_unit": unit}]


def test_first_ai_size_is_anchored():
    plan, held = guard({"equipment": [_row(2)]}, _size(15.625), REPORT)
    g = plan["equipment"][0]["ai_estimate_guard"]
    assert held == [] and g["status"] == "anchored" and g["anchor"]["size"] == 15.625


def test_a_jump_on_the_same_mande_is_held_and_the_anchor_is_used():
    plan, _ = guard({"equipment": [_row(2)]}, _size(15.625), REPORT)
    plan["equipment"][0]["unit_conversion"] = _row(1)["unit_conversion"]  # a later AI run re-estimates
    plan, held = guard(plan, _size(156.25), REPORT)
    row = plan["equipment"][0]
    g = row["ai_estimate_guard"]
    assert held == ["eq:r1"] and g["status"] == "held"
    assert row["unit_conversion"]["inputs"]["volumetric_productivity_kg_m3_h"] == 2  # anchored estimate restored
    assert g["held"]["size"] == 156.25 and g["held"]["drift"] == pytest.approx(9.0)
    assert any(a["name"] == "volumetric_productivity_kg_m3_h" and a["value"] == 1 for a in g["held"]["assumptions"])
    # The two AI estimates' disagreement becomes the Monte Carlo range.
    p = row["unit_conversion"]["input_provenance"]["volumetric_productivity_kg_m3_h"]
    assert (p["low"], p["high"]) == (1, 2)
    # Next run: the resolver keeps the saved (anchored) inputs, so it is stable.
    plan, held = guard(plan, _size(15.625), REPORT)
    assert held == [] and plan["equipment"][0]["ai_estimate_guard"]["status"] == "stable"
    assert len(plan["equipment"][0]["ai_estimate_guard"]["proposals"]) == 1


def test_small_changes_within_tolerance_are_kept():
    plan, _ = guard({"equipment": [_row(2)]}, _size(15.625), REPORT)
    plan["equipment"][0]["unit_conversion"] = _row(1.8)["unit_conversion"]
    size = 15.625 * (1 + TOLERANCE / 2)
    plan, held = guard(plan, _size(size), REPORT)
    assert held == [] and plan["equipment"][0]["unit_conversion"]["inputs"]["volumetric_productivity_kg_m3_h"] == 1.8
    assert plan["equipment"][0]["ai_estimate_guard"]["anchor"]["size"] == 15.625  # drift never creeps


def test_a_changed_mande_or_a_user_input_re_anchors_instead_of_holding():
    plan, _ = guard({"equipment": [_row(2)]}, _size(15.625), REPORT)
    changed = copy.deepcopy(REPORT)
    changed["entities"][1]["values"][0]["normalized_value"] = 999999.0
    plan["equipment"][0]["unit_conversion"] = _row(1)["unit_conversion"]
    plan, held = guard(plan, _size(156.25), changed)
    assert held == [] and plan["equipment"][0]["ai_estimate_guard"]["anchor"]["size"] == 156.25
    plan["equipment"][0]["unit_conversion"] = _row(0.5, status="user_input")["unit_conversion"]
    plan, held = guard(plan, _size(312.5), changed)
    g = plan["equipment"][0]["ai_estimate_guard"]
    assert held == [] and g["anchor"]["by"] == "user" and g["anchor"]["size"] == 312.5


def test_priced_by_hand_or_unsized_items_are_left_alone():
    row = {**_row(2), "manual_price": {"amount": 1000}}
    plan, held = guard({"equipment": [row]}, _size(15.625), REPORT)
    assert held == [] and "ai_estimate_guard" not in plan["equipment"][0]
    plan, held = guard({"equipment": [_row(2)]}, _size(None), REPORT)
    assert "ai_estimate_guard" not in plan["equipment"][0]


def test_ai_assumption_ranges_are_converted_and_checked():
    a = normalize_assumption({"name": "residence_time_h", "value": 30, "low": 20, "high": 60, "unit": "min",
                              "rationale": "r", "limitations": "l"})
    assert a["unit"] == "h" and a["value"] == pytest.approx(0.5)
    assert (a["low"], a["high"]) == (pytest.approx(1 / 3), pytest.approx(1.0))
    bad = normalize_assumption({"name": "working_fraction", "value": 0.8, "low": 0.9, "high": 0.95,
                                "unit": "fraction", "rationale": "r", "limitations": "l"})
    assert "low" not in bad and "high" not in bad  # value outside its own range: no range used
    none = normalize_assumption({"name": "working_fraction", "value": 0.8, "low": None, "high": None,
                                 "unit": "fraction", "rationale": "r", "limitations": "l"})
    assert "low" not in none


def test_monte_carlo_varies_an_ai_assumption_that_has_a_range():
    from backend.scenarios_and_uncertainty.monte_carlo.discovery import discover

    row = _row(2)
    row["curve_id"] = "openpytea:reactor"
    p = row["unit_conversion"]["input_provenance"]["volumetric_productivity_kg_m3_h"]
    p.update(low=1, high=3)
    state = {"plan": {"equipment": [row]}, "parsed": {"report": REPORT}}
    params = {p["id"]: p for p in discover(state)["settings"]["parameters"]}
    item = next(v for k, v in params.items() if k.endswith("volumetric_productivity_kg_m3_h"))
    assert item["enabled"] and (item["minimum"], item["mode"], item["maximum"]) == (1, 2, 3)
    fixed = next(v for k, v in params.items() if k.endswith("working_fraction"))
    assert not fixed["enabled"]  # no range: held at its value, not given a made-up spread


def test_the_equipment_run_holds_a_jump_and_prices_the_anchored_size(monkeypatch):
    """Wiring: the run uses the guard's restored inputs for the price it reports."""
    from types import SimpleNamespace

    from backend.blocks.equipment import runner

    def fake_calculate(report, plan, policy=None):
        row = plan["equipment"][0]
        inputs = row["unit_conversion"]["inputs"]
        size = 25 / inputs["volumetric_productivity_kg_m3_h"] / inputs["working_fraction"]
        line = {"parsed_source": {"equipment_key": "eq:r1"}, "size": size, "size_unit": "m3"}
        return SimpleNamespace(equipment=[], size=size), [line]

    calls = []

    def fake_prepare(ctx):
        return REPORT, copy.deepcopy(ctx.plan), {}, [], None, [], {}

    monkeypatch.setattr(runner, "prepare", fake_prepare)
    monkeypatch.setattr(runner, "calculate_equipment", lambda *a: (calls.append(1), fake_calculate(*a))[1])
    monkeypatch.setattr(runner, "plain", lambda total: {"size": total.size, "equipment": []})
    monkeypatch.setattr(runner, "identity_register", lambda *a: {})
    import backend.orchestration.pricing_status as ps
    import backend.equipment_resolution.review as rv
    monkeypatch.setattr(ps, "annotate", lambda *a: None)
    monkeypatch.setattr(rv, "review", lambda *a, **k: {})
    monkeypatch.setattr(runner, "Product", lambda result, payload, updates, **k: SimpleNamespace(result=result, payload=payload, updates=updates, **k))

    first, _ = guard({"equipment": [_row(2)]}, _size(15.625), REPORT)  # anchored by an earlier run
    plan = copy.deepcopy(first)
    plan["equipment"][0]["unit_conversion"] = _row(0.2)["unit_conversion"]  # the AI re-estimates: 156.25 m3
    ctx = SimpleNamespace(plan=plan, state={"plan": plan, "locked": []}, report=REPORT, use_ai=False,
                          provider=None, store=None, upstream={})
    product = runner.calculate(ctx)
    assert product.result["size"] == pytest.approx(15.625)  # priced on the anchored estimate
    assert len(calls) == 2  # recalculated once after holding
    held = [g for g in product.result["estimate_guard"] if g["status"] == "held"]
    assert held and held[0]["held"]["size"] == pytest.approx(156.25)
