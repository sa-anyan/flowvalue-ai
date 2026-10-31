"""BLENDERS — GARRETT, PRINTED P. 260 / PDF P. 10

Printed size exponent(s), applied ONLY to a documented comparable reference cost.
Mild-steel construction. Do not change blender subtype between reference and target.
No absolute cost intercept is supplied by this module.
"""

from ...models import ReferenceCost
from .general import estimate_from_reference

EXPONENTS = {
    "ribbon": 0.6,
    "double_arm": 0.6,
    "sigma": 0.6,
    "twin_shell": 0.6,
    "double_cone": 0.42,
}
SIZE_UNIT = "ft3"


def estimate_cost(target_size: float, reference: ReferenceCost):
    if reference.variant not in EXPONENTS:
        raise ValueError("Unsupported blenders variant; no exponent will be invented")
    return estimate_from_reference(
        equipment="blenders",
        variant=reference.variant,
        target_size=target_size,
        reference=reference,
        exponent=EXPONENTS[reference.variant],
        size_unit=SIZE_UNIT,
        printed_page=260,
        scope="purchased_equipment",
        notes=(
            "Mild-steel construction. Do not change blender subtype between reference and target.",
        ),
    )
