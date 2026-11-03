"""Area = abs(duty)/(U * positive temperature-driving-force * correction)."""

from .common import positive as p


def calculate(duty, inputs):
    q = p(abs(duty), "heat duty kW")
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
