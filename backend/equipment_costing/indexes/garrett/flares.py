"""FLARES — GARRETT, PRINTED P. 283 / PDF P. 33

Printed size exponents, not standalone price equations.
A documented comparable reference price is mandatory.
Mild steel, high-Btu gas, with accessories. Gas heating value and support configuration must match the reference.
"""

from ...models import ReferenceCost
from .general import estimate_from_reference

VARIANTS = {
    "elevated": (0.59, "lb_per_h_waste_gas"),
    "ground": (0.39, "lb_per_h_waste_gas"),
}


def estimate_cost(target_size: float, reference: ReferenceCost):
    if reference.variant not in VARIANTS:
        raise ValueError("Unsupported flares variant; no exponent will be invented")
    exponent, unit = VARIANTS[reference.variant]
    return estimate_from_reference(
        equipment="flares",
        variant=reference.variant,
        target_size=target_size,
        reference=reference,
        exponent=exponent,
        size_unit=unit,
        printed_page=283,
        notes=(
            "Mild steel, high-Btu gas, with accessories. Gas heating value and support configuration must match the reference.",
        ),
    )
