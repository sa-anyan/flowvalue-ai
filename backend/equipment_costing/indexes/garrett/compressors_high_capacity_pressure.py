"""COMPRESSORS HIGH CAPACITY PRESSURE — GARRETT, PRINTED P. 272 / PDF P. 22

Source construction: steel, electric motor drive, gear reducer, 1,000 psi basis. Printed isothermal HP equation is a power calculation, NOT an absolute cost equation; this method requires supplied horsepower and comparable cost. No pressure/gas/driver conversion is inferred.
Printed size exponent(s) only: a documented comparable reference price is required.
Out-of-range targets use nearest-boundary anchors and are explicitly flagged.
"""

from ...models import ReferenceCost
from .general import estimate_from_reference

VARIANTS = {"centrifugal": (0.8, "hp"), "reciprocating": (0.8, "hp")}
SOURCE_RANGE = None


def estimate_cost(target_size: float, reference: ReferenceCost):
    if reference.variant not in VARIANTS:
        raise ValueError(
            "Unsupported compressors_high_capacity_pressure variant; no formula or exponent will be invented"
        )
    exponent, size_unit = VARIANTS[reference.variant]
    return estimate_from_reference(
        equipment="compressors_high_capacity_pressure",
        variant=reference.variant,
        target_size=target_size,
        reference=reference,
        exponent=exponent,
        size_unit=size_unit,
        printed_page=272,
        scope="purchased_equipment",
        source_range=SOURCE_RANGE,
        notes=(
            "Source construction: steel, electric motor drive, gear reducer, 1,000 psi basis. Printed isothermal HP equation is a power calculation, NOT an absolute cost equation; this method requires supplied horsepower and comparable cost. No pressure/gas/driver conversion is inferred.",
        ),
    )
