"""Chemical water balance to an evaporation-based cost coordinate, not wet feed."""

import pytest
from backend.equipment_costing.unit_conversion.bridges.service import evaluate, describe
from backend.equipment_costing.registry import estimate_cost

MODEL = "openpytea:spray_dryer_seider_2013"


def report():
    return {
        "entities": [
            {
                "key": "dryer",
                "kind": "equipment",
                "identifier": "D-101",
                "values": [],
                "stream_keys": ["feed", "powder"],
            },
            *[
                {
                    "key": key,
                    "kind": "material",
                    "identifier": key,
                    "values": [
                        {
                            "id": key + "-water",
                            "property": "component_mass_flow",
                            "component": "Water",
                            "normalized_value": amount,
                            "normalized_unit": "kg/h",
                            "status": "verified",
                            "sheet": "MEB",
                            "cell": cell,
                        }
                    ],
                }
                for key, amount, cell in [("feed", 19, "G1"), ("powder", 5, "G2")]
            ],
        ]
    }


def specification():
    return {
        "model_id": MODEL,
        "method": "dryer_evaporation",
        "measurement_id": "feed-water",
        "outlet_measurement_id": "powder-water",
        "inputs": {},
        "rationale": "Selected dryer water boundary",
    }


def test_water_removal_is_cost_coordinate_and_has_lineage():
    result = evaluate(report(), "dryer", specification())
    assert result["size"] == pytest.approx(14 / 0.45359237)
    assert result["size_unit"] == "lb/h"
    assert {v["cell"] for v in result["source_measurements"]} == {"G1", "G2"}
    cost = estimate_cost(MODEL, result["size"], size_unit=result["size_unit"])
    assert cost.estimate.amount > 0
    assert any(
        r["id"] == "dryer_evaporation"
        for r in describe(report(), "dryer", MODEL)["recipes"]
    )


@pytest.mark.parametrize("change", ["same_stream", "wrong_component", "no_removal"])
def test_invalid_drying_boundaries_are_rejected(change):
    data, spec = report(), specification()
    if change == "same_stream":
        spec["outlet_measurement_id"] = spec["measurement_id"]
    elif change == "wrong_component":
        data["entities"][1]["values"][0]["component"] = "Protein"
    else:
        data["entities"][2]["values"][0]["normalized_value"] = 20
    with pytest.raises(ValueError):
        evaluate(data, "dryer", spec)


def test_total_wet_feed_cannot_be_used_as_evaporation_rate():
    data, spec = report(), specification()
    observation = data["entities"][1]["values"][0]
    observation.update(property="mass_flow", component=None, normalized_value=114)
    spec["method"] = "direct"
    with pytest.raises(ValueError, match="EVAPORATION_BASIS_REQUIRED"):
        evaluate(data, "dryer", spec)
