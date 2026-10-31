"""ELECTRIC GENERATORS — GARRETT, PRINTED P. 285 / PDF P. 35

Printed size exponents, not standalone price equations.
A documented comparable reference price is mandatory.
Electric generating capacity. Retain the reference driver, fuel, and supply scope; no driver conversion factor is applied.
"""

from ...models import ReferenceCost
from .general import estimate_from_reference

VARIANTS = {
    "diesel_drive": (0.71, "kW_electric_capacity"),
    "turbine_drive": (0.76, "kW_electric_capacity"),
}


def estimate_cost(target_size: float, reference: ReferenceCost):
    if reference.variant not in VARIANTS:
        raise ValueError(
            "Unsupported electric_generators variant; no exponent will be invented"
        )
    exponent, unit = VARIANTS[reference.variant]
    return estimate_from_reference(
        equipment="electric_generators",
        variant=reference.variant,
        target_size=target_size,
        reference=reference,
        exponent=exponent,
        size_unit=unit,
        printed_page=285,
        notes=(
            "Electric generating capacity. Retain the reference driver, fuel, and supply scope; no driver conversion factor is applied.",
        ),
    )
