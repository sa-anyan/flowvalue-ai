"""ION EXCHANGE — GARRETT, PRINTED P. 290 / PDF P. 40

Printed size exponents, not standalone price equations.
A documented comparable reference price is mandatory.
Mild steel, 465 ppm removed source basis. No removal-concentration adjustment is inferred. Source gpm gallon definition must remain consistent with the reference.
"""

from ...models import ReferenceCost
from .general import estimate_from_reference

VARIANTS = {"standard": (0.97, "gpm_water_treated")}


def estimate_cost(target_size: float, reference: ReferenceCost):
    if reference.variant not in VARIANTS:
        raise ValueError(
            "Unsupported ion_exchange variant; no exponent will be invented"
        )
    exponent, unit = VARIANTS[reference.variant]
    return estimate_from_reference(
        equipment="ion_exchange",
        variant=reference.variant,
        target_size=target_size,
        reference=reference,
        exponent=exponent,
        size_unit=unit,
        printed_page=290,
        notes=(
            "Mild steel, 465 ppm removed source basis. No removal-concentration adjustment is inferred. Source gpm gallon definition must remain consistent with the reference.",
        ),
    )
