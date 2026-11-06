import pytest
from backend.equipment_costing.unit_conversion.bridges.service import evaluate, describe
from backend.blocks.equipment.calculation import calculate_equipment


def fixture():
    report = {
        "entities": [
            {
                "kind": "equipment",
                "key": "cmp",
                "identifier": "CMP-9",
                "values": [],
                "stream_keys": ["inlet"],
            },
            {
                "kind": "material",
                "key": "inlet",
                "identifier": "IN",
                "values": [
                    {
                        "id": "n",
                        "property": "molar_flow",
                        "normalized_value": 10,
                        "normalized_unit": "kmol/h",
                        "status": "verified",
                        "sheet": "Balance",
                        "cell": "B2",
                    }
                ],
            },
        ]
    }
    spec = {
        "enabled": True,
        "model_id": "G271-042",
        "method": "standard_gas_flow",
        "measurement_id": "n",
        "inputs": {
            "molecular_weight_kg_kmol": 29,
            "reference_temperature_k": 288.15,
            "reference_pressure_bar": 1.01325,
            "reference_compressibility_z": 1,
        },
        "unit_context": {},
        "rationale": "Explicit synthetic reference-state assumption",
    }
    return report, spec


def test_reference_state_flow_and_reference_provenance_reach_cost_model():
    report, spec = fixture()
    result = evaluate(report, "cmp", spec)
    assert result["size_unit"] == "scfm" and result["size"] > 0
    assert (
        result["unit_context"]["input_gas_reference"]
        == result["unit_context"]["target_gas_reference"]
    )
    assert "288.15" in result["unit_context"]["target_gas_reference"]
    assert any(
        r["id"] == "standard_gas_flow"
        for r in describe(report, "cmp", "G271-042")["recipes"]
    )
    total, rows = calculate_equipment(
        report,
        {
            "equipment": [
                {
                    "equipment_key": "cmp",
                    "curve_id": "G271-042",
                    "unit_conversion": spec,
                    "costing_options": {"allow_unverified": True},
                }
            ]
        },
    )
    assert total.equipment[0].equipment_cost is not None
    assert rows[0]["costing_options"]["unit_context"].target_gas_reference


def test_reference_state_cannot_be_omitted_or_silently_assumed():
    report, spec = fixture()
    spec["inputs"].pop("reference_temperature_k")
    with pytest.raises(ValueError, match="explicit positive reference"):
        evaluate(report, "cmp", spec)
