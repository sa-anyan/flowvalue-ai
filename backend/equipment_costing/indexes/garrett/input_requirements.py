"""Garrett equipment input contracts, kept beside the costing source definitions.

Shared conversion constants live in unit_conversion, not in equipment modules.
Targets are chart coordinates, never automatic equipment sizing assumptions.
"""

from ...unit_conversion.models import InputRequirement

# Source label -> (physical quantity, canonical chart-coordinate unit).
SIZE_INPUTS = {
    "actual chamber volume, ft3": ("volume", "ft3"),
    "1,000 lb carbon": ("mass", "1000 lb"),
    "1,000 scfm flue gas": ("standard_volume_flow", "1000 scfm"),
    "HP": ("power", "hp"),
    "HP (small axis)": ("boiler_power", "boiler_hp"),
    "air flow capacity, cfm": ("standard_volume_flow", "scfm"),
    "capacity, 1,000 gpm": ("volume_flow", "1000 gpm"),
    "capacity, ton/h": ("mass_flow", "ton/h"),
    "cfm": ("volume_flow", "cfm"),
    "column diameter, ft": ("length", "ft"),
    "diameter, ft": ("length", "ft"),
    "drive rating, HP": ("power", "hp"),
    "duct diameter, in": ("length", "in"),
    "filter area, ft²": ("area", "ft2"),
    "flow rate, 1,000 cfm": ("volume_flow", "1000 cfm"),
    "flow × pressure, gpm·psi/1,000": ("flow_pressure_product", "1000 gpm_psi"),
    "ft² (all floors)": ("area", "ft2"),
    "ft³": ("volume", "ft3"),
    "gal": ("volume", "gal"),
    "gas flow, 1,000 cfm": ("volume_flow", "1000 cfm"),
    "generating capacity, kW": ("power", "kW"),
    "grinding capacity, ton/h": ("mass_flow", "ton/h"),
    "heat input, million Btu/h": ("power", "million Btu/h"),
    "heat transfer area, 1,000 ft²": ("area", "1000 ft2"),
    "heat transferred, MM Btu/h": ("power", "million Btu/h"),
    "heat-transfer area, 10 ft² (different from shell/tube)": ("area", "10 ft2"),
    "heat-transfer area, ft²": ("area", "ft2"),
    "height, ft": ("length", "ft"),
    "height, ft (short scale)": ("length", "ft"),
    "horsepower, HP": ("power", "hp"),
    "inlet flow, thousand cfm": ("volume_flow", "1000 cfm"),
    "insulation thickness, in": ("length", "in"),
    "lb steam/h (large axis)": ("mass_flow", "lb/h"),
    "length, ft": ("length", "ft"),
    "motor rating, HP": ("power", "hp"),
    "nominal pipe diameter, in": ("length", "in"),
    "packing size, in": ("length", "in"),
    "peripheral heat-transfer area, ft²": ("area", "ft2"),
    "pipe diameter, in": ("length", "in"),
    "reactor volume, 1,000 gal": ("volume", "1000 gal"),
    "refrigeration capacity, tons": ("power", "refrigeration_ton"),
    "refrigeration ton": ("power", "refrigeration_ton"),
    "screen area, ft²": ("area", "ft2"),
    # Workbook calls this tonnes; the PDF says t/h without a ton definition.
    "solids handled, tonnes/h": ("mass_flow", "ton/h"),
    "t/hr (as printed)": ("mass_flow", "ton/h"),
    "tank capacity, 1,000 gal": ("volume", "1000 gal"),
    "tank diameter, ft": ("length", "ft"),
    "throughput, ton/h": ("mass_flow", "ton/h"),
    "vessel capacity, 1,000 gal": ("volume", "1000 gal"),
    "vessel weight, lb": ("mass", "lb"),
    "waste gas flow, lb/h": ("mass_flow", "lb/h"),
    "water throughput, 1,000 gpm": ("volume_flow", "1000 gpm"),
    "water treated, gpm": ("volume_flow", "gpm"),
}


def input_requirements(model):
    """Required size plus optional explicitly named engineering context fields.

    Pressure/temperature normalization does not select or recalibrate a curve.
    Design and operating conditions are never substituted for one another.
    """
    meta = model["interpretation"]
    if meta["blocking_issues"]:
        size = InputRequirement(
            "size", "unresolved", None, issue="; ".join(meta["blocking_issues"])
        )
    elif model["size_unit"] not in SIZE_INPUTS:
        size = InputRequirement(
            "size",
            "unresolved",
            None,
            issue="Chart-coordinate interpretation is not implemented",
        )
    else:
        quantity, unit = SIZE_INPUTS[model["size_unit"]]
        size = InputRequirement("size", quantity, unit)
    return (
        size,
        InputRequirement(
            "design_pressure",
            "pressure",
            "psi",
            False,
            "design pressure; not operating pressure",
        ),
        InputRequirement(
            "operating_pressure",
            "pressure",
            "psi",
            False,
            "operating pressure; not design pressure",
        ),
        InputRequirement(
            "temperature",
            "temperature",
            "degF",
            False,
            "context only; no sizing or curve selection",
        ),
    )
