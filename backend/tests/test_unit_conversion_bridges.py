"""User inputs, dimensional conversion and explicit engineering bridges."""

import copy
from unittest.mock import patch
import pytest
from backend.equipment_costing.unit_conversion.bridges.service import evaluate, describe

REPORT = {
    "entities": [
        {
            "key": "e",
            "identifier": "E-1",
            "kind": "equipment",
            "stream_keys": ["s"],
            "values": [],
        },
        {
            "key": "s",
            "identifier": "S-1",
            "kind": "material",
            "values": [
                {
                    "id": "m",
                    "property": "mass_flow",
                    "normalized_value": 1000.0,
                    "normalized_unit": "kg/h",
                    "status": "verified",
                    "sheet": "Balance",
                    "cell": "A1",
                },
                {
                    "id": "n",
                    "property": "molar_flow",
                    "normalized_value": 1.0,
                    "normalized_unit": "kmol/h",
                    "status": "verified",
                    "sheet": "Balance",
                    "cell": "A2",
                },
                {
                    "id": "h1",
                    "property": "enthalpy_flow",
                    "normalized_value": -100.0,
                    "normalized_unit": "kW",
                    "status": "verified",
                    "sheet": "Balance",
                    "cell": "A3",
                },
                {
                    "id": "h2",
                    "property": "enthalpy_flow",
                    "normalized_value": -90.0,
                    "normalized_unit": "kW",
                    "status": "verified",
                    "sheet": "Balance",
                    "cell": "A4",
                },
            ],
        },
    ]
}


def run(method, quantity, target, inputs=None, **extra):
    contract = ({"id": "test"}, {"quantity": quantity}, target)
    with patch(
        "backend.equipment_costing.unit_conversion.bridges.service.model_contract",
        return_value=contract,
    ):
        return evaluate(
            REPORT,
            "e",
            {
                "model_id": "test",
                "method": method,
                "measurement_id": "m",
                "inputs": inputs or {},
                **extra,
            },
        )


def test_direct_flow_preserves_source_and_trace():
    before = copy.deepcopy(REPORT)
    r = run("direct", "mass_flow", "lb/h")
    assert r["size"] == pytest.approx(2204.62262185)
    assert r["source_measurements"][0]["cell"] == "A1"
    assert REPORT == before


def test_liquid_and_vessel_volume_require_user_density_and_residence():
    with pytest.raises(ValueError):
        run("liquid_flow", "volume_flow", "m3/h")
    assert (
        run("liquid_flow", "volume_flow", "m3/h", {"density_kg_m3": 1000})["size"] == 1
    )
    r = run(
        "vessel_volume",
        "volume",
        "1000 gal",
        {"density_kg_m3": 1000, "residence_time_h": 2, "working_fraction": 0.8},
        unit_context={"target_gallon_basis": "US"},
    )
    assert r["size"] == pytest.approx(0.6604301309)
    with pytest.raises(ValueError):
        run(
            "vessel_volume",
            "volume",
            "m3",
            {"density_kg_m3": 1000, "residence_time_h": 2, "working_fraction": 2},
        )


def test_pump_coordinate_and_power():
    inputs = {"density_kg_m3": 1000, "differential_pressure_bar": 2, "efficiency": 0.5}
    assert run("pump_power", "power", "kW", inputs)["size"] == pytest.approx(
        0.1111111111
    )
    assert (
        run(
            "pump_coordinate",
            "flow_pressure_product",
            "1000 gpm_psi",
            inputs,
            unit_context={"target_gallon_basis": "US"},
        )["size"]
        > 0
    )
    with pytest.raises(ValueError):
        run(
            "pump_power",
            "power",
            "kW",
            {"density_kg_m3": 1000, "differential_pressure_bar": 2},
        )


