"""Actual gas-volume and dryer-chamber bridge; no default state or residence time."""

from backend.engineering_sizing.registry import calculate
from backend.engineering_sizing.common import positive


def evaluate(method, value, unit, inputs, convert):
    quantity = convert("quantity", unit)
    if method == "standard_gas_flow":
        reference = dict(
            inputs,
            temperature_k=positive(
                inputs.get("reference_temperature_k"), "reference temperature K"
            ),
            absolute_pressure_bar=positive(
                inputs.get("reference_pressure_bar"), "reference absolute pressure bar"
            ),
            compressibility_z=positive(
                inputs.get("reference_compressibility_z"), "reference Z"
            ),
        )
        if quantity == "volume_flow":
            q = convert(value, unit, "m3/h")
            value = (
                q
                * positive(
                    inputs.get("absolute_pressure_bar"), "inlet absolute pressure"
                )
                * 100
                / (
                    8.31446261815324
                    * positive(inputs.get("temperature_k"), "inlet gas temperature")
                    * positive(inputs.get("compressibility_z"), "inlet Z")
                )
            )
            unit = "kmol/h"
        elif quantity not in {"mass_flow", "molar_flow"}:
            raise ValueError(
                "Standard gas flow requires mass, molar or actual volumetric flow with explicit state"
            )
        flow, _, details = evaluate("gas_flow", value, unit, reference, convert)
        details.update(
            reference_temperature_k=reference["temperature_k"],
            reference_pressure_bar=reference["absolute_pressure_bar"],
            reference_compressibility_z=reference["compressibility_z"],
            scope="Explicit reference-state conversion, not proof of the chart's standard/wet/dry basis or equipment pressure applicability",
        )
        return flow, "Sm3/h", details
    if method == "gas_compression":
        if quantity == "mass_flow":
            mass = convert(value, unit, "kg/h")
        elif quantity == "molar_flow":
            mass = convert(value, unit, "kmol/h") * positive(
                inputs.get("molecular_weight_kg_kmol"), "mixture MW"
            )
        elif quantity == "volume_flow":
            q = convert(value, unit, "m3/h")
            mass = (
                q
                * positive(
                    inputs.get("absolute_pressure_bar"), "inlet absolute pressure"
                )
                * 100
                * positive(inputs.get("molecular_weight_kg_kmol"), "mixture MW")
                / (
                    8.31446261815324
                    * positive(inputs.get("temperature_k"), "inlet temperature")
                    * positive(inputs.get("compressibility_z"), "Z")
                )
            )
        else:
            raise ValueError(
                "Gas compression requires mass, molar or actual volumetric flow"
            )
        result, output_unit, details = calculate("gas_compression", mass, inputs)
        details["flow_basis"] = (
            "Source flow converted to kg/h using explicit inlet gas state where necessary"
        )
        details["design_validated"] = False
        details["limitations"] = (
            "Single-stage screening; no intercooling, stage selection or mechanical design. High pressure ratios require separate applicability review."
        )
        return result, output_unit, details
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
