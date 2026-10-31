"""AGITATORS — GARRETT, PRINTED P. 257 / PDF P. 7

Turbine: dual blades, mild steel, 30–45 rpm, motor/reducer/shaft.
Propeller: mild steel, single blade. Scaling across exponent bands is blocked.
"""

from ...models import ReferenceCost
from .general import estimate_from_reference


def estimate_cost(target_hp: float, reference: ReferenceCost):
    sizes = (reference.size, target_hp)
    if reference.variant == "turbine":
        if all(0 < s < 4 for s in sizes):
            n = 0.23
        elif all(4 <= s <= 30 for s in sizes):
            n = 0.56
        elif all(s > 30 for s in sizes):
            n = 0.68
        else:
            raise ValueError(
                "Cross-band turbine scaling requires another reference or a reviewed piecewise method"
            )
    elif reference.variant == "propeller":
        if all(1 <= s <= 3 for s in sizes):
            n = 0.42
        elif all(3 <= s <= 100 for s in sizes):
            n = 0.51
        else:
            raise ValueError(
                "Propeller scaling is limited to a single printed 1–3 or 3–100 hp band"
            )
    else:
        raise ValueError(
            "Choose turbine or propeller; tag letters do not select a subtype"
        )
    return estimate_from_reference(
        equipment="agitators",
        variant=reference.variant,
        target_size=target_hp,
        reference=reference,
        exponent=n,
        size_unit="hp",
        printed_page=257,
        notes=(
            "Reference must match the source blade, speed and drive configuration.",
            "No automatic crossing of printed exponent bands.",
        ),
    )
