"""SIZE-C01 independent Decimal enthalpy-work references; no empirical factors."""

import math
from decimal import Decimal, localcontext

import pytest

from backend.engineering_sizing import calculate

BASE = dict(
    molecular_weight_kg_kmol=28,
    temperature_k=300,
    absolute_pressure_bar=1,
    discharge_pressure_bar=2,
    heat_capacity_ratio=1.4,
    efficiency=0.75,
    compressibility_z=1,
)


def reference(params):
    """Exact binary input values, 100-digit independent ideal enthalpy route."""
    with localcontext() as ctx:
        ctx.prec = 100
        d = lambda key: Decimal.from_float(float(params[key]))
        k = d("heat_capacity_ratio")
        r = Decimal("1.380649e-23") * Decimal("6.02214076e23")
        pressure_ratio = d("discharge_pressure_bar") / d("absolute_pressure_bar")
        t2 = d("temperature_k") * (pressure_ratio.ln() * (k - 1) / k).exp()
        cp = r / d("molecular_weight_kg_kmol") * k / (k - 1)
        return float(cp * (t2 - d("temperature_k")) / d("efficiency"))


GAMMAS = [math.nextafter(1.0, 2.0), 1 + 1e-12, 1 + 1e-8, 1.01, 1.3, 1.4, 1.67, 2.0]
PRESSURES = [math.nextafter(1.0, 2.0), 1 + 1e-12, 1.01, 2.0, 8.0, 20.0]


@pytest.mark.parametrize("gamma", GAMMAS)
@pytest.mark.parametrize("pout", PRESSURES)
def test_independent_compressor_grid(gamma, pout):
    params = {**BASE, "heat_capacity_ratio": gamma, "discharge_pressure_bar": pout}
    actual, unit, _ = calculate("gas_compression", 3600, params)
    assert unit == "kW"
    # Relative-only tolerance keeps tiny near-unity-pressure duties meaningful.
    # 5e-12 matches the parent independent compressor tolerance; not design uncertainty.
    assert actual == pytest.approx(reference(params), rel=5e-12, abs=0)


def test_analytic_gamma_limit_and_reproducibility():
    params = {**BASE, "heat_capacity_ratio": math.nextafter(1.0, 2.0)}
    # As gamma -> 1+, cp*(T2-T1) -> (R/MW)*T1*ln(PR).
    with localcontext() as ctx:
        ctx.prec = 100
        expected = float(
            Decimal("8.31446261815324") / 28 * 300 * Decimal(2).ln() / Decimal(".75")
        )
    first = calculate("gas_compression", 3600, params)
    assert first[0] == pytest.approx(expected, rel=5e-12, abs=0)
    assert first == calculate("gas_compression", 3600, params)


@pytest.mark.parametrize("key", ["absolute_pressure_bar", "discharge_pressure_bar"])
@pytest.mark.parametrize("value", [0, -1, float("nan"), float("inf"), True, None])
def test_invalid_absolute_pressures(key, value):
    with pytest.raises(ValueError):
        calculate("gas_compression", 3600, {**BASE, key: value})


@pytest.mark.parametrize(
    "value", [0, 1, -1, 2.01, float("nan"), float("inf"), True, None]
)
def test_invalid_gamma(value):
    with pytest.raises(ValueError):
        calculate("gas_compression", 3600, {**BASE, "heat_capacity_ratio": value})


@pytest.mark.parametrize("pout", [0.5, 1.0])
def test_noncompressing_pressure_rejected(pout):
    with pytest.raises(ValueError):
        calculate("gas_compression", 3600, {**BASE, "discharge_pressure_bar": pout})


def test_close_large_absolute_pressures_keep_pressure_difference():
    pin = 1e200
    params = {
        **BASE,
        "absolute_pressure_bar": pin,
        "discharge_pressure_bar": math.nextafter(pin, math.inf),
    }
    assert calculate("gas_compression", 3600, params)[0] == pytest.approx(
        reference(params), rel=5e-12, abs=0
    )


def test_overflowing_pressure_ratio_can_have_finite_result():
    # Numerical stress only, not a physically approved compressor pressure range.
    params = {**BASE, "absolute_pressure_bar": 1e-200, "discharge_pressure_bar": 1e200}
    assert calculate("gas_compression", 3600, params)[0] == pytest.approx(
        reference(params), rel=5e-12, abs=0
    )


def test_nonfinite_output_rejected_at_direct_method_boundary():
    from backend.engineering_sizing.compression import calculate as direct

    with pytest.raises(ValueError):
        direct(1e308, {**BASE, "temperature_k": 1e308})


def test_pressure_term_overflow_explicit_rejection():
    with pytest.raises(ValueError, match="finite numerical range"):
        calculate(
            "gas_compression",
            3600,
            {
                **BASE,
                "absolute_pressure_bar": 1e-320,
                "discharge_pressure_bar": 1e308,
                "heat_capacity_ratio": 2,
            },
        )
