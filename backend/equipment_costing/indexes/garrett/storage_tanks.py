"""STORAGE TANKS — GARRETT P. 303 / PDF P. 53

Printed exponents only; documented comparable reference price required.
Mild steel unless variant states otherwise. Actual source gallons, not thousands-of-gallons plot coordinates. Source gallon definition retained. Construction/pressure/support scope must match reference. No floating-roof or lining factor applied.
"""

from ...models import ReferenceCost
from .general import estimate_from_reference

VARIANTS = {
    "small_cone_top": (0.51, "source_gal", "purchased_equipment"),
    "large_cone_top": (0.51, "source_gal", "purchased_equipment"),
    "horizontal_pressure": (0.72, "source_gal", "purchased_equipment"),
    "sphere": (0.62, "source_gal", "purchased_equipment"),
    "fiberglass": (0.71, "source_gal", "purchased_equipment"),
    "small_storage": (0.71, "source_gal", "purchased_equipment"),
}


def estimate_cost(target_size: float, reference: ReferenceCost):
    if reference.variant not in VARIANTS:
        raise ValueError(
            "Unsupported storage_tanks variant; no exponent will be invented"
        )
    exponent, unit, scope = VARIANTS[reference.variant]
    return estimate_from_reference(
        equipment="storage_tanks",
        variant=reference.variant,
        target_size=target_size,
        reference=reference,
        exponent=exponent,
        size_unit=unit,
        scope=scope,
        printed_page=303,
        notes=(
            "Mild steel unless variant states otherwise. Actual source gallons, not thousands-of-gallons plot coordinates. Source gallon definition retained. Construction/pressure/support scope must match reference. No floating-roof or lining factor applied.",
        ),
    )
