"""HEAT EXCHANGERS SHELL TUBE — GARRETT, PRINTED P. 286 / PDF P. 36

Printed size exponents, not standalone price equations.
A documented comparable reference price is mandatory.
Mild steel. Shell-and-tube reference basis: floating head, 150 psig, 3/4 x 1 inch square pitch, 16 ft tubes. Input is actual outside area in ft2, not the differently scaled graph coordinates. No type/material/pressure factor is applied.
"""

from ...models import ReferenceCost
from .general import estimate_from_reference

VARIANTS = {
    "shell_and_tube": (0.68, "ft2_outside_heat_transfer_area"),
    "double_pipe": (0.68, "ft2_outside_heat_transfer_area"),
    "air_cooled": (0.39, "ft2_outside_heat_transfer_area"),
}


def estimate_cost(target_size: float, reference: ReferenceCost):
    if reference.variant not in VARIANTS:
        raise ValueError(
            "Unsupported heat_exchangers_shell_tube variant; no exponent will be invented"
        )
    exponent, unit = VARIANTS[reference.variant]
    return estimate_from_reference(
        equipment="heat_exchangers_shell_tube",
        variant=reference.variant,
        target_size=target_size,
        reference=reference,
        exponent=exponent,
        size_unit=unit,
        printed_page=286,
        notes=(
            "Mild steel. Shell-and-tube reference basis: floating head, 150 psig, 3/4 x 1 inch square pitch, 16 ft tubes. Input is actual outside area in ft2, not the differently scaled graph coordinates. No type/material/pressure factor is applied.",
        ),
    )
