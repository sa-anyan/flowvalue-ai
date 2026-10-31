"""VACUUM EQUIPMENT — GARRETT P. 306 / PDF P. 56

Printed exponents only; documented comparable reference price required.
Mild steel/cast iron source basis. Vacuum capacity factor is equivalent-air lb/h divided by vacuum in mm mercury absolute, not gauge vacuum. Barometric condenser uses thousands of source-gpm water. Stage/condenser/material configuration must match reference; no factors inferred.
"""

from ...models import ReferenceCost
from .general import estimate_from_reference

VARIANTS = {
    "vacuum_pump": (0.75, "lb_per_h_air_per_mmHg_absolute", "purchased_equipment"),
    "steam_jet_ejector": (
        0.42,
        "lb_per_h_air_per_mmHg_absolute",
        "purchased_equipment",
    ),
    "barometric_condenser": (0.67, "1000_source_gpm_water", "purchased_equipment"),
}


def estimate_cost(target_size: float, reference: ReferenceCost):
    if reference.variant not in VARIANTS:
        raise ValueError(
            "Unsupported vacuum_equipment variant; no exponent will be invented"
        )
    exponent, unit, scope = VARIANTS[reference.variant]
    return estimate_from_reference(
        equipment="vacuum_equipment",
        variant=reference.variant,
        target_size=target_size,
        reference=reference,
        exponent=exponent,
        size_unit=unit,
        scope=scope,
        printed_page=306,
        notes=(
            "Mild steel/cast iron source basis. Vacuum capacity factor is equivalent-air lb/h divided by vacuum in mm mercury absolute, not gauge vacuum. Barometric condenser uses thousands of source-gpm water. Stage/condenser/material configuration must match reference; no factors inferred.",
        ),
    )
