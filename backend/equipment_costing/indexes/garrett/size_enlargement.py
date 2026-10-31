"""SIZE ENLARGEMENT — GARRETT P. 302 / PDF P. 52

Printed exponents only; documented comparable reference price required.
Mild steel; source ton definition unresolved. Screw extruder and disk/drum granulator correction factors do not independently establish base prices; unsupported as standalone variants.
"""

from ...models import ReferenceCost
from .general import estimate_from_reference

VARIANTS = {
    "pug_mill": (0.15, "source_ton_per_h", "purchased_equipment"),
    "pellet_mill": (0.12, "source_ton_per_h", "purchased_equipment"),
    "pelletizing_rolls": (0.58, "source_ton_per_h", "purchased_equipment"),
}


def estimate_cost(target_size: float, reference: ReferenceCost):
    if reference.variant not in VARIANTS:
        raise ValueError(
            "Unsupported size_enlargement variant; no exponent will be invented"
        )
    exponent, unit, scope = VARIANTS[reference.variant]
    return estimate_from_reference(
        equipment="size_enlargement",
        variant=reference.variant,
        target_size=target_size,
        reference=reference,
        exponent=exponent,
        size_unit=unit,
        scope=scope,
        printed_page=302,
        notes=(
            "Mild steel; source ton definition unresolved. Screw extruder and disk/drum granulator correction factors do not independently establish base prices; unsupported as standalone variants.",
        ),
    )
