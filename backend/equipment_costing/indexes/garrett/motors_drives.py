"""MOTORS DRIVES — GARRETT P. 293 / PDF P. 43

Printed exponents only; documented comparable reference price required.
Small electric motor basis is TEFC. Large electric motor and variable-speed-drive curves lack their own numerical exponents and remain unsupported. No speed or construction factors applied.
"""

from ...models import ReferenceCost
from .general import estimate_from_reference

VARIANTS = {
    "small_electric_motor": (0.86, "hp", "purchased_equipment"),
    "gas_turbine": (0.76, "hp", "purchased_equipment"),
    "gas_engine": (0.76, "hp", "purchased_equipment"),
    "steam_turbine": (0.41, "hp", "purchased_equipment"),
}


def estimate_cost(target_size: float, reference: ReferenceCost):
    if reference.variant not in VARIANTS:
        raise ValueError(
            "Unsupported motors_drives variant; no exponent will be invented"
        )
    exponent, unit, scope = VARIANTS[reference.variant]
    return estimate_from_reference(
        equipment="motors_drives",
        variant=reference.variant,
        target_size=target_size,
        reference=reference,
        exponent=exponent,
        size_unit=unit,
        scope=scope,
        printed_page=293,
        notes=(
            "Small electric motor basis is TEFC. Large electric motor and variable-speed-drive curves lack their own numerical exponents and remain unsupported. No speed or construction factors applied.",
        ),
    )
