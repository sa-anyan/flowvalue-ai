"""M1.6 (roadmap finding #11): independent reference cases for bridge equations.

Each expected value is calculated by hand from the textbook relationship in the
comment, not by calling FlowValue code. LMTD/duty countercurrent cases and the
gas bridges already have reference tests (test_heat_exchanger_basis.py,
test_standard_gas_flow_bridge.py, test_gas_compression_bridge.py); this file
adds the cases that had none.
"""

import math

import pytest

from backend.equipment_costing.unit_conversion import convert as _convert
from backend.equipment_costing.unit_conversion.bridges import drying, liquid
from backend.equipment_costing.unit_conversion.bridges.heat_exchanger import signed_enthalpy_duty
from backend.tests.test_heat_exchanger_basis import fixture, run

QUANTITY = {"m3/h": "volume_flow", "kg/h": "mass_flow"}


def conv(*args):
    if args[0] == "quantity":
        return QUANTITY[args[1]]
    value, unit, target = args
    return _convert(value, unit, target).value


# --- Heat exchanger ---------------------------------------------------------

def test_lmtd_parallel_flow_reference():
    # Parallel flow: dT1 = Th,in - Tc,in = 150 - 20 = 130 K; dT2 = Th,out - Tc,out = 100 - 60 = 40 K
    # LMTD = (130 - 40) / ln(130/40) = 90 / 1.178655 = 76.3582 K (Incropera, Fundamentals of Heat and Mass Transfer, eq. 11.15)
    obs, basis, inputs = fixture()
    basis["flow_arrangement"] = "parallel"
    area, unit, details = run(obs, basis, inputs)
    lmtd = 90 / math.log(130 / 40)
    assert lmtd == pytest.approx(76.3582, abs=1e-4)
    # Q = 40 kW (hot side 100 -> 60 kW enthalpy flow); A = Q / (U * LMTD) = 40000 / (500 * 76.3582) = 1.04769 m2
    assert unit == "m2" and area == pytest.approx(40000 / (500 * lmtd), rel=1e-12)
    assert area == pytest.approx(1.04769, abs=1e-5)


def test_parallel_flow_with_outlet_temperature_cross_is_rejected():
    # Parallel flow cannot heat the cold stream above the hot outlet: Tc,out 110 > Th,out 100
    obs, basis, inputs = fixture()
    basis["flow_arrangement"] = "parallel"
    next(o for o in obs if o["id"] == "cold_outlettemperature")["value"] = 110
    with pytest.raises(ValueError, match="no positive LMTD"):
        run(obs, basis, inputs)


def test_enthalpy_duty_sign_convention():
    # Hot side releases (inlet - outlet); cold side absorbs (outlet - inlet). No absolute value.
    assert signed_enthalpy_duty(100, 60, "hot") == 40
    assert signed_enthalpy_duty(10, 50, "cold") == 40
    assert signed_enthalpy_duty(60, 100, "hot") == -40  # wrong direction stays negative, never abs()
    with pytest.raises(ValueError):
        signed_enthalpy_duty(float("nan"), 1, "hot")


# --- Pump head (S = Q * sqrt(H)) --------------------------------------------

def test_pump_size_from_differential_pressure_reference():
    # H = dP / (rho * g) = 2 bar * 1e5 Pa/bar / (1000 kg/m3 * 9.80665 m/s2) = 20.3943 m
    # S = Q * sqrt(H) = 36 m3/h * 4.516008 = 162.5763 m3/h*m^0.5
    size, unit, details = liquid.evaluate(
        "pump_flow_head", 36, "m3/h", {"differential_pressure_bar": 2, "density_kg_m3": 1000}, conv)
    assert details["head_m"] == pytest.approx(20.3943, abs=1e-4)
    assert size == pytest.approx(162.5763, abs=1e-4) and unit == "m3/h_sqrt_m"


def test_pump_size_from_mass_flow_and_supplied_head():
    # Q = 36000 kg/h / 1200 kg/m3 = 30 m3/h; S = 30 * sqrt(25) = 150
    size, _, details = liquid.evaluate("pump_flow_head", 36000, "kg/h", {"head_m": 25, "density_kg_m3": 1200}, conv)
    assert details["volumetric_flow_m3_h"] == pytest.approx(30)
    assert size == pytest.approx(150)


@pytest.mark.parametrize("inputs", [
    {"differential_pressure_bar": 0, "density_kg_m3": 1000},
    {"differential_pressure_bar": -1, "density_kg_m3": 1000},
    {"differential_pressure_bar": 2},  # no density: never defaulted
    {"head_m": float("inf")},
])
def test_pump_head_rejects_missing_or_non_physical_inputs(inputs):
    with pytest.raises(ValueError):
        liquid.evaluate("pump_flow_head", 36, "m3/h", inputs, conv)


# --- Dryer water removal ------------------------------------------------------

def _water(key, value, unit="kg/h", prop="component_mass_flow", component="Water"):
    return {"entity_key": key, "property": prop, "component": component, "value": value, "unit": unit}


def test_dryer_net_water_removal_reference():
    # Evaporation = feed water - product water = 500 - 20 = 480 kg/h
    value, unit, details = drying.water_evaporation(_water("feed", 500), _water("product", 20), conv)
    assert (value, unit) == (480, "kg/h")
    # Unit conversion: 500/3600 kg/s feed water = 500 kg/h
    value, _, _ = drying.water_evaporation(_water("feed", 500 / 3600, unit="kg/s"), _water("product", 20), conv)
    assert value == pytest.approx(480)
    assert "not an independently verified" in details["assumption"].lower()


@pytest.mark.parametrize("feed,product,message", [
    (_water("feed", 20), _water("product", 500), "no positive net water removal"),
    (_water("feed", 500), _water("feed", 20), "different streams"),
    (_water("feed", 500, prop="mass_flow"), _water("product", 20), "water component"),
    (_water("feed", 500, component="Protein"), _water("product", 20), "water component"),
    (_water("feed", -5), _water("product", 0), "non-negative"),
])
def test_dryer_rejects_wrong_boundary_or_basis(feed, product, message):
    with pytest.raises(ValueError, match=message):
        drying.water_evaporation(feed, product, conv)
