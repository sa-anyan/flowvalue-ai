"""Duty/enthalpy difference to area; reference and same-side selection are explicit."""

from backend.engineering_sizing.registry import calculate


def evaluate(value, unit, inputs, convert, outlet=None):
    duty = convert(value, unit, "kW")
    if outlet is not None:
        duty = convert(outlet["value"], outlet["unit"], "kW") - duty
    return calculate("exchanger_area", duty, inputs)
