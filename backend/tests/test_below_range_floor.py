"""Founder decision (11 Nov 2026): equipment below a correlation's range is priced
at the correlation's minimum size (option B), flagged as an explicit assumption.

Applies to Garrett graph curves and OpenPyTEA correlations. Sizes above the
range are unaffected. Each item can opt back into the previous behaviour with
below_range_policy="extrapolate".
"""

import pytest

from backend.equipment_costing.registry import estimate_cost, list_equipment_models

MODELS = {m["id"]: m for m in list_equipment_models(source="all")}


def price(model_id, size, **options):
    return estimate_cost(model_id, size, size_unit=MODELS[model_id]["size_unit"], allow_unverified=True, **options)


@pytest.mark.parametrize("model_id", ["G279-066", "G296-122", "G303-144"])
def test_garrett_below_range_priced_at_minimum_anchor(model_id):
    lower = MODELS[model_id]["observed_size_range"][0]
    floored = price(model_id, lower / 50)
    at_minimum = price(model_id, lower)
    assert floored.amount == pytest.approx(at_minimum.amount)
    assert not floored.estimate.extrapolated
    floor = floored.evidence["below_range_floor"]
    assert floor["priced_at_size"] == lower and floor["size_ratio"] == pytest.approx(50)
    assert any(i.startswith("BELOW-RANGE FLOOR") for i in floored.issues)


def test_garrett_in_range_and_above_range_unchanged():
    in_range = price("G279-066", 50)
    assert "below_range_floor" not in in_range.evidence
    above = price("G279-066", 1400)
    assert above.estimate.extrapolated and "below_range_floor" not in above.evidence


def test_garrett_per_item_override_restores_extrapolation():
    lower = MODELS["G279-066"]["observed_size_range"][0]
    extrapolated = price("G279-066", lower / 50, below_range_policy="extrapolate")
    assert extrapolated.estimate.extrapolated
    assert extrapolated.amount < price("G279-066", lower / 50).amount


def test_openpytea_below_range_priced_at_published_minimum():
    cyclone = "openpytea:cyclones_seider_2013"  # published range 200-100,000 cfm
    floored = price(cyclone, 50)
    assert floored.amount == pytest.approx(price(cyclone, 200).amount)
    floor = floored.evidence["below_range_floor"]
    assert floor["priced_at_size"] == 200 and floor["size_ratio"] == pytest.approx(4)
    assert any(i.startswith("BELOW-RANGE FLOOR") for i in floored.issues)


def test_openpytea_override_and_above_range_stay_strict():
    cyclone = "openpytea:cyclones_seider_2013"
    with pytest.raises(ValueError, match="MODEL_OUT_OF_RANGE"):
        price(cyclone, 50, below_range_policy="extrapolate")
    with pytest.raises(ValueError, match="MODEL_OUT_OF_RANGE"):
        price(cyclone, 200000)


def test_unknown_policy_is_rejected():
    with pytest.raises(ValueError, match="below_range_policy"):
        price("G279-066", 50, below_range_policy="guess")


def test_libraries_without_the_floor_ignore_the_setting():
    nottingham = next(i for i, m in MODELS.items() if m.get("source") == "nottingham" and "PUMP" in i)
    a = price(nottingham, 5)
    b = price(nottingham, 5, below_range_policy="extrapolate")
    assert a.amount == b.amount


def test_sizing_step_keeps_openpytea_below_range():
    from backend.equipment_costing.unit_conversion.bridges.automatic import PROMPT

    assert "Do not switch library only because the size is small" in PROMPT
