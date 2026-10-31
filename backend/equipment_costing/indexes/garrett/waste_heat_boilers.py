"""WASTE HEAT BOILERS — GARRETT, PRINTED P. 263 / PDF P. 13

Printed size exponent(s), applied ONLY to a documented comparable reference cost.
Flue-gas flow is in THOUSANDS of standard cubic feet per minute. Added fins, radiation sections and alloy/clad construction need separate review.
No absolute cost intercept is supplied by this module.
"""

from ...models import ReferenceCost
from .general import estimate_from_reference

EXPONENTS = {"standard": 0.75}
SIZE_UNIT = "1000_scfm"


def estimate_cost(target_size: float, reference: ReferenceCost):
    if reference.variant not in EXPONENTS:
        raise ValueError(
            "Unsupported waste_heat_boilers variant; no exponent will be invented"
        )
    return estimate_from_reference(
        equipment="waste_heat_boilers",
        variant=reference.variant,
        target_size=target_size,
        reference=reference,
        exponent=EXPONENTS[reference.variant],
        size_unit=SIZE_UNIT,
        printed_page=263,
        scope="purchased_equipment",
        notes=(
            "Flue-gas flow is in THOUSANDS of standard cubic feet per minute. Added fins, radiation sections and alloy/clad construction need separate review.",
        ),
    )
