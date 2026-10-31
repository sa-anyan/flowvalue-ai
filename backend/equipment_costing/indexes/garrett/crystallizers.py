"""CRYSTALLIZERS — GARRETT, PRINTED P. 276 / PDF P. 26

Mild steel. Retain reference crystallizer configuration, process and source ton definition; no ton-to-kg conversion or material/module factors applied.
Printed size exponent(s) only: a documented comparable reference price is required.
Out-of-range targets use nearest-boundary anchors and are explicitly flagged.
"""

from ...models import ReferenceCost
from .general import estimate_from_reference

VARIANTS = {
    "cooling_evaporative": (0.68, "source_ton_per_h"),
    "growth": (0.63, "source_ton_per_h"),
    "forced_circulation": (0.63, "source_ton_per_h"),
    "dtb": (0.63, "source_ton_per_h"),
    "vapor_recompression": (0.75, "source_ton_per_h"),
}
SOURCE_RANGE = None


def estimate_cost(target_size: float, reference: ReferenceCost):
    if reference.variant not in VARIANTS:
        raise ValueError(
            "Unsupported crystallizers variant; no formula or exponent will be invented"
        )
    exponent, size_unit = VARIANTS[reference.variant]
    return estimate_from_reference(
        equipment="crystallizers",
        variant=reference.variant,
        target_size=target_size,
        reference=reference,
        exponent=exponent,
        size_unit=size_unit,
        printed_page=276,
        scope="purchased_equipment",
        source_range=SOURCE_RANGE,
        notes=(
            "Mild steel. Retain reference crystallizer configuration, process and source ton definition; no ton-to-kg conversion or material/module factors applied.",
        ),
    )
