"""Editing sizing on the Equipment page: impossible values are refused, model changes keep sizing."""

import pytest

from backend.blocks.equipment.runner import follow_model_change
from backend.equipment_costing.unit_conversion.bridges.service import check_physical_bounds

VOLUME_A = "openpytea:vertical_cylinder_perry_1996"
VOLUME_B = "openpytea:cone_roof_tank_towler_2010"
AREA = "openpytea:clarifier_steel_seider_2013"


def _row(curve, conversion_model, **extra):
    return {"equipment_key": "eq:t", "curve_id": curve, **extra,
            "unit_conversion": {"enabled": True, "model_id": conversion_model, "method": "vessel_volume",
                                "inputs": {"density_kg_m3": 1000, "residence_time_h": 24, "working_fraction": 0.8},
                                "derivations": [{"name": "density_kg_m3", "method": "density_from_flows"}]}}


@pytest.mark.parametrize("name,value,message", [
    ("working_fraction", 3.8, "between 0 and 1"),
    ("working_fraction", 0, "between 0 and 1"),
    ("efficiency", 1.2, "between 0 and 1"),
    ("residence_time_h", 0, "greater than 0"),
    ("density_kg_m3", -5, "greater than 0"),
])
def test_impossible_sizing_values_are_refused_with_the_input_named(name, value, message):
    with pytest.raises(ValueError) as error:
        check_physical_bounds({name: value})
    assert message in str(error.value) and str(value).rstrip("0").rstrip(".") in str(error.value)


def test_plausible_values_and_ratios_above_one_pass():
    check_physical_bounds({"working_fraction": 0.8, "efficiency": 1, "residence_time_h": 48,
                           "heat_capacity_ratio": 1.4, "compressibility_z": 1.02, "density_kg_m3": None})


def test_a_new_model_sized_by_the_same_quantity_keeps_the_mande_sizing():
    [row] = follow_model_change([_row(VOLUME_B, VOLUME_A)])
    assert row["unit_conversion"]["model_id"] == VOLUME_B
    assert row["unit_conversion"]["derivations"][0]["name"] == "density_kg_m3"  # M&E link kept
    assert row["unit_conversion"]["inputs"]["residence_time_h"] == 24


def test_a_model_sized_differently_or_a_typed_price_is_left_alone():
    [row] = follow_model_change([_row(AREA, VOLUME_A)])
    assert row["unit_conversion"]["model_id"] == VOLUME_A  # volume sizing cannot drive an area model
    [priced] = follow_model_change([_row(VOLUME_B, VOLUME_A, manual_price={"amount": 1000})])
    assert priced["unit_conversion"]["model_id"] == VOLUME_A
    [unknown] = follow_model_change([_row("not-a-model", VOLUME_A)])
    assert unknown["unit_conversion"]["model_id"] == VOLUME_A
