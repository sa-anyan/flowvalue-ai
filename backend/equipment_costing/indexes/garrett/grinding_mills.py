"""GRINDING MILLS — GARRETT P. 292 / PDF P. 42

Printed exponents only; documented comparable reference price required.
Ball/rod/wet pebble/jet/rubbish mill page. Source reduction ratio 34; retain exact mill configuration. Installed and purchased references are distinct. Source ton definition is unresolved.
"""

from ...models import ReferenceCost
from .general import estimate_from_reference

VARIANTS = {
    "shredder": (0.53, "source_ton_per_h", "purchased_equipment"),
    "mill_purchased": (0.7, "source_ton_per_h", "purchased_equipment"),
    "mill_installed": (0.62, "source_ton_per_h", "installed_equipment"),
}


def estimate_cost(target_size: float, reference: ReferenceCost):
    if reference.variant not in VARIANTS:
        raise ValueError(
            "Unsupported grinding_mills variant; no exponent will be invented"
        )
    exponent, unit, scope = VARIANTS[reference.variant]
    return estimate_from_reference(
        equipment="grinding_mills",
        variant=reference.variant,
        target_size=target_size,
        reference=reference,
        exponent=exponent,
        size_unit=unit,
        scope=scope,
        printed_page=292,
        notes=(
            "Ball/rod/wet pebble/jet/rubbish mill page. Source reduction ratio 34; retain exact mill configuration. Installed and purchased references are distinct. Source ton definition is unresolved.",
        ),
    )
