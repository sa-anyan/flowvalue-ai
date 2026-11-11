"""UNIT-C01 native type boundaries; independent existing physical references."""

import copy
import json
from pathlib import Path
from decimal import Decimal
from fractions import Fraction
from types import SimpleNamespace

import numpy as np
import pytest

from backend.engineering_sizing.common import positive, reject_boolean
from backend.engineering_sizing.registry import METHODS, calculate
from backend.engineering_sizing.adapter import observation, derive
from backend.engineering_sizing.heat_exchangers import validate_heat_duty_type

REFS = json.loads(
    (Path(__file__).parent / "fixtures/sizing_verification/references.json").read_text()
)


class BooleanScalar:
    dtype = SimpleNamespace(kind="b")

    def __float__(self):
        raise AssertionError("Boolean was coerced before validation")

    def __abs__(self):
        raise AssertionError("Boolean magnitude was taken before validation")


BOOLS = [True, False, np.bool_(True), np.bool_(False), BooleanScalar()]
FACTORIES = [int, float, Decimal, Fraction, np.int64, np.float32, np.float64]


@pytest.mark.parametrize("value", BOOLS)
def test_shared_guard_before_coercion(value):
    with pytest.raises(ValueError, match="cannot be boolean"):
        positive(value, "test quantity")
    with pytest.raises(ValueError, match="cannot be boolean"):
        positive(value, "test quantity", zero=True)
    with pytest.raises(ValueError, match="cannot be boolean"):
        validate_heat_duty_type(value)


@pytest.mark.parametrize("factory", FACTORIES, ids=lambda f: f.__name__)
def test_valid_zero_and_one_are_not_filtered(factory):
    assert positive(factory(1), "test") == 1
    assert positive(factory(0), "test", zero=True) == 0


@pytest.mark.parametrize("r", REFS, ids=lambda r: r["method"])
@pytest.mark.parametrize("value", BOOLS)
def test_every_native_main_input_rejects_boolean(r, value):
    with pytest.raises(ValueError, match="cannot be boolean"):
        calculate(r["method"], value, r["parameters"])


PARAMS = [(r, key) for r in REFS for key in r["parameters"]]


@pytest.mark.parametrize(
    "r,key", PARAMS, ids=[r["method"] + "-" + key for r, key in PARAMS]
)
@pytest.mark.parametrize("value", BOOLS)
def test_each_consumed_parameter_rejects_boolean(r, key, value):
    with pytest.raises(ValueError, match="cannot be boolean"):
        calculate(r["method"], r["value"], {**r["parameters"], key: value})


@pytest.mark.parametrize("r", REFS, ids=lambda r: r["method"])
@pytest.mark.parametrize("factory", FACTORIES, ids=lambda f: f.__name__)
def test_every_native_main_numeric_representation(r, factory):
    value = (
        factory(str(r["value"]))
        if factory in [Decimal, Fraction]
        else factory(r["value"])
    )
    actual, unit, _ = calculate(r["method"], value, r["parameters"])
    # Account for the value actually represented (e.g. float32), rather than
    # treating a quantised source number as the original exact decimal input.
    expected = float(r["expected"]) * float(value) / r["value"]
    assert actual == pytest.approx(
        expected, rel=r["relative_tolerance"], abs=r["absolute_tolerance"]
    )
    assert unit == r["unit"]


@pytest.mark.parametrize("r", REFS, ids=lambda r: r["method"])
@pytest.mark.parametrize(
    "factory", [Decimal, Fraction, np.float64], ids=lambda f: f.__name__
)
def test_native_parameter_scalar_representations(r, factory):
    params = {k: factory(str(v)) for k, v in r["parameters"].items()}
    actual = calculate(r["method"], r["value"], params)
    assert actual[0] == pytest.approx(
        float(r["expected"]), rel=r["relative_tolerance"], abs=r["absolute_tolerance"]
    )


PROPS = [
    ("volume_flow", "m3/h"),
    ("mass_flow", "kg/h"),
    ("molar_flow", "kmol/h"),
    ("pressure", "bar_abs"),
    ("temperature", "degC"),
    ("volume", "m3"),
    ("area", "m2"),
    ("density", "kg/m3"),
    ("heat_duty", "kW"),
    ("power", "kW"),
    ("enthalpy_flow", "kW"),
]


@pytest.mark.parametrize("prop,unit", PROPS)
@pytest.mark.parametrize("value", BOOLS)
def test_all_observation_kinds_guard_before_float(prop, unit, value):
    report = {
        "entities": [
            {
                "key": "s",
                "kind": "equipment" if prop == "volume" else "material",
                "values": [
                    {
                        "id": "source-id",
                        "property": prop,
                        "normalized_value": value,
                        "normalized_unit": unit,
                        "status": "verified",
                    }
                ],
            }
        ]
    }
    with pytest.raises(ValueError, match="cannot be boolean"):
        observation(report, "s", prop)


@pytest.mark.parametrize("factory", FACTORIES, ids=lambda f: f.__name__)
@pytest.mark.parametrize("value", [-100, 0, 1])
def test_observation_preserves_numeric_value_and_source(factory, value):
    report = {
        "entities": [
            {
                "key": "s",
                "values": [
                    {
                        "id": "Balance!D7",
                        "property": "heat_duty",
                        "normalized_value": factory(value),
                        "normalized_unit": "kW",
                        "status": "verified",
                    }
                ],
            }
        ]
    }
    before = copy.deepcopy(report)
    assert observation(report, "s", "heat_duty") == (float(value), "kW", "Balance!D7")
    assert report == before


@pytest.mark.parametrize("value", BOOLS)
@pytest.mark.parametrize("endpoint", ["low", "high"])
def test_ranged_assumptions_guard_before_comparison(value, endpoint):
    spec = {
        "method": "vessel_hold_up",
        "stream_key": "s",
        "parameters": {
            "residence_time_h": {"value": 2, "unit": "h", "low": 1, "high": 3},
            "working_fraction": 0.8,
        },
    }
    spec["parameters"]["residence_time_h"][endpoint] = value
    report = {
        "entities": [
            {
                "key": "s",
                "values": [
                    {
                        "id": "q",
                        "property": "volume_flow",
                        "normalized_value": 10,
                        "normalized_unit": "m3/h",
                        "status": "verified",
                    }
                ],
            }
        ]
    }
    with pytest.raises(ValueError, match="cannot be boolean"):
        derive(spec, report)


@pytest.mark.parametrize("factory", FACTORIES, ids=lambda f: f.__name__)
def test_valid_signed_heat_and_zero_fractions(factory):
    params = {"overall_u_w_m2_k": 500, "lmtd_k": 20, "lmtd_correction": 1}
    assert calculate("exchanger_area", factory(-100), params)[0] == 10
    assert calculate("vaporizer_area", factory(-100), params)[0] == 10
    assert (
        calculate(
            "evaporated_water",
            1000,
            {
                "feed_water_mass_fraction": 0.8,
                "product_water_mass_fraction": factory(0),
            },
        )[0]
        == 800
    )
    assert (
        calculate(
            "phase_change_duty",
            360,
            {
                "latent_heat_kj_kg": 2000,
                "phase_change_fraction": 0.5,
                "sensible_enthalpy_change_kj_kg": factory(0),
            },
        )[0]
        == 100
    )
