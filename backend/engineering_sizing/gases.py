"""Actual ideal-gas volume; explicit absolute pressure, temperature, MW and Z."""

from .common import positive as p


def calculate(mass_flow, inputs):
    mass = p(mass_flow, "mass flow kg/h")
    mw = p(inputs.get("molecular_weight_kg_kmol"), "mixture molecular weight kg/kmol")
    t = p(inputs.get("temperature_k"), "gas temperature K")
    pressure = p(inputs.get("absolute_pressure_bar"), "gas absolute pressure bar")
    z = p(inputs.get("compressibility_z"), "compressibility Z")
    return (
        mass / mw * 8.31446261815324 * t / (pressure * 100) * z,
        "m3/h",
        {
            "formula": "Q = (mass/MW) * R * T * Z / P_abs",
            "scope": "Actual ideal/real-gas screening volume; explicit phase/composition/condition basis required",
        },
    )
