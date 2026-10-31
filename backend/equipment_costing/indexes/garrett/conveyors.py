"""CONVEYORS — GARRETT, PRINTED P. 273 / PDF P. 23

Length scaling, mild steel. Keep width/diameter, spacing, throughput and conveyor configuration unchanged from reference. Cross-section factors are not applied.
Printed size exponent(s) only: a documented comparable reference price is required.
Out-of-range targets use nearest-boundary anchors and are explicitly flagged.
"""

from ...models import ReferenceCost
from .general import estimate_from_reference

VARIANTS = {
    "screw": (0.78, "ft_length"),
    "belt": (0.76, "ft_length"),
    "bucket_elevator": (0.5, "ft_length"),
    "roll": (0.5, "ft_length"),
    "pneumatic": (0.37, "ft_length"),
    "vibrating": (1.0, "ft_length"),
}
SOURCE_RANGE = None


def estimate_cost(target_size: float, reference: ReferenceCost):
    if reference.variant not in VARIANTS:
        raise ValueError(
            "Unsupported conveyors variant; no formula or exponent will be invented"
        )
    exponent, size_unit = VARIANTS[reference.variant]
    return estimate_from_reference(
        equipment="conveyors",
        variant=reference.variant,
        target_size=target_size,
        reference=reference,
        exponent=exponent,
        size_unit=size_unit,
        printed_page=273,
        scope="purchased_equipment",
        source_range=SOURCE_RANGE,
        notes=(
            "Length scaling, mild steel. Keep width/diameter, spacing, throughput and conveyor configuration unchanged from reference. Cross-section factors are not applied.",
        ),
    )
