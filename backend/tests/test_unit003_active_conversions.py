"""UNIT-003 independent reference, compatibility and native handoff tests."""

import copy
import csv
import json
import math
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from unittest.mock import patch
import numpy as np
import pytest
from backend.equipment_costing.unit_conversion import (
    convert,
    identify_unit,
    Measurement,
    ConversionContext,
)
from backend.equipment_costing.unit_conversion.unit_aliases import UNITS
from backend.equipment_costing.unit_conversion.sizing_parameters import (
    normalize_parameters,
)
from backend.equipment_costing.unit_conversion.relationships import (
    average_power,
    residence_time,
)
from backend.equipment_costing.unit_conversion.bridges import gas, liquid
from backend.equipment_costing.unit_conversion.bridges.service import evaluate
from backend.engineering_sizing.adapter import derive

ROOT = Path(__file__).resolve().parents[2]
REFS = json.loads(
    (Path(__file__).parent / "fixtures/unit003/conversions.json").read_text()
)
PRIOR = list(
    csv.DictReader(
        (
            ROOT
            / "docs/verification/phase1/units/catalogue_audit/canonical_unit_master_register.csv"
        ).open()
    )
)
ALIASES = list(
    csv.DictReader(
        (
            ROOT
            / "docs/verification/phase1/units/catalogue_audit/unit_alias_verification.csv"
        ).open(encoding="utf-8")
    )
)
UNITS_NEW = sorted({c["source"] for c in REFS})


@pytest.mark.parametrize("c", REFS, ids=lambda c: c["id"])
def test_independent_forward_reverse_roundtrip(c):
    r = convert(
        c["value"], c["source"], c["target"], source={"sheet": "Design", "cell": "B3"}
    )
    expected = float(c["expected"])
    assert r.status == "converted"
    assert r.value == pytest.approx(
        expected, rel=c["relative_tolerance"], abs=c["absolute_tolerance"]
    )
    assert r.original.source == {"sheet": "Design", "cell": "B3"}
    rev = convert(expected, c["target"], c["source"])
    assert rev.value == pytest.approx(
        c["value"], rel=c["relative_tolerance"], abs=1e-13
    )
    rt = convert(r.value, c["target"], c["source"])
    assert rt.value == pytest.approx(c["value"], rel=2e-12, abs=1e-13)


@pytest.mark.parametrize("unit", UNITS_NEW)
@pytest.mark.parametrize(
    "x",
    [float("nan"), float("inf"), -float("inf"), True, False, np.bool_(True), "1", None],
)
def test_new_families_reject_nonfinite_and_invalid_types(unit, x):
    assert convert(x, unit, unit).status == "unresolved"


@pytest.mark.parametrize("unit", UNITS_NEW)
def test_sign_and_invalid_units(unit):
    signed = identify_unit(unit).quantity == "velocity"
    r = convert(-1, unit, unit)
    assert (r.status == "converted") == signed
    if signed:
        assert r.value == -1
    assert convert(1, unit, "not_a_unit").status == "unresolved"


@pytest.mark.parametrize("a", ["m/s", "m/h", "ft/s", "ft/min"])
@pytest.mark.parametrize("b", ["m3/h", "m3/s", "s", "W/m2/K"])
def test_velocity_is_not_flow_time_or_u(a, b):
    assert convert(1, a, b).status == "unresolved"


@pytest.mark.parametrize("a", ["W/m2/K", "kW/m2/K", "Btu_IT/(h*ft2*delta_degF)"])
@pytest.mark.parametrize("b", ["W", "degF", "delta_degF", "m2", "m/h", "s"])
def test_u_is_a_separate_quantity(a, b):
    assert convert(1, a, b).status == "unresolved"


@pytest.mark.parametrize(
    "unit",
    [
        "seconds",
        "SECOND",
        "minutes",
        "hours",
        "days",
        " hr ",
        "m³/m²/h",
        "W/(m² K)",
        "W/(m^2*K)",
        "kW/(m2 K)",
        "Btu_IT/(h ft² °F)",
    ],
)
def test_active_spellings(unit):
    assert identify_unit(unit).quantity in {
        "time",
        "velocity",
        "heat_transfer_coefficient",
    }


