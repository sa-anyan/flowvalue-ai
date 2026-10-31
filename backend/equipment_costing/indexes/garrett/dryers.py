"""DRYERS — GARRETT, PRINTED P. 277 / PDF P. 27

Mild steel. Rotary size is peripheral area; fluid-bed/spray size is actual volume. The plotted volume axis is divided by 10; this display factor cancels in same-unit ratios and is NOT applied to actual volumes here. No shelf-area or discharge-method proxy.
Printed size exponent(s) only: a documented comparable reference price is required.
Out-of-range targets use nearest-boundary anchors and are explicitly flagged.
"""

from ...models import ReferenceCost
from .general import estimate_from_reference

VARIANTS = {
    "rotary": (0.45, "ft2_peripheral_area"),
    "fluid_bed": (0.48, "ft3_volume"),
    "spray": (0.29, "ft3_volume"),
}
SOURCE_RANGE = None


def estimate_cost(target_size: float, reference: ReferenceCost):
    if reference.variant not in VARIANTS:
        raise ValueError(
            "Unsupported dryers variant; no formula or exponent will be invented"
        )
    exponent, size_unit = VARIANTS[reference.variant]
    return estimate_from_reference(
        equipment="dryers",
        variant=reference.variant,
        target_size=target_size,
        reference=reference,
        exponent=exponent,
        size_unit=size_unit,
        printed_page=277,
        scope="purchased_equipment",
        source_range=SOURCE_RANGE,
        notes=(
            "Mild steel. Rotary size is peripheral area; fluid-bed/spray size is actual volume. The plotted volume axis is divided by 10; this display factor cancels in same-unit ratios and is NOT applied to actual volumes here. No shelf-area or discharge-method proxy.",
        ),
    )
