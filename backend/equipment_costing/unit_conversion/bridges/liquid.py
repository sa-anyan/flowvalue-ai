"""Liquid sizing bridges; all density/time/loading assumptions are user inputs."""

from backend.engineering_sizing.registry import calculate
from backend.engineering_sizing.common import positive


def flow(value, unit, inputs, convert):
    if convert("quantity", unit) == "volume_flow":
        return convert(value, unit, "m3/h")
    return convert(value, unit, "kg/h") / positive(
        inputs.get("density_kg_m3"), "density kg/m3"
    )


def evaluate(method, value, unit, inputs, convert):
    q = flow(value, unit, inputs, convert)
    if method == "liquid_flow":
        return (
            q,
            "m3/h",
            {"formula": "Q = mass_flow / density, or supplied volume flow"},
        )
    route = {
        "vessel_volume": "vessel_hold_up",
        "filter_area": "filter_area",
        "pump_coordinate": "pump_duty",
        "pump_power": "pump_duty",
        "mixing_power": "vessel_hold_up",
    }[method]
    size, output, details = calculate(route, q, inputs)
    if method == "pump_power":
        eta = positive(inputs.get("efficiency"), "efficiency")
        if eta > 1:
            raise ValueError("Efficiency must be <= 1")
        return (
            details["shaft_power_kw"],
            "kW",
            {**details, "formula": "P_shaft = Q * differential_pressure / efficiency"},
        )
    if method == "mixing_power":
        return (
            size
            * positive(inputs.get("power_density_kw_m3"), "mixing power density kW/m3"),
            "kW",
            {
                "formula": "P = working/design volume basis * specified power density",
                "scope": "Preliminary mixing-power assumption; not a validated agitator design",
            },
        )
    return size, output, details
