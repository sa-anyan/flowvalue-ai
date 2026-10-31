"""BOILERS — GARRETT, PRINTED P. 262 / PDF P. 12

Package boilers: 0.65 for 5–1,000 hp; 0.77 for 6–600 × 10^3 lb/h.
Field erected: 0.82. These are alternative capacity bases, not interchangeable
power definitions. The source's boiler-horsepower footnote is ambiguous; no
conversion to mechanical hp or Btu/h is implemented.
"""

from ...models import ReferenceCost
from .general import estimate_from_reference

VARIANTS = {
    "package_hp": (0.65, "boiler_hp", (5, 1000)),
    "package_steam": (0.77, "lb_per_h_steam", (6000, 600000)),
    "field_erected": (0.82, "lb_per_h_steam", None),
}


def estimate_cost(target_size: float, reference: ReferenceCost):
    if reference.variant not in VARIANTS:
        raise ValueError("Choose package_hp, package_steam or field_erected")
    exponent, unit, bounds = VARIANTS[reference.variant]
    return estimate_from_reference(
        equipment="boilers",
        variant=reference.variant,
        target_size=target_size,
        reference=reference,
        exponent=exponent,
        size_unit=unit,
        printed_page=262,
        source_range=bounds,
        notes=(
            "Reference/target must retain pressure rating, fuel and boiler configuration.",
            "No boiler-hp/Btu conversion or pressure/coal-firing factor applied.",
        ),
    )
