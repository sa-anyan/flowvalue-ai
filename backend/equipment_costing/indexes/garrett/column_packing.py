"""COLUMN PACKING — GARRETT, PRINTED P. 270 / PDF P. 20

UNIT PRICE PER ft3 OF PACKING, not total purchase cost. Size means nominal packing-piece size in inches, not packed volume or column diameter. Negative exponents intentionally reduce unit price as nominal packing size rises. Do not add this result directly to CAPEX.
Printed size exponent(s) only: a documented comparable reference price is required.
Out-of-range targets use nearest-boundary anchors and are explicitly flagged.
"""

from ...models import ReferenceCost
from .general import estimate_from_reference

VARIANTS = {
    "berl_saddles_porcelain": (-1.16, "in_nominal_packing_size"),
    "pall_rings_stainless": (-0.64, "in_nominal_packing_size"),
    "pall_rings_polypropylene": (-0.95, "in_nominal_packing_size"),
    "interlox_saddles_porcelain": (-0.4, "in_nominal_packing_size"),
    "interlox_saddles_polypropylene": (-0.95, "in_nominal_packing_size"),
    "raschig_rings_porcelain": (-0.5, "in_nominal_packing_size"),
}
SOURCE_RANGE = None


def estimate_cost(target_size: float, reference: ReferenceCost):
    if reference.variant not in VARIANTS:
        raise ValueError(
            "Unsupported column_packing variant; no formula or exponent will be invented"
        )
    exponent, size_unit = VARIANTS[reference.variant]
    return estimate_from_reference(
        equipment="column_packing",
        variant=reference.variant,
        target_size=target_size,
        reference=reference,
        exponent=exponent,
        size_unit=size_unit,
        printed_page=270,
        scope="packing_unit_price_per_ft3",
        source_range=SOURCE_RANGE,
        notes=(
            "UNIT PRICE PER ft3 OF PACKING, not total purchase cost. Size means nominal packing-piece size in inches, not packed volume or column diameter. Negative exponents intentionally reduce unit price as nominal packing size rises. Do not add this result directly to CAPEX.",
        ),
    )
