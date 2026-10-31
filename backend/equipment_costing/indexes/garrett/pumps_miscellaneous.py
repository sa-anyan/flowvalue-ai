"""PUMPS MISCELLANEOUS — GARRETT P. 297 / PDF P. 47

Printed exponents only; documented comparable reference price required.
Mild steel source basis. Gear curve is flow in gpm, not flow-times-pressure. Chemical injection has a separately scaled flow annotation without an explicit unit: source_flow_basis requires an identical documented reference basis. Sliding-vane curve has no distinct printed exponent. No graph-axis price multipliers or horsepower conversions applied.
"""

from ...models import ReferenceCost
from .general import estimate_from_reference

VARIANTS = {
    "reciprocating": (0.59, "gpm_times_psi", "purchased_equipment"),
    "turbine": (0.47, "gpm_times_psi", "purchased_equipment"),
    "chemical_injection": (0.52, "source_flow_basis", "purchased_equipment"),
    "diaphragm": (0.43, "gpm_times_psi", "purchased_equipment"),
    "rotary": (0.52, "gpm_times_psi", "purchased_equipment"),
    "gear": (0.75, "source_gpm", "purchased_equipment"),
    "sump": (0.15, "gpm_times_psi", "purchased_equipment"),
}


def estimate_cost(target_size: float, reference: ReferenceCost):
    if reference.variant not in VARIANTS:
        raise ValueError(
            "Unsupported pumps_miscellaneous variant; no exponent will be invented"
        )
    exponent, unit, scope = VARIANTS[reference.variant]
    return estimate_from_reference(
        equipment="pumps_miscellaneous",
        variant=reference.variant,
        target_size=target_size,
        reference=reference,
        exponent=exponent,
        size_unit=unit,
        scope=scope,
        printed_page=297,
        notes=(
            "Mild steel source basis. Gear curve is flow in gpm, not flow-times-pressure. Chemical injection has a separately scaled flow annotation without an explicit unit: source_flow_basis requires an identical documented reference basis. Sliding-vane curve has no distinct printed exponent. No graph-axis price multipliers or horsepower conversions applied.",
        ),
    )