def test_gas_molar_and_dryer_routes():
    inputs = {
        "temperature_k": 300,
        "absolute_pressure_bar": 1,
        "compressibility_z": 1,
        "gas_residence_time_s": 10,
    }
    q = run("gas_flow", "volume_flow", "m3/h", inputs, measurement_id="n")["size"]
    assert q == pytest.approx(24.9433878545)
    assert run("dryer_volume", "volume", "m3", inputs, measurement_id="n")[
        "size"
    ] == pytest.approx(q * 10 / 3600)
    with pytest.raises(ValueError):
        run("gas_flow", "volume_flow", "m3/h", inputs)  # MW absent for mass flow


def test_heat_area_uses_difference_and_confirmation():
    inputs = {"overall_u_w_m2_k": 500, "lmtd_k": 20, "lmtd_correction": 1}
    kw = {
        "measurement_id": "h1",
        "outlet_measurement_id": "h2",
        "same_side_reference_confirmed": True,
    }
    assert run("exchanger_area", "area", "m2", inputs, **kw)["size"] == pytest.approx(1)
    with pytest.raises(ValueError):
        run("exchanger_area", "area", "m2", inputs, measurement_id="h1")


def test_filter_mixing_and_vessel_mass():
    assert (
        run(
            "filter_area",
            "area",
            "m2",
            {"density_kg_m3": 1000, "hydraulic_loading_m_h": 2},
        )["size"]
        == 0.5
    )
    assert (
        run(
            "mixing_power",
            "power",
            "kW",
            {
                "density_kg_m3": 1000,
                "residence_time_h": 2,
                "working_fraction": 0.8,
                "power_density_kw_m3": 1,
            },
        )["size"]
        == 2.5
    )
    assert (
        run(
            "vessel_mass",
            "mass",
            "kg",
            {
                "inside_diameter_m": 1,
                "wall_thickness_m": 0.01,
                "straight_length_m": 2,
                "material_density_kg_m3": 7850,
                "heads_and_auxiliaries_kg": 100,
            },
        )["size"]
        > 100
    )


def test_no_unlinked_source_or_wrong_output_dimension():
    with pytest.raises(ValueError):
        run("direct", "mass_flow", "kg/h", measurement_id="not-linked")
    with pytest.raises(ValueError):
        run("vessel_volume", "power", "kW")
    with pytest.raises(ValueError):
        run("direct", "mass_flow", "kg/h", {"density_kg_m3": float("nan")})


def test_unresolved_models_and_inputs_are_visible():
    with pytest.raises(ValueError):
        evaluate(REPORT, "e", {"model_id": "nonexistent"})
    context = describe(REPORT, "e", "G258-004")
    assert all(
        p["value"] is None and p["status"] == "user_input"
        for recipe in context["recipes"]
        for p in recipe["parameters"]
    )


def test_saved_equation_flows_into_canonical_equipment_calculation():
    from backend.blocks.equipment.calculation import calculate_equipment

    spec = {
        "enabled": True,
        "model_id": "G258-004",
        "method": "vessel_volume",
        "measurement_id": "m",
        "inputs": {
            "density_kg_m3": 1000,
            "residence_time_h": 2,
            "working_fraction": 0.8,
        },
        "unit_context": {"target_gallon_basis": "US"},
    }
    plan = {
        "equipment": [
            {"equipment_key": "e", "curve_id": "G258-004", "unit_conversion": spec}
        ]
    }
    _, rows = calculate_equipment(REPORT, plan)
    assert rows[0]["size"] == pytest.approx(660.430130895)
    assert rows[0]["size_unit"] == "US_gal"
    # Conversion resolves size; it does not bypass the costing model's own restrictions.
    plan["equipment"][0]["curve_id"] = "G258-005"
    _, rows = calculate_equipment(REPORT, plan)
    assert rows[0]["size"] is None


def test_standalone_enthalpy_is_not_equipment_power():
    with pytest.raises(ValueError, match="standalone stream enthalpy"):
        run("direct", "power", "kW", measurement_id="h1")
