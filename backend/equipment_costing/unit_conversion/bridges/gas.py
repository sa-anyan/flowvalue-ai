"""Actual gas-volume and dryer-chamber bridge; no default state or residence time."""

from backend.engineering_sizing.registry import calculate
from backend.engineering_sizing.common import positive


def evaluate(method, value, unit, inputs, convert):
    quantity = convert("quantity", unit)
    if quantity == "volume_flow":
        q = convert(value, unit, "m3/h")
    elif quantity == "molar_flow":
        n = convert(value, unit, "kmol/h")
        t = positive(inputs.get("temperature_k"), "absolute temperature K")
        p = positive(inputs.get("absolute_pressure_bar"), "absolute pressure bar")
        z = positive(inputs.get("compressibility_z"), "compressibility Z")
        q = n * 8.31446261815324 * t * z / (p * 100)
    else:
        q, _, _ = calculate("gas_volume", convert(value, unit, "kg/h"), inputs)
    if method == "dryer_volume":
        return calculate("dryer_chamber", q, inputs)
    return (
        q,
        "m3/h",
        {
            "formula": "Q_actual = n * R * T * Z / P_absolute",
            "scope": "Actual gas flow; reference/phase applicability requires user confirmation",
        },
    )
