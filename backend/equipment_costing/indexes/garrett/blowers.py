"""BLOWERS — GARRETT, PRINTED P. 261 / PDF P. 11

Printed size exponent(s), applied ONLY to a documented comparable reference cost.
Cast iron with motor. The <3 psi exponent is variable and is deliberately unsupported; no interpolation between pressure variants.
No absolute cost intercept is supplied by this module.
"""

from ...models import ReferenceCost
from .general import estimate_from_reference

EXPONENTS = {"30_psi": 0.52, "10_psi": 0.79}
SIZE_UNIT = "cfm"


def estimate_cost(target_size: float, reference: ReferenceCost):
    if reference.variant not in EXPONENTS:
        raise ValueError("Unsupported blowers variant; no exponent will be invented")
    return estimate_from_reference(
        equipment="blowers",
        variant=reference.variant,
        target_size=target_size,
        reference=reference,
        exponent=EXPONENTS[reference.variant],
        size_unit=SIZE_UNIT,
        printed_page=261,
        scope="purchased_equipment",
        notes=(
            "Cast iron with motor. The <3 psi exponent is variable and is deliberately unsupported; no interpolation between pressure variants.",
        ),
    )
