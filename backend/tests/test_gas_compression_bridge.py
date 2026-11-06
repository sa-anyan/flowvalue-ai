import pytest
from backend.equipment_costing.unit_conversion import convert, identify_unit
from backend.equipment_costing.unit_conversion.bridges.gas import evaluate
from backend.equipment_costing.unit_conversion.bridges.derivations import derive


def cv(value, unit, target=None):
    return (
        identify_unit(unit).quantity
        if value == "quantity"
        else convert(value, unit, target).value
    )


def test_mass_and_molar_flow_use_same_canonical_compression_calculation():
    inputs = {
        "molecular_weight_kg_kmol": 20,
        "temperature_k": 300,
        "absolute_pressure_bar": 1,
        "discharge_pressure_bar": 2,
        "heat_capacity_ratio": 1.4,
        "efficiency": 0.75,
        "compressibility_z": 1,
    }
    mass = evaluate("gas_compression", 3600, "kg/h", inputs, cv)
    per_second = evaluate("gas_compression", 1, "kg/s", inputs, cv)
    molar = evaluate("gas_compression", 180, "kmol/h", inputs, cv)
    assert mass[0] > 0 and mass[1] == "kW"
    assert mass[0] == pytest.approx(per_second[0]) == pytest.approx(molar[0])
    assert not mass[2]["design_validated"]
    inputs["discharge_pressure_bar"] = 0.5
    with pytest.raises(ValueError):
        evaluate("gas_compression", 3600, "kg/h", inputs, cv)


def test_discharge_absolute_pressure_binding_preserves_source_and_gauge_basis():
    observations = [
        {
            "id": "outlet-pressure",
            "entity_key": "outlet",
            "property": "pressure",
            "value": 2,
            "unit": "barg",
            "sheet": "Balance",
            "cell": "C8",
        }
    ]
    result, audit = derive(
        [
            {
                "name": "discharge_pressure_bar",
                "method": "absolute_pressure",
                "measurement_ids": ["outlet-pressure"],
            }
        ],
        observations,
        {},
        {"atmospheric_pressure_pa": 101325},
    )
    assert result["discharge_pressure_bar"] == pytest.approx(3.01325)
    assert audit[0]["source_measurements"][0]["cell"] == "C8"
