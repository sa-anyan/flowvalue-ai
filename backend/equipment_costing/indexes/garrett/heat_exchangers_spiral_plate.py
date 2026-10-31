"""SPIRAL / PLATE-AND-FRAME EXCHANGERS — GARRETT, P. 287 / PDF P. 37

Standalone historical USD purchase-price equations, A in actual ft2:
spiral plate C=660*A**0.59; plate and frame C=100*A**0.78.
304 stainless steel, no insulation. Early 1987, CE Index 320.
The currency symbol is not a multiplier; the chart's $1000 axis does not
multiply these dollar equations by another thousand.
"""

from .general import estimate_from_equation

EQUATIONS = {"spiral_plate": (660.0, 0.59), "plate_and_frame": (100.0, 0.78)}


def estimate_cost(
    area_ft2: float, *, variant: str, valid_area_range: tuple[float, float]
):
    if variant not in EQUATIONS:
        raise ValueError("Unsupported spiral/plate exchanger variant")
    coefficient, exponent = EQUATIONS[variant]
    return estimate_from_equation(
        equipment="heat_exchangers_spiral_plate",
        variant=variant,
        size=area_ft2,
        size_unit="ft2_heat_transfer_area",
        equation=lambda a: coefficient * a**exponent,
        formula=f"{coefficient:g} * A**{exponent:g}",
        valid_size_range=valid_area_range,
        exponent=exponent,
        printed_page=287,
        notes=(
            "304 stainless steel; no insulation or installation included.",
            "Input is actual heat-transfer area in ft2.",
        ),
    )
