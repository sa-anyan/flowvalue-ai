"""FURNACES — GARRETT, PRINTED P. 284 / PDF P. 34

Printed size exponents, not standalone price equations.
A documented comparable reference price is mandatory.
Mild steel tubes. Input is transferred heat, not fuel input. MM denotes one million Btu.
"""

from ...models import ReferenceCost
from .general import estimate_from_reference

VARIANTS = {
    "hershoff": (0.48, "MMBtu_per_h_transferred"),
    "box": (0.7, "MMBtu_per_h_transferred"),
    "cylindrical": (0.78, "MMBtu_per_h_transferred"),
}


def estimate_cost(target_size: float, reference: ReferenceCost):
    if reference.variant not in VARIANTS:
        raise ValueError("Unsupported furnaces variant; no exponent will be invented")
    exponent, unit = VARIANTS[reference.variant]
    return estimate_from_reference(
        equipment="furnaces",
        variant=reference.variant,
        target_size=target_size,
        reference=reference,
        exponent=exponent,
        size_unit=unit,
        printed_page=284,
        notes=(
            "Mild steel tubes. Input is transferred heat, not fuel input. MM denotes one million Btu.",
        ),
    )