def test_btu_ambiguity_and_interval_only():
    assert convert(1, "Btu/(h*ft2*°F)", "W/m2/K").status == "unresolved"
    r = convert(
        1, "Btu/(h*ft2*°F)", "W/m2/K", context=ConversionContext(btu_basis="IT")
    )
    assert r.value == pytest.approx(5.678263341113488, rel=2e-12)
    assert r.assumptions
    assert (
        convert(
            1, "Btu/(h*ft2*degF)", "W/m2/K", context=ConversionContext(btu_basis="IT")
        ).status
        == "unresolved"
    )
    assert convert(1, "w/m2/k", "W/m2/K").status == "unresolved"


@pytest.mark.parametrize("r", PRIOR, ids=lambda r: r["canonical_identifier"])
def test_prior_definitions_unchanged(r):
    d = UNITS[r["canonical_identifier"]]
    assert d.symbol == r["display_symbol"] and d.quantity == r["physical_quantity"]
    assert d.factor == float(r["production_multiplier"])
    assert d.offset == float(r["production_offset"])
    assert d.pressure_basis == (r["pressure_basis"] or None)


@pytest.mark.parametrize("r", ALIASES, ids=lambda r: r["namespace"] + "-" + r["alias"])
def test_prior_alias_bindings_unchanged(r):
    assert identify_unit(r["alias"]).symbol == r["independent_intended_target"]


def report(prop="volume_flow", value=10, unit="m3/h"):
    return {
        "entities": [
            {
                "key": "e",
                "kind": "equipment",
                "identifier": "E-1",
                "stream_keys": ["s"],
                "values": [],
            },
            {
                "key": "s",
                "kind": "material",
                "identifier": "S-1",
                "values": [
                    {
                        "id": "Balance!D7",
                        "property": prop,
                        "normalized_value": value,
                        "normalized_unit": unit,
                        "status": "verified",
                        "sheet": "Balance",
                        "cell": "D7",
                    }
                ],
            },
        ]
    }


@pytest.mark.parametrize(
    "method,params,expected,prop,value,unit",
    [
        (
            "filter_area",
            {"hydraulic_loading_m_h": {"value": 0.001, "unit": "m/s"}},
            10 / 3.6,
            "volume_flow",
            10,
            "m3/h",
        ),
        (
            "exchanger_area",
            {
                "overall_u_w_m2_k": {"value": 0.5, "unit": "kW/m2/K"},
                "lmtd_k": 20,
                "lmtd_correction": 1,
            },
            10,
            "heat_duty",
            100,
            "kW",
        ),
        (
            "vaporizer_area",
            {
                "overall_u_w_m2_k": {"value": 0.5, "unit": "kW/m2/K"},
                "lmtd_k": 20,
                "lmtd_correction": 1,
            },
            10,
            "heat_duty",
            100,
            "kW",
        ),
        (
            "vessel_hold_up",
            {"residence_time_h": {"value": 30, "unit": "min"}, "working_fraction": 0.8},
            6.25,
            "volume_flow",
            10,
            "m3/h",
        ),
        (
            "ion_exchange_ebct",
            {
                "empty_bed_contact_time_min": {"value": 0.5, "unit": "h"},
                "resin_bed_fraction": 0.5,
            },
            10,
            "volume_flow",
            10,
            "m3/h",
        ),
        (
            "ion_exchange_capacity",
            {
                "service_cycle_h": {"value": 480, "unit": "min"},
                "ionic_load_mol_equiv_m3": 2,
                "working_resin_capacity_mol_equiv_m3": 1000,
                "resin_bed_fraction": 0.5,
            },
            0.32,
            "volume_flow",
            10,
            "m3/h",
        ),
        (
            "dryer_chamber",
            {"gas_residence_time_s": {"value": 1, "unit": "min"}},
            1 / 6,
            "volume_flow",
            10,
            "m3/h",
        ),
    ],
)
def test_normalization_then_native_sizing(method, params, expected, prop, value, unit):
    source = report(prop, value, unit)
    spec = {"method": method, "stream_key": "s", "parameters": params}
    before = copy.deepcopy(spec)
    result = derive(spec, source)
    assert result[0] == pytest.approx(expected, rel=2e-12)
    assert result[2]["parameter_unit_conversions"]
    assert result[2]["source_evidence"] == ["Balance!D7"]
    assert result[2]["assumptions"] == before and spec == before


