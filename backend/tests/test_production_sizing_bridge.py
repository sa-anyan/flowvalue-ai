"""Production sizing remains an explicit scenario, never a fabricated broth flow."""

import copy
from unittest.mock import patch

import pytest
from backend.equipment_costing.unit_conversion.bridges.service import evaluate


def run(inputs):
    report = {
        "entities": [
            {
                "key": "reactor",
                "kind": "equipment",
                "identifier": "BIO-7",
                "values": [],
                "stream_keys": [],
            }
        ]
    }
    before = copy.deepcopy(report)
    with patch(
        "backend.equipment_costing.unit_conversion.bridges.service.model_contract",
        return_value=({"id": "test"}, {"quantity": "volume"}, "m3"),
    ):
        result = evaluate(
            report,
            "reactor",
            {
                "model_id": "test",
                "method": "vessel_productivity",
                "measurement_id": None,
                "inputs": inputs,
            },
        )
    assert report == before
    return result


def test_productivity_scenario_without_invented_flow_or_connection():
    result = run(
        {
            "product_rate_kg_h": 120,
            "volumetric_productivity_kg_m3_h": 4,
            "production_allocation_fraction": 0.5,
            "working_fraction": 0.75,
        }
    )
    assert result["size"] == pytest.approx(20)
    assert result["source_measurements"] == []
    assert result["validation"]["engineering_design_validated"] is False


@pytest.mark.parametrize(
    "override",
    [
        {"volumetric_productivity_kg_m3_h": 0},
        {"product_rate_kg_h": -1},
        {"working_fraction": 1.1},
        {"production_allocation_fraction": 2},
    ],
)
def test_invalid_productivity_scenarios_rejected(override):
    with pytest.raises(ValueError):
        run(
            {
                "product_rate_kg_h": 120,
                "volumetric_productivity_kg_m3_h": 4,
                "production_allocation_fraction": 0.5,
                "working_fraction": 0.75,
                **override,
            }
        )
