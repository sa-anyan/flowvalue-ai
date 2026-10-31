"""BUILDINGS — GARRETT, PRINTED P. 264 / PDF P. 14

Printed size exponent(s), applied ONLY to a documented comparable reference cost.
Capital item, not process equipment. Office-type building with air conditioning/restrooms/insulation; the scanned exponent is 0.8, not OCR 0.5.
No absolute cost intercept is supplied by this module.
"""

from ...models import ReferenceCost
from .general import estimate_from_reference

EXPONENTS = {"office": 0.8}
SIZE_UNIT = "ft2"


def estimate_cost(target_size: float, reference: ReferenceCost):
    if reference.variant not in EXPONENTS:
        raise ValueError("Unsupported buildings variant; no exponent will be invented")
    return estimate_from_reference(
        equipment="buildings",
        variant=reference.variant,
        target_size=target_size,
        reference=reference,
        exponent=EXPONENTS[reference.variant],
        size_unit=SIZE_UNIT,
        printed_page=264,
        scope="building_cost",
        notes=(
            "Capital item, not process equipment. Office-type building with air conditioning/restrooms/insulation; the scanned exponent is 0.8, not OCR 0.5.",
        ),
    )
