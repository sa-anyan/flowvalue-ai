"""COLUMNS — GARRETT, PRINTED P. 268 / PDF P. 18

Weight-based correlation only, not the diameter-based cost-per-height graph. Printed exponent applies to 100,000–1,000,000 lb. Retain reference construction/pressure; trays and packing are not added automatically.
Printed size exponent(s) only: a documented comparable reference price is required.
Out-of-range targets use nearest-boundary anchors and are explicitly flagged.
"""

from ...models import ReferenceCost
from .general import estimate_from_reference

VARIANTS = {"weight_basis": (0.78, "lb_column_weight")}
SOURCE_RANGE = (100000, 1000000)


def estimate_cost(target_size: float, reference: ReferenceCost):
    if reference.variant not in VARIANTS:
        raise ValueError(
            "Unsupported columns variant; no formula or exponent will be invented"
        )
    exponent, size_unit = VARIANTS[reference.variant]
    return estimate_from_reference(
        equipment="columns",
        variant=reference.variant,
        target_size=target_size,
        reference=reference,
        exponent=exponent,
        size_unit=size_unit,
        printed_page=268,
        scope="purchased_equipment",
        source_range=SOURCE_RANGE,
        notes=(
            "Weight-based correlation only, not the diameter-based cost-per-height graph. Printed exponent applies to 100,000–1,000,000 lb. Retain reference construction/pressure; trays and packing are not added automatically.",
        ),
    )
