"""DUCTS — GARRETT, PRINTED P. 278 / PDF P. 28

Historical USD per FOOT of duct, at 1/8 inch wall thickness.
D is diameter in inches: mild steel -2.22+1.66D; stainless -6.43+5.84D;
water cooled 79+6.78D. Printed size exponent 1.08.
No total length multiplication or wall-thickness factors are implicit.
"""

from .general import estimate_from_equation

EQUATIONS = {
    "mild_steel": (1.66, -2.22),
    "stainless": (5.84, -6.43),
    "water_cooled": (6.78, 79.0),
}


def estimate_cost(
    diameter_in: float, *, variant: str, valid_diameter_range: tuple[float, float]
):
    if variant not in EQUATIONS:
        raise ValueError("Unsupported duct variant")
    slope, intercept = EQUATIONS[variant]
    return estimate_from_equation(
        equipment="ducts",
        variant=variant,
        size=diameter_in,
        size_unit="in_duct_diameter",
        equation=lambda d: intercept + slope * d,
        formula=f"{intercept:g} + {slope:g} * D",
        valid_size_range=valid_diameter_range,
        exponent=1.08,
        printed_page=278,
        scope="duct_unit_price_per_ft",
        notes=(
            "Price per foot, NOT total duct cost. Multiply by reviewed duct length separately.",
            "1/8 inch wall basis; no wall-thickness adjustment applied.",
            "Nonpositive equation prices at reviewed bounds are rejected, not clipped.",
        ),
    )
