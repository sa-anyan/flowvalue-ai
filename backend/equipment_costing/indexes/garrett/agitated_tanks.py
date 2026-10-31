"""AGITATED TANKS — GARRETT, PRINTED P. 258 / PDF P. 8

Printed size exponent(s), applied ONLY to a documented comparable reference cost.
Jacketed, agitated mild-steel tank. Keep pressure rating and tank configuration identical to the supplied reference.
No absolute cost intercept is supplied by this module.
"""

from ...models import ReferenceCost
from .general import estimate_from_reference

EXPONENTS = {"standard": 0.53}
SIZE_UNIT = "US_gal"


def estimate_cost(target_size: float, reference: ReferenceCost):
    if reference.variant not in EXPONENTS:
        raise ValueError(
            "Unsupported agitated_tanks variant; no exponent will be invented"
        )
    return estimate_from_reference(
        equipment="agitated_tanks",
        variant=reference.variant,
        target_size=target_size,
        reference=reference,
        exponent=EXPONENTS[reference.variant],
        size_unit=SIZE_UNIT,
        printed_page=258,
        scope="purchased_equipment",
        notes=(
            "Jacketed, agitated mild-steel tank. Keep pressure rating and tank configuration identical to the supplied reference.",
        ),
    )
