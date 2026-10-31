"""PUMPS CENTRIFUGAL — GARRETT P. 296 / PDF P. 46

Printed exponents only; documented comparable reference price required.
Cast iron horizontal, includes motor/coupling/base. Size is raw flow-times-pressure product, not horsepower; graph scaling cancels in reference ratios. Conventional and inline curves have no printed exponent. No hydraulic sizing or pressure factors applied.
"""

from ...models import ReferenceCost
from .general import estimate_from_reference

VARIANTS = {
    "axial_flow": (0.79, "gpm_times_psi", "purchased_equipment"),
    "mixed_flow": (0.79, "gpm_times_psi", "purchased_equipment"),
}


def estimate_cost(target_size: float, reference: ReferenceCost):
    if reference.variant not in VARIANTS:
        raise ValueError(
            "Unsupported pumps_centrifugal variant; no exponent will be invented"
        )
    exponent, unit, scope = VARIANTS[reference.variant]
    return estimate_from_reference(
        equipment="pumps_centrifugal",
        variant=reference.variant,
        target_size=target_size,
        reference=reference,
        exponent=exponent,
        size_unit=unit,
        scope=scope,
        printed_page=296,
        notes=(
            "Cast iron horizontal, includes motor/coupling/base. Size is raw flow-times-pressure product, not horsepower; graph scaling cancels in reference ratios. Conventional and inline curves have no printed exponent. No hydraulic sizing or pressure factors applied.",
        ),
    )
