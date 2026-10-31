"""REFRIGERATION — GARRETT P. 300 / PDF P. 50

Printed exponents only; documented comparable reference price required.
40 deg F source basis; no evaporating-temperature adjustment. Refrigeration tons are not mass tons; ambiguous abbreviated footnote is not used for automatic conversion.
"""

from ...models import ReferenceCost
from .general import estimate_from_reference

VARIANTS = {"40_F": (0.69, "refrigeration_ton", "purchased_equipment")}


def estimate_cost(target_size: float, reference: ReferenceCost):
    if reference.variant not in VARIANTS:
        raise ValueError(
            "Unsupported refrigeration variant; no exponent will be invented"
        )
    exponent, unit, scope = VARIANTS[reference.variant]
    return estimate_from_reference(
        equipment="refrigeration",
        variant=reference.variant,
        target_size=target_size,
        reference=reference,
        exponent=exponent,
        size_unit=unit,
        scope=scope,
        printed_page=300,
        notes=(
            "40 deg F source basis; no evaporating-temperature adjustment. Refrigeration tons are not mass tons; ambiguous abbreviated footnote is not used for automatic conversion.",
        ),
    )
