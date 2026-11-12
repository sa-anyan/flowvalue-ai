"""M1.6: independent reference cases for equations inside the unit-conversion bridges.

These bridges feed equipment costing directly, so each equation is treated as a
calculation method with an independent reference and an applicability limit
(docs/verification/phase1/bridge_methods/bridge_method_register.csv).

Expected values are written from the governing textbook equations and were
evaluated separately with 40-digit decimal arithmetic; they are not outputs of
the production functions. Tolerances cover binary floating point only.

    LMTD           = (dT1 - dT2) / ln(dT1 / dT2)
                     countercurrent: dT1 = Th,in - Tc,out, dT2 = Th,out - Tc,in
                     parallel:       dT1 = Th,in - Tc,in,  dT2 = Th,out - Tc,out
    Enthalpy duty  = H_in - H_out (hot side), H_out - H_in (cold side)
    Pump head      = dP / (rho * g), g = 9.80665 m/s2 (standard gravity)
    Pump coordinate S = Q * sqrt(H)
    Standard gas   = Q_actual * (P / P_ref) * (T_ref / T) * (Z_ref / Z)
    From mass      = (m / MW) * R * T_ref * Z_ref / P_ref
    Drying load    = feed water - product water (selected boundary)
"""

import math

import pytest

from backend.equipment_costing.unit_conversion import convert, identify_unit
from backend.equipment_costing.unit_conversion.bridges import drying, gas, liquid
from backend.equipment_costing.unit_conversion.bridges.heat_exchanger import (
    calculate_basis,
    signed_enthalpy_duty,
)

FLOAT = dict(rel=1e-12, abs=0)


def cv(value, unit, target=None):
    if value == "quantity":
        return identify_unit(unit).quantity
    result = convert(value, unit, target)
    if result.value is None:
        raise ValueError("; ".join(result.issues))
    return result.value


# ---------------------------------------------------------------- LMTD and duty

def thermal_case(arrangement):
    observations = []
    for role, t_c, h_kw in [
        ("hot_inlet", 150, 100),
        ("hot_outlet", 100, 60),
        ("cold_inlet", 20, 10),
        ("cold_outlet", 60, 50),
    ]:
        for prop, value, unit in [
            ("temperature", t_c, "degC"),
            ("enthalpy_flow", h_kw, "kW"),
            ("mass_flow", 3600, "kg/h"),
        ]:
            observations.append(
                dict(id=role + prop, entity_key=role, property=prop, value=value,
                     unit=unit, sheet="Ref", cell="A1")
            )
    basis = {r + "_stream_key": r for r in ("hot_inlet", "hot_outlet", "cold_inlet", "cold_outlet")}
    basis.update(
        duty_side="hot", duty_method="enthalpy_difference", flow_arrangement=arrangement,
        phase_change="none", duty_conflict_policy="provisional_selected_side",
        common_enthalpy_reference_confirmed=True, steady_state_mass_flow_assumed=False,
        rationale="M1.6 reference", limitations="Preliminary",
    )
    inputs = dict(overall_u_w_m2_k=500, lmtd_correction=1)
    return calculate_basis(observations, [], basis, inputs, lambda v, u, t: convert(v, u, t).value)


def test_lmtd_countercurrent_reference():
    # dT1 = 150 - 60 = 90 K, dT2 = 100 - 20 = 80 K -> 84.90187015703761725... K
    area, unit, details = thermal_case("countercurrent")
    assert details["resolved_inputs"]["lmtd_k"] == pytest.approx(84.90187015703761725, **FLOAT)
    # A = Q / (U * LMTD) = 40 000 W / (500 W/m2/K * LMTD)
    assert (area, unit) == (pytest.approx(40000 / (500 * 84.90187015703761725), **FLOAT), "m2")


def test_lmtd_parallel_reference():
    # dT1 = 150 - 20 = 130 K, dT2 = 100 - 60 = 40 K -> 76.35822210854355034... K
    area, unit, details = thermal_case("parallel")
    assert details["resolved_inputs"]["lmtd_k"] == pytest.approx(76.35822210854355034, **FLOAT)
    assert area == pytest.approx(1.0476933300814632153, **FLOAT)


def test_parallel_needs_more_area_than_countercurrent_for_same_duty():
    # Physical check: countercurrent always has the larger mean driving force.
    assert thermal_case("parallel")[0] > thermal_case("countercurrent")[0]


def test_enthalpy_duty_sign_convention():
    # Hot side releases H_in - H_out; cold side absorbs H_out - H_in.
    assert signed_enthalpy_duty(100.0, 60.0, "hot") == 40.0
    assert signed_enthalpy_duty(10.0, 50.0, "cold") == 40.0
    # A wrong-direction stream stays negative; it is not silently absoluted.
    assert signed_enthalpy_duty(60.0, 100.0, "hot") == -40.0
    for bad in (True, math.nan, math.inf):
        with pytest.raises(ValueError):
            signed_enthalpy_duty(bad, 1.0, "hot")
    with pytest.raises(ValueError):
        signed_enthalpy_duty(1.0, 2.0, "neither")


# ---------------------------------------------------------------- pump head