def test_range_endpoints_preserved_and_normalized():
    params = {
        "residence_time_h": {
            "value": 30,
            "low": 15,
            "high": 60,
            "unit": "min",
            "source": {"cell": "C7"},
        },
        "working_fraction": 1,
    }
    spec = {"method": "vessel_hold_up", "stream_key": "s", "parameters": params}
    before = copy.deepcopy(spec)
    result = derive(spec, report())
    assert result[0] == 5
    assert (
        result[2]["size_range"]["low"] == 2.5 and result[2]["size_range"]["high"] == 10
    )
    assert len(result[2]["parameter_unit_conversions"]) == 3
    assert spec == before
    assert all(
        c["conversion"]["original"]["source"] == {"cell": "C7"}
        for c in result[2]["parameter_unit_conversions"]
    )


@pytest.mark.parametrize("field", ["value", "low", "high"])
@pytest.mark.parametrize("value", [True, np.bool_(False), float("nan"), float("inf")])
def test_bad_typed_assumptions_rejected(field, value):
    record = {"value": 30, "low": 10, "high": 60, "unit": "min", field: value}
    with pytest.raises(ValueError):
        derive(
            {
                "method": "vessel_hold_up",
                "stream_key": "s",
                "parameters": {"residence_time_h": record, "working_fraction": 1},
            },
            report(),
        )


@pytest.mark.parametrize("unit", ["m3/h", "kg/h", "degC", "s"])
def test_wrong_loading_dimension_rejected(unit):
    with pytest.raises(ValueError):
        normalize_parameters({"hydraulic_loading_m_h": {"value": 1, "unit": unit}})


@pytest.mark.parametrize(
    "factory", [Decimal, Fraction, np.int64, np.float32, np.float64]
)
def test_native_typed_numeric_representations_preserved(factory):
    result = derive(
        {
            "method": "vessel_hold_up",
            "stream_key": "s",
            "parameters": {
                "residence_time_h": {"value": factory(1), "unit": "h"},
                "working_fraction": 1,
            },
        },
        report(),
    )
    assert result[0] == 10


def cv(value, unit, target=None):
    if value == "quantity":
        return identify_unit(unit).quantity
    r = convert(value, unit, target)
    if r.value is None:
        raise ValueError("; ".join(r.issues))
    return r.value


def test_contextual_power_and_residence_are_explicit_and_traceable():
    e = Measurement(4, "kWh", {"cell": "E4"})
    t = Measurement(30, "min", {"cell": "T4"})
    r = average_power(e, t)
    assert r.value == 8 and r.unit == "kW"
    assert r.source["inputs"][0]["original"]["source"] == {"cell": "E4"}
    assert average_power(Measurement(-4, "kWh"), t).value == -8
    r = residence_time(
        Measurement(1000, "L", {"cell": "V4"}),
        Measurement(2, "m3/h"),
        target_unit="min",
    )
    assert r.value == 30 and r.source["inputs"][0]["original"]["source"] == {
        "cell": "V4"
    }
    assert convert(4, "kWh", "kW").status == "unresolved"
    assert convert(1, "m3", "h").status == "unresolved"


@pytest.mark.parametrize("x", [0, -1, True, float("nan"), float("inf"), None])
def test_duration_and_flow_denominators_required(x):
    with pytest.raises(ValueError):
        average_power(Measurement(1, "J"), Measurement(x, "s"))
    with pytest.raises(ValueError):
        residence_time(Measurement(1, "m3"), Measurement(x, "m3/h"))


def test_context_wrong_dimensions_and_missing_inputs():
    for f, args in [
        (average_power, (Measurement(1, "kW"), Measurement(1, "s"))),
        (residence_time, (Measurement(1, "m3"), Measurement(1, "kg/h"))),
        (average_power, (Measurement(1, "J"), None)),
        (residence_time, (Measurement(1, "m3"), Measurement(1, "scfm"))),
    ]:
        with pytest.raises(ValueError):
            f(*args)
    with pytest.raises(ValueError):
        average_power(Measurement(1e308, "J"), Measurement(1e-308, "s"))


