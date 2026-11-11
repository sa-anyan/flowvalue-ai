"""Explicit physical derivations, separate from same-quantity unit conversion.

Inputs are typed, source-linked Measurements. No duration, working volume or
flow is inferred. Existing liquid/gas/equipment derivations remain in bridges/.
"""

from dataclasses import asdict

from .models import Measurement
from .unit_conversion import UnitResolutionError, convert


def _normalized(measurement, unit):
    if not isinstance(measurement, Measurement):
        raise UnitResolutionError("A source-linked Measurement is required")
    result = convert(
        measurement.value, measurement.unit, unit, source=measurement.source
    )
    if result.value is None:
        raise UnitResolutionError("; ".join(result.issues))
    return result


def _result(value, unit, target, formula, conversions):
    result = convert(value, unit, target)
    if result.value is None:
        raise UnitResolutionError("; ".join(result.issues))
    return Measurement(
        result.value,
        target,
        {
            "relationship": formula,
            "inputs": [asdict(c) for c in conversions],
            "output_conversion": asdict(result),
            "scope": "Explicit supplied physical basis; not inferred equipment design",
        },
    )


def average_power(energy, duration, *, target_unit="kW"):
    """E/duration is average signed power, not a peak or motor rating."""
    e = _normalized(energy, "J")
    t = _normalized(duration, "s")
    if t.value <= 0:
        raise UnitResolutionError("Explicit duration must be positive")
    return _result(
        e.value / t.value, "W", target_unit, "P_average = E / duration", (e, t)
    )


def residence_time(working_volume, actual_volume_flow, *, target_unit="h"):
    """Vworking/Qactual; the caller explicitly selects the same-phase basis."""
    v = _normalized(working_volume, "m3")
    q = _normalized(actual_volume_flow, "m3/s")
    if q.value <= 0:
        raise UnitResolutionError("Explicit actual volume flow must be positive")
    return _result(
        v.value / q.value,
        "s",
        target_unit,
        "residence_time = working_volume / actual_volume_flow",
        (v, q),
    )
