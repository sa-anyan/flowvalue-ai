"""THICKENERS CLARIFIERS — GARRETT P. 305 / PDF P. 55

Printed exponents only; documented comparable reference price required.
Rake mechanism, concrete tank and drive. Diameter in feet. No concrete/steel correction automatically applied.
"""

from ...models import ReferenceCost
from .general import estimate_from_reference

VARIANTS = {"rake_concrete_tank_drive": (1.03, "ft_diameter", "purchased_equipment")}


def estimate_cost(target_size: float, reference: ReferenceCost):
    if reference.variant not in VARIANTS:
        raise ValueError(
            "Unsupported thickeners_clarifiers variant; no exponent will be invented"
        )
    exponent, unit, scope = VARIANTS[reference.variant]
    return estimate_from_reference(
        equipment="thickeners_clarifiers",
        variant=reference.variant,
        target_size=target_size,
        reference=reference,
        exponent=exponent,
        size_unit=unit,
        scope=scope,
        printed_page=305,
        notes=(
            "Rake mechanism, concrete tank and drive. Diameter in feet. No concrete/steel correction automatically applied.",
        ),
    )
