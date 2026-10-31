"""SMALL STAINLESS TANKS — GARRETT P. 304 / PDF P. 54

Printed exponents only; documented comparable reference price required.
304 stainless steel. Input actual source gallons; no 316/304 material adjustment or plot multiplier applied.
"""

from ...models import ReferenceCost
from .general import estimate_from_reference

VARIANTS = {
    "dished_head_50_psi": (0.68, "source_gal", "purchased_equipment"),
    "flanged_dished_head": (0.48, "source_gal", "purchased_equipment"),
    "cone_top_bottom_legs": (0.57, "source_gal", "purchased_equipment"),
    "flat_top_bottom": (0.93, "source_gal", "purchased_equipment"),
}


def estimate_cost(target_size: float, reference: ReferenceCost):
    if reference.variant not in VARIANTS:
        raise ValueError(
            "Unsupported small_stainless_tanks variant; no exponent will be invented"
        )
    exponent, unit, scope = VARIANTS[reference.variant]
    return estimate_from_reference(
        equipment="small_stainless_tanks",
        variant=reference.variant,
        target_size=target_size,
        reference=reference,
        exponent=exponent,
        size_unit=unit,
        scope=scope,
        printed_page=304,
        notes=(
            "304 stainless steel. Input actual source gallons; no 316/304 material adjustment or plot multiplier applied.",
        ),
    )