def test_pump_head_from_pressure_reference():
    # H = 200 000 Pa / (1000 kg/m3 * 9.80665 m/s2) = 20.39432425955856485 m
    # S = 36 m3/h * sqrt(H) = 162.5762720706435071
    s, unit, details = liquid.evaluate(
        "pump_flow_head", 36, "m3/h",
        {"differential_pressure_bar": 2, "density_kg_m3": 1000}, cv,
    )
    assert details["head_m"] == pytest.approx(20.39432425955856485, **FLOAT)
    assert (s, unit) == (pytest.approx(162.5762720706435071, **FLOAT), "m3/h_sqrt_m")


def test_pump_head_supplied_directly_and_mass_flow_basis():
    # 36 000 kg/h at 1000 kg/m3 = 36 m3/h; supplied head 25 m -> S = 36 * 5 = 180
    s, _, details = liquid.evaluate(
        "pump_flow_head", 36000, "kg/h", {"head_m": 25, "density_kg_m3": 1000}, cv
    )
    assert s == pytest.approx(180.0, **FLOAT)
    assert details["volumetric_flow_m3_h"] == pytest.approx(36.0, **FLOAT)


@pytest.mark.parametrize("inputs", [
    {"differential_pressure_bar": -1, "density_kg_m3": 1000},
    {"differential_pressure_bar": 2, "density_kg_m3": 0},
    {"head_m": 0},
])
def test_pump_head_rejects_non_physical_inputs(inputs):
    with pytest.raises(ValueError):
        liquid.evaluate("pump_flow_head", 36, "m3/h", inputs, cv)


# ---------------------------------------------------------------- standard gas flow

STATE = dict(absolute_pressure_bar=5, temperature_k=313.15, compressibility_z=1,
             reference_temperature_k=273.15, reference_pressure_bar=1.01325,
             reference_compressibility_z=1)


def test_standard_gas_flow_from_actual_volume_ideal():
    # 100 * (5 / 1.01325) * (273.15 / 313.15) = 430.4296508118775419 Sm3/h
    q, unit, details = gas.evaluate("standard_gas_flow", 100, "m3/h", dict(STATE), cv)
    assert (q, unit) == (pytest.approx(430.4296508118775419, **FLOAT), "Sm3/h")
    assert details["reference_temperature_k"] == 273.15


def test_standard_gas_flow_non_ideal_inlet():
    # Z = 0.95 at the inlet: multiply the ideal result by Z_ref / Z = 1 / 0.95
    q, _, _ = gas.evaluate(
        "standard_gas_flow", 100, "m3/h", dict(STATE, compressibility_z=0.95), cv
    )
    assert q == pytest.approx(453.0838429598710968, **FLOAT)


def test_standard_gas_flow_from_mass():
    # 1000 kg/h N2 / 28.0134 kg/kmol * R * 273.15 K / (1.01325 bar * 100) = 800.1159996649509783
    q, unit, _ = gas.evaluate(
        "standard_gas_flow", 1000, "kg/h", dict(STATE, molecular_weight_kg_kmol=28.0134), cv
    )
    assert (q, unit) == (pytest.approx(800.1159996649509783, **FLOAT), "Sm3/h")


@pytest.mark.parametrize("missing", ["reference_temperature_k", "reference_pressure_bar", "absolute_pressure_bar"])
def test_standard_gas_flow_requires_explicit_states(missing):
    inputs = {k: v for k, v in STATE.items() if k != missing}
    with pytest.raises(ValueError):
        gas.evaluate("standard_gas_flow", 100, "m3/h", inputs, cv)


# ---------------------------------------------------------------- drying load

def water(key, value, unit="kg/h", component="Water", prop="component_mass_flow"):
    return dict(entity_key=key, property=prop, component=component, value=value, unit=unit)


def test_drying_net_water_removal_reference():
    # 1000 kg/h water in the feed, 50 kg/h in the product -> 950 kg/h removed
    load, unit, details = drying.water_evaporation(water("f", 1000), water("p", 50), cv)
    assert (load, unit) == (950.0, "kg/h")
    assert details["feed_water_kg_h"] == 1000.0


def test_drying_converts_units_before_subtracting():
    # 0.3 kg/s feed water = 1080 kg/h; 80 kg/h product water -> 1000 kg/h
    load, _, _ = drying.water_evaporation(water("f", 0.3, "kg/s"), water("p", 80), cv)
    assert load == pytest.approx(1000.0, **FLOAT)
    # "t/h" is refused as an ambiguous ton (metric, short or long), not guessed.
    with pytest.raises(ValueError, match="Ambiguous ton"):
        drying.water_evaporation(water("f", 1.2, "t/h"), water("p", 200), cv)


@pytest.mark.parametrize("feed, product", [
    (water("f", 50), water("p", 1000)),            # product wetter than feed
    (water("f", 1000), water("f", 50)),            # same stream twice
    (water("f", 1000, prop="mass_flow"), water("p", 50)),  # total wet flow, not water
    (water("f", 1000, component="Ethanol"), water("p", 50)),
])
def test_drying_rejects_invalid_boundaries(feed, product):
    with pytest.raises(ValueError):
        drying.water_evaporation(feed, product, cv)
