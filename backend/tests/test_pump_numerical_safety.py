"""SIZE-C03: independent pressure-work checks and finite direct/registry outputs."""

import math
from decimal import Decimal, localcontext

import pytest
from backend.engineering_sizing import calculate
from backend.engineering_sizing.pumps import calculate as direct


@pytest.mark.parametrize("flow", [0.036, 3.6, 36, 3600])
@pytest.mark.parametrize("dp", [0.01, 1, 10])
@pytest.mark.parametrize("efficiency", [None, 0.1, 0.5, 1])
def test_independent_pump_reference(flow, dp, efficiency):
    with localcontext() as ctx:
        ctx.prec = 60
        q = Decimal.from_float(flow)
        delta = Decimal.from_float(dp) * 100000
        hydraulic = q / 3600 * delta / 1000
        psi = Decimal(".45359237") * Decimal("9.80665") / Decimal(".0254") ** 2
        coordinate = hydraulic / (1000 * Decimal(".003785411784") / 60 * psi / 1000)
        shaft = (
            None if efficiency is None else hydraulic / Decimal.from_float(efficiency)
        )
    params = {"differential_pressure_bar": dp, "efficiency": efficiency}
    kernel = direct(flow, params)
    registered = calculate("pump_duty", flow, params)
    # TRACE01: the registry adds only method-version metadata to the audit.
    # Numerical values, units and every other audit field must match the
    # kernel exactly; the metadata itself must name the registered method.
    assert registered[2]["engineering_method"]["method_id"] == "pump_duty"
    for result in [kernel, registered]:
        value, unit, details = result
        assert unit == "1000 US_gpm_psi"
        assert value == pytest.approx(float(coordinate), rel=1e-11, abs=0)
        assert details["hydraulic_power_kw"] == pytest.approx(
            float(hydraulic), rel=1e-13, abs=0
        )
        if shaft is None:
            assert "shaft_power_kw" not in details
        else:
            assert details["shaft_power_kw"] == pytest.approx(
                float(shaft), rel=1e-13, abs=0
            )
        details_without_version = {
            k: v for k, v in details.items() if k != "engineering_method"
        }
        assert (value, unit, details_without_version) == direct(flow, params)


@pytest.mark.parametrize("efficiency", [0, -1, 1.01, True, float("nan"), float("inf")])
def test_invalid_efficiency(efficiency):
    with pytest.raises(ValueError):
        direct(3.6, dict(differential_pressure_bar=1, efficiency=efficiency))


@pytest.mark.parametrize(
    "flow,dp,efficiency", [(3.6, 1, 1e-320), (1e308, 1e308, 0.5), (1e-320, 1e-320, 0.5)]
)
def test_unrepresentable_outputs_rejected(flow, dp, efficiency):
    with pytest.raises(ValueError, match="finite and positive"):
        direct(flow, dict(differential_pressure_bar=dp, efficiency=efficiency))


def test_no_arbitrary_efficiency_floor():
    result = direct(3.6, dict(differential_pressure_bar=1, efficiency=1e-300))
    assert math.isfinite(result[2]["shaft_power_kw"])
    assert result[2]["shaft_power_kw"] == pytest.approx(1e299)
