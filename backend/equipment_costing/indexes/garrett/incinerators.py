"""INCINERATORS — GARRETT, PRINTED P. 288 / PDF P. 38

Printed size exponents, not standalone price equations.
A documented comparable reference price is mandatory.
Mild steel. Input is heat input in millions of Btu per hour; transferred heat is not interchangeable.
"""

from ...models import ReferenceCost
from .general import estimate_from_reference

VARIANTS = {
    "rotary_kiln": (0.48, "MMBtu_per_h_heat_input"),
    "hearth": (0.64, "MMBtu_per_h_heat_input"),
    "catalytic": (0.75, "MMBtu_per_h_heat_input"),
    "direct_flame": (0.39, "MMBtu_per_h_heat_input"),
}


def estimate_cost(target_size: float, reference: ReferenceCost):
    if reference.variant not in VARIANTS:
        raise ValueError(
            "Unsupported incinerators variant; no exponent will be invented"
        )
    exponent, unit = VARIANTS[reference.variant]
    return estimate_from_reference(
        equipment="incinerators",
        variant=reference.variant,
        target_size=target_size,
        reference=reference,
        exponent=exponent,
        size_unit=unit,
        printed_page=288,
        notes=(
            "Mild steel. Input is heat input in millions of Btu per hour; transferred heat is not interchangeable.",
        ),
    )
