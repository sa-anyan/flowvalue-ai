"""Pump hydraulic power and Garrett flow-times-differential-pressure coordinate."""

from backend.equipment_costing.unit_conversion.unit_aliases import PSI, US_GALLON

from .common import positive as p


def calculate(flow, inputs):
    q = p(flow, "volumetric flow m3/h")
    dp = p(inputs.get("differential_pressure_bar"), "differential pressure bar")
    # Exact US gallon/psi definitions; differential pressure is not operating pressure.
    coordinate = (q / (US_GALLON * 60)) * (dp * 100000 / PSI) / 1000
    details = {
        "formula": "coordinate = Q_US_gpm * differential_pressure_psi / 1000",
        "hydraulic_power_kw": q / 3600 * dp * 100000 / 1000,
    }
    p(coordinate, "calculated pump flow-pressure coordinate")
    p(details["hydraulic_power_kw"], "calculated hydraulic power kW")
    if inputs.get("efficiency") is not None:
        eta = p(inputs["efficiency"], "pump efficiency")
        if eta > 1:
            raise ValueError("Efficiency cannot exceed one")
        details["shaft_power_kw"] = p(
            details["hydraulic_power_kw"] / eta, "calculated shaft power kW"
        )
    return coordinate, "1000 US_gpm_psi", details
