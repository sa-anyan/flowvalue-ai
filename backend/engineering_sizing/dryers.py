"""Preliminary chamber hold-up from actual gas flow and explicit gas residence time."""

from .common import positive as p


def calculate(flow, inputs):
    q = p(flow, "actual gas volume m3/h")
    t = p(inputs.get("gas_residence_time_s"), "gas residence seconds")
    return (
        q * t / 3600,
        "m3",
        {
            "formula": "V = actual gas flow * residence_seconds / 3600",
            "scope": "Gas hold-up screening only; evaporation, droplet drying and vendor design may govern",
        },
    )
