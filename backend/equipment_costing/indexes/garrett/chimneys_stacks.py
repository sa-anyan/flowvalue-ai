"""CHIMNEYS STACKS — GARRETT, PRINTED P. 266 / PDF P. 16

Printed size exponent(s), applied ONLY to a documented comparable reference cost.
Tall carbon-steel lined/insulated stacks with foundations. Short-stack exponent is not printed and is unsupported. No diameter/material factors applied.
No absolute cost intercept is supplied by this module.
"""

from ...models import ReferenceCost
from .general import estimate_from_reference

EXPONENTS = {"tall": 1.63}
SIZE_UNIT = "ft"


def estimate_cost(target_size: float, reference: ReferenceCost):
    if reference.variant not in EXPONENTS:
        raise ValueError(
            "Unsupported chimneys_stacks variant; no exponent will be invented"
        )
    return estimate_from_reference(
        equipment="chimneys_stacks",
        variant=reference.variant,
        target_size=target_size,
        reference=reference,
        exponent=EXPONENTS[reference.variant],
        size_unit=SIZE_UNIT,
        printed_page=266,
        scope="purchased_equipment",
        notes=(
            "Tall carbon-steel lined/insulated stacks with foundations. Short-stack exponent is not printed and is unsupported. No diameter/material factors applied.",
        ),
    )
