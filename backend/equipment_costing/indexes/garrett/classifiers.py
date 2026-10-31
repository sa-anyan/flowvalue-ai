"""CLASSIFIERS — GARRETT, PRINTED P. 267 / PDF P. 17

Mild steel rake/spiral classifier. Source labels solids capacity t/hr without an explicit ton definition; caller must retain the same source ton basis.
Printed size exponent(s) only: a documented comparable reference price is required.
Out-of-range targets use nearest-boundary anchors and are explicitly flagged.
"""

from ...models import ReferenceCost
from .general import estimate_from_reference

VARIANTS = {"rake": (1.32, "source_ton_per_h"), "spiral": (1.32, "source_ton_per_h")}
SOURCE_RANGE = None


def estimate_cost(target_size: float, reference: ReferenceCost):
    if reference.variant not in VARIANTS:
        raise ValueError(
            "Unsupported classifiers variant; no formula or exponent will be invented"
        )
    exponent, size_unit = VARIANTS[reference.variant]
    return estimate_from_reference(
        equipment="classifiers",
        variant=reference.variant,
        target_size=target_size,
        reference=reference,
        exponent=exponent,
        size_unit=size_unit,
        printed_page=267,
        scope="purchased_equipment",
        source_range=SOURCE_RANGE,
        notes=(
            "Mild steel rake/spiral classifier. Source labels solids capacity t/hr without an explicit ton definition; caller must retain the same source ton basis.",
        ),
    )