@pytest.mark.parametrize("density", [None, 0, -1, True, float("nan"), float("inf")])
def test_mass_volume_requires_qualified_numeric_density(density):
    with pytest.raises(ValueError):
        liquid.evaluate("liquid_flow", 2, "kg/s", {"density_kg_m3": density}, cv)


def test_no_water_density_assumption():
    assert liquid.evaluate("liquid_flow", 2, "kg/s", {"density_kg_m3": 800}, cv)[0] == 9
    assert convert(2, "kg/s", "m3/h").status == "unresolved"


@pytest.mark.parametrize(
    "key",
    [
        "temperature_k",
        "absolute_pressure_bar",
        "compressibility_z",
        "reference_temperature_k",
        "reference_pressure_bar",
        "reference_compressibility_z",
    ],
)
@pytest.mark.parametrize("x", [None, 0, -1, True, float("nan"), float("inf")])
def test_gas_reference_inputs_explicit_and_valid(key, x):
    p = {
        "temperature_k": 300,
        "absolute_pressure_bar": 1,
        "compressibility_z": 1,
        "reference_temperature_k": 300,
        "reference_pressure_bar": 2,
        "reference_compressibility_z": 1,
        key: x,
    }
    with pytest.raises(ValueError):
        gas.evaluate("standard_gas_flow", 100, "m3/h", p, cv)


def test_gas_references_and_pressure_roles():
    p = {
        "temperature_k": 300,
        "absolute_pressure_bar": 1,
        "compressibility_z": 1,
        "reference_temperature_k": 300,
        "reference_pressure_bar": 2,
        "reference_compressibility_z": 1,
    }
    assert gas.evaluate("standard_gas_flow", 100, "m3/h", p, cv)[0] == pytest.approx(50)
    assert convert(1, "cfm", "scfm").status == "unresolved"
    assert convert(1, "scfm", "Nm3/h").status == "unresolved"
    assert (
        convert(
            1,
            "scfm",
            "Nm3/h",
            context=ConversionContext(
                input_gas_reference="A", target_gas_reference="B"
            ),
        ).status
        == "unresolved"
    )
    assert convert(1, "bar", "bara").status == "unresolved"
    assert convert(1, "barg", "bara").status == "unresolved"
    assert convert(
        1, "barg", "bara", context=ConversionContext(atmospheric_pressure_pa=101325)
    ).value == pytest.approx(2.01325)
    assert (
        convert(
            -2,
            "barg",
            "bara",
            context=ConversionContext(atmospheric_pressure_pa=101325),
        ).status
        == "unresolved"
    )
    assert convert(1, "bara", "Pa").pressure_basis == "absolute"


def test_bridge_uses_same_parameter_normalizer_and_costing_receives_area():
    # Actual existing model; no synthetic price/model or changed equation.
    from backend.equipment_costing.registry import (
        list_equipment_models,
        estimate_from_parsed_inputs,
    )

    models = list_equipment_models("openpytea")
    model = next(
        m
        for m in models
        if m["category"] == "Filters"
        and m["input_requirements"][0]["quantity"] == "area"
        and m["status"] != "disabled"
    )
    spec = {
        "model_id": model["id"],
        "method": "filter_area",
        "measurement_id": "Balance!D7",
        "inputs": {
            "hydraulic_loading_m_h": {
                "value": 0.001,
                "unit": "m/s",
                "source": {"cell": "C8"},
            }
        },
    }
    before = copy.deepcopy(spec)
    preview = evaluate(report(), "e", spec)
    target = model["input_requirements"][0]["unit"]
    expected = 10 / 3.6
    assert preview["intermediate"]["value"] == pytest.approx(expected)
    assert preview["parameter_unit_conversions"][0]["conversion"]["original"][
        "source"
    ] == {"cell": "C8"}
    priced = estimate_from_parsed_inputs(
        model["id"],
        {
            "size": Measurement(
                preview["size"],
                preview["size_unit"],
                {"unit003": preview["parameter_unit_conversions"]},
            )
        },
        allow_unverified=True,
    )
    native = estimate_from_parsed_inputs(
        model["id"], {"size": Measurement(expected, "m2")}, allow_unverified=True
    )
    assert priced.estimate.amount == pytest.approx(native.estimate.amount)
    assert spec == before
    assert preview["original_user_inputs"] == before["inputs"]


