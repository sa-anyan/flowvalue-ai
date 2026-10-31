"""AIR CONDITIONING — GARRETT, PRINTED P. 259 / PDF P. 9

Printed size exponent(s), applied ONLY to a documented comparable reference cost.
Package includes compressor, motor, controls, condenser and refrigerant. No Btu conversion is inferred from the abbreviated source footnote.
No absolute cost intercept is supplied by this module.
"""

from ...models import ReferenceCost
from .general import estimate_from_reference

EXPONENTS = {"standard": 0.73}
SIZE_UNIT = "refrigeration_ton"


def estimate_cost(target_size: float, reference: ReferenceCost):
    if reference.variant not in EXPONENTS:
        raise ValueError(
            "Unsupported air_conditioning variant; no exponent will be invented"
        )
    return estimate_from_reference(
        equipment="air_conditioning",
        variant=reference.variant,
        target_size=target_size,
        reference=reference,
        exponent=EXPONENTS[reference.variant],
        size_unit=SIZE_UNIT,
        printed_page=259,
        scope="purchased_equipment",
        notes=(
            "Package includes compressor, motor, controls, condenser and refrigerant. No Btu conversion is inferred from the abbreviated source footnote.",
        ),
    )
