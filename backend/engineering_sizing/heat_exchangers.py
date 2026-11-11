"""Area = abs(duty)/(U * positive temperature-driving-force * correction)."""

from .common import positive as p, reject_boolean


def validate_heat_duty_type(duty):
    """Check before abs/float can erase a Python or NumPy boolean type."""
    reject_boolean(duty, "heat duty kW")


def calculate(duty, inputs):
    validate_heat_duty_type(duty)
    try:
        magnitude = abs(duty)
    except TypeError:
        raise ValueError("heat duty kW requires a signed numerical value") from None
    q = p(magnitude, "heat duty kW")
    u = p(inputs.get("overall_u_w_m2_k"), "overall U W/m2/K")
    dt = p(inputs.get("lmtd_k"), "LMTD K")
    f = p(inputs.get("lmtd_correction"), "LMTD correction")
    if f > 1:
        raise ValueError("LMTD correction cannot exceed one")
    return (
        q * 1000 / (u * dt * f),
        "m2",
        {
            "formula": "A = abs(Q_kW) * 1000 / (U_W_m2_K * LMTD_K * F)",
            "scope": "Thermal area estimate; no mechanical exchanger design",
        },
    )