def test_optional_and_unresolved_coordinates_still_guarded():
    assert convert(1, "cP", "Pa*s").status == "unresolved"
    assert convert(1, "specific_gravity", "kg/m3").status == "unresolved"
    assert convert(1, "boiler_hp", "W").status == "unresolved"
    from backend.equipment_costing.registry import (
        list_equipment_models,
        resolve_equipment_inputs,
    )
    from backend.equipment_costing.indexes.openpytea.adapter import native_input

    blocked = list(
        csv.DictReader(
            (
                ROOT
                / "docs/verification/phase1/units/catalogue_audit/costing_unit_dependency_matrix.csv"
            ).open()
        )
    )
    by = {m["id"]: m for m in list_equipment_models("all")}
    for row in blocked:
        if row["unit_interface_status"] != "BLOCKED":
            continue
        m = by[row["model_id"]]
        if row["source"] == "garrett":
            result = resolve_equipment_inputs(m["id"], {"size": Measurement(1, "kg/h")})
            assert result.status != "resolved"
        else:
            with pytest.raises(ValueError):
                native_input(1, "m3", m["input_requirements"][0])


@pytest.mark.parametrize(
    "value", [True, float("nan"), float("inf"), -float("inf"), None]
)
def test_physical_relationship_numerators_reject_invalid_values(value):
    with pytest.raises(ValueError):
        average_power(Measurement(value, "J"), Measurement(1, "s"))
    with pytest.raises(ValueError):
        residence_time(Measurement(value, "m3"), Measurement(1, "m3/h"))


def test_physical_zero_and_output_dimension_constraints():
    assert average_power(Measurement(0, "J"), Measurement(1, "s")).value == 0
    assert residence_time(Measurement(0, "m3"), Measurement(1, "m3/h")).value == 0
    with pytest.raises(ValueError):
        average_power(Measurement(1, "J"), Measurement(1, "s"), target_unit="J")
    with pytest.raises(ValueError):
        residence_time(Measurement(1, "m3"), Measurement(1, "m3/h"), target_unit="m3")


def test_typed_conversion_requires_a_selected_value_and_unit():
    for record in [{"unit": "min"}, {"value": 30}, {"value": 30, "unit": "nonsense"}]:
        with pytest.raises(ValueError):
            normalize_parameters({"residence_time_h": record})


NEW_ALIAS_MEANINGS = {
    "m/s": "m/s",
    "m/h": "m/h",
    "ft/s": "ft/s",
    "ft/min": "ft/min",
    "m3/m2/h": "m/h",
    "s": "s",
    "min": "min",
    "h": "h",
    "day": "day",
    "W/m2/K": "W/m2/K",
    "W/(m2 K)": "W/m2/K",
    "W/(m2*K)": "W/m2/K",
    "W/(m2*delta_K)": "W/m2/K",
    "kW/m2/K": "kW/m2/K",
    "kW/(m2 K)": "kW/m2/K",
    "kW/(m2*K)": "kW/m2/K",
    "Btu_IT/(h*ft2*delta_degF)": "Btu_IT/(h*ft2*delta_degF)",
    "Btu_IT/(h ft2 °F)": "Btu_IT/(h*ft2*delta_degF)",
    "Btu_IT/(h*ft2*°F)": "Btu_IT/(h*ft2*delta_degF)",
    "Btu_th/(h*ft2*delta_degF)": "Btu_th/(h*ft2*delta_degF)",
    "Btu_th/(h ft2 °F)": "Btu_th/(h*ft2*delta_degF)",
    "Btu_th/(h*ft2*°F)": "Btu_th/(h*ft2*delta_degF)",
    "sec": "s",
    "second": "s",
    "seconds": "s",
    "minute": "min",
    "minutes": "min",
    "hr": "h",
    "hour": "h",
    "hours": "h",
    "d": "day",
    "days": "day",
}


@pytest.mark.parametrize("alias,canonical", NEW_ALIAS_MEANINGS.items())
def test_every_new_alias_has_explicit_semantics(alias, canonical):
    assert identify_unit(alias).symbol == canonical
    assert convert(1, alias, canonical).value == 1
