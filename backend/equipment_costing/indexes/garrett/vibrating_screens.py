"""VIBRATING SCREENS — GARRETT P. 301 / PDF P. 51

Printed exponents only; documented comparable reference price required.
Mild steel single-deck vibrating screen. No double-deck or material factor applied.
"""

from ...models import ReferenceCost
from .general import estimate_from_reference

VARIANTS = {"single_deck": (0.75, "ft2_screen_area", "purchased_equipment")}


def estimate_cost(target_size: float, reference: ReferenceCost):
    if reference.variant not in VARIANTS:
        raise ValueError(
            "Unsupported vibrating_screens variant; no exponent will be invented"
        )
    exponent, unit, scope = VARIANTS[reference.variant]
    return estimate_from_reference(
        equipment="vibrating_screens",
        variant=reference.variant,
        target_size=target_size,
        reference=reference,
        exponent=exponent,
        size_unit=unit,
        scope=scope,
        printed_page=301,
        notes=(
            "Mild steel single-deck vibrating screen. No double-deck or material factor applied.",
        ),
    )
