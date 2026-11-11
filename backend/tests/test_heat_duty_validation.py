"""SIZE-C02: guard Python/NumPy boolean duties before numeric coercion."""

from decimal import Decimal
from fractions import Fraction

import numpy as np
import pytest

from backend.engineering_sizing.registry import calculate
from backend.engineering_sizing.heat_exchangers import calculate as shared
from backend.engineering_sizing.adapter import derive, observation

PARAMS = dict(overall_u_w_m2_k=500, lmtd_k=20, lmtd_correction=1)
METHODS = ["exchanger_area", "vaporizer_area"]
BOOLEANS = [True, False, np.bool_(True), np.bool_(False)]


def report(value, unit="kW"):
    return {
        "entities": [
            {
                "key": "stream",
                "values": [
                    {
                        "id": "Q1",
                        "property": "heat_duty",
                        "normalized_value": value,
                        "normalized_unit": unit,
                        "status": "verified",
                    }
                ],
            }
        ]
    }


def spec(method):
    return dict(method=method, stream_key="stream", parameters=PARAMS)


@pytest.mark.parametrize("value", BOOLEANS)
def test_direct_shared_boolean_rejected(value):
    with pytest.raises(ValueError, match="cannot be boolean"):
        shared(value, PARAMS)


@pytest.mark.parametrize("method", METHODS)
@pytest.mark.parametrize("value", BOOLEANS)
def test_registry_boolean_rejected(method, value):
    with pytest.raises(ValueError, match="cannot be boolean"):
        calculate(method, value, PARAMS)


@pytest.mark.parametrize("method", METHODS)
@pytest.mark.parametrize("value", BOOLEANS)
def test_adapter_boolean_rejected(method, value):
    with pytest.raises(ValueError):
        derive(spec(method), report(value))


@pytest.mark.parametrize("value", BOOLEANS)
def test_source_observation_boolean_rejected_before_float(value):
    with pytest.raises(ValueError, match="cannot be boolean"):
        observation(report(value), "stream", "heat_duty")


@pytest.mark.parametrize(
    "value",
    [
        100,
        -100,
        100.0,
        -100.0,
        Decimal("100"),
        Decimal("-100"),
        Fraction(100),
        Fraction(-100),
        np.float64(100),
        np.float32(-100),
        np.int64(-100),
    ],
)
@pytest.mark.parametrize("method", METHODS)
def test_independent_signed_area_reference(method, value):
    # 100 kW magnitude / (500 W/m2/K *20 K) = 10 m2, independently derived.
    for actual in [
        shared(value, PARAMS),
        calculate(method, value, PARAMS),
        derive(spec(method), report(value)),
    ]:
        assert actual[0] == pytest.approx(10, rel=1e-12, abs=1e-14)
        assert actual[1] == "m2"


@pytest.mark.parametrize("method", METHODS)
@pytest.mark.parametrize(
    "value",
    [0, 0.0, -0.0, None, "not a number", float("nan"), float("inf"), -float("inf")],
)
def test_invalid_and_zero_duties_retain_rejection(method, value):
    # Zero has never represented a supported positive equipment area.
    for call in [
        lambda: shared(value, PARAMS),
        lambda: calculate(method, value, PARAMS),
        lambda: derive(spec(method), report(value)),
    ]:
        with pytest.raises(ValueError):
            call()


@pytest.mark.parametrize("method", METHODS)
@pytest.mark.parametrize("unit", ["kg/h", "m3", "W"])
def test_wrong_canonical_duty_units_rejected(method, unit):
    with pytest.raises(ValueError):
        derive(spec(method), report(100, unit))
