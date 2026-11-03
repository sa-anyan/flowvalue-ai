"""Continuous hold-up V=Q*t/f; kinetics/batch cycles require separate justification."""

from .common import positive as p


def calculate(flow, inputs):
    q = p(flow, "volumetric flow m3/h")
    t = p(inputs.get("residence_time_h"), "residence time h")
    f = p(inputs.get("working_fraction"), "working fraction")
    if f > 1:
        raise ValueError("Working fraction cannot exceed one")
    return (
        q * t / f,
        "m3",
        {
            "formula": "V = Q * residence_time / working_fraction",
            "quantity": "vessel capacity",
        },
    )
