"""EVAPORATORS — GARRETT, PRINTED P. 280 / PDF P. 30

Printed size exponents, not standalone price equations.
A documented comparable reference price is mandatory.
Single effect, stainless steel; retain the reference construction and service.
"""

from ...models import ReferenceCost
from .general import estimate_from_reference

VARIANTS = {
    "forced_circulation": (0.7, "ft2_heat_transfer_area"),
    "falling_film": (0.53, "ft2_heat_transfer_area"),
    "long_tube": (0.53, "ft2_heat_transfer_area"),
    "short_tube": (0.53, "ft2_heat_transfer_area"),
}


def estimate_cost(target_size: float, reference: ReferenceCost):
    if reference.variant not in VARIANTS:
        raise ValueError(
            "Unsupported evaporators variant; no exponent will be invented"
        )
    exponent, unit = VARIANTS[reference.variant]
    return estimate_from_reference(
        equipment="evaporators",
        variant=reference.variant,
        target_size=target_size,
        reference=reference,
        exponent=exponent,
        size_unit=unit,
        printed_page=280,
        notes=(
            "Single effect, stainless steel; retain the reference construction and service.",
        ),
    )
