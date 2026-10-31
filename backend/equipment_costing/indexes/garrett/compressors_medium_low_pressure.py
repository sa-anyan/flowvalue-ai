"""COMPRESSORS MEDIUM LOW PRESSURE — GARRETT, PRINTED P. 271 / PDF P. 21

Source capacity is standard cubic feet per minute. Straight-lobe example is 20 psi; other displayed examples 150 psi. Keep reference type, pressure and flow reference conditions unchanged; no automatic pressure/driver factor.
Printed size exponent(s) only: a documented comparable reference price is required.
Out-of-range targets use nearest-boundary anchors and are explicitly flagged.
"""

from ...models import ReferenceCost
from .general import estimate_from_reference

VARIANTS = {
    "straight_lobe": (0.51, "scf_per_min"),
    "sliding_vane": (0.79, "scf_per_min"),
    "helical_screw": (0.87, "scf_per_min"),
    "reciprocating_air": (0.34, "scf_per_min"),
}
SOURCE_RANGE = None


def estimate_cost(target_size: float, reference: ReferenceCost):
    if reference.variant not in VARIANTS:
        raise ValueError(
            "Unsupported compressors_medium_low_pressure variant; no formula or exponent will be invented"
        )
    exponent, size_unit = VARIANTS[reference.variant]
    return estimate_from_reference(
        equipment="compressors_medium_low_pressure",
        variant=reference.variant,
        target_size=target_size,
        reference=reference,
        exponent=exponent,
        size_unit=size_unit,
        printed_page=271,
        scope="purchased_equipment",
        source_range=SOURCE_RANGE,
        notes=(
            "Source capacity is standard cubic feet per minute. Straight-lobe example is 20 psi; other displayed examples 150 psi. Keep reference type, pressure and flow reference conditions unchanged; no automatic pressure/driver factor.",
        ),
    )
