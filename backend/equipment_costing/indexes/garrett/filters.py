"""FILTERS — GARRETT, PRINTED P. 282 / PDF P. 32

Printed size exponents, not standalone price equations.
A documented comparable reference price is mandatory.
Stainless steel. Auxiliary vacuum pumps/receivers are not automatically included.
"""

from ...models import ReferenceCost
from .general import estimate_from_reference

VARIANTS = {
    "rotary_vacuum_drum": (0.39, "ft2_filter_area"),
    "rotary_leaf": (0.39, "ft2_filter_area"),
    "vacuum_table": (0.5, "ft2_filter_area"),
    "tilting_pan": (0.5, "ft2_filter_area"),
    "belt": (0.5, "ft2_filter_area"),
    "pressure_leaf": (0.61, "ft2_filter_area"),
    "plate_and_frame": (0.61, "ft2_filter_area"),
}


def estimate_cost(target_size: float, reference: ReferenceCost):
    if reference.variant not in VARIANTS:
        raise ValueError("Unsupported filters variant; no exponent will be invented")
    exponent, unit = VARIANTS[reference.variant]
    return estimate_from_reference(
        equipment="filters",
        variant=reference.variant,
        target_size=target_size,
        reference=reference,
        exponent=exponent,
        size_unit=unit,
        printed_page=282,
        notes=(
            "Stainless steel. Auxiliary vacuum pumps/receivers are not automatically included.",
        ),
    )
