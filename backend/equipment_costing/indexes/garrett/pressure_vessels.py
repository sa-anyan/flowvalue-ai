"""PRESSURE VESSELS — GARRETT P. 298 / PDF P. 48

Printed exponents only; documented comparable reference price required.
Mild steel, 15 psi volume curve only. Source gallon definition retained without conversion. 250 psi and weight-based horizontal/vertical curves have no printed exponent on this page and remain unsupported; column exponent is not silently borrowed.
"""

from ...models import ReferenceCost
from .general import estimate_from_reference

VARIANTS = {"15_psi_volume": (0.64, "source_gal", "purchased_equipment")}


def estimate_cost(target_size: float, reference: ReferenceCost):
    if reference.variant not in VARIANTS:
        raise ValueError(
            "Unsupported pressure_vessels variant; no exponent will be invented"
        )
    exponent, unit, scope = VARIANTS[reference.variant]
    return estimate_from_reference(
        equipment="pressure_vessels",
        variant=reference.variant,
        target_size=target_size,
        reference=reference,
        exponent=exponent,
        size_unit=unit,
        scope=scope,
        printed_page=298,
        notes=(
            "Mild steel, 15 psi volume curve only. Source gallon definition retained without conversion. 250 psi and weight-based horizontal/vertical curves have no printed exponent on this page and remain unsupported; column exponent is not silently borrowed.",
        ),
    )
