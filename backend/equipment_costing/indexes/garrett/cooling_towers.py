"""COOLING TOWERS — GARRETT, PRINTED P. 275 / PDF P. 25

Capacity is THOUSANDS of gpm; retain source gallon definition. Source thermal basis: 15 F range, 10 F approach, 82 F wet bulb. Reference must retain these or a separately reviewed equivalent thermal basis; no thermal factors applied.
Printed size exponent(s) only: a documented comparable reference price is required.
Out-of-range targets use nearest-boundary anchors and are explicitly flagged.
"""

from ...models import ReferenceCost
from .general import estimate_from_reference

VARIANTS = {"standard": (0.79, "1000_gpm")}
SOURCE_RANGE = None


def estimate_cost(target_size: float, reference: ReferenceCost):
    if reference.variant not in VARIANTS:
        raise ValueError(
            "Unsupported cooling_towers variant; no formula or exponent will be invented"
        )
    exponent, size_unit = VARIANTS[reference.variant]
    return estimate_from_reference(
        equipment="cooling_towers",
        variant=reference.variant,
        target_size=target_size,
        reference=reference,
        exponent=exponent,
        size_unit=size_unit,
        printed_page=275,
        scope="purchased_equipment",
        source_range=SOURCE_RANGE,
        notes=(
            "Capacity is THOUSANDS of gpm; retain source gallon definition. Source thermal basis: 15 F range, 10 F approach, 82 F wet bulb. Reference must retain these or a separately reviewed equivalent thermal basis; no thermal factors applied.",
        ),
    )
