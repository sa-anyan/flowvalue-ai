"""Sharma/WaterTAP 1.8.0 native construction polynomials; no implicit TIC/escalation."""

from ...models import positive

COEFFICIENTS = {
    "circular": (-0.0006, 98.952, 191806.0),
    "rectangular": (-0.0029, 169.19, 94365.0),
}


def calculate(area_ft2, geometry, *, allow_unverified=False):
    area = positive(area_ft2, "clarifier area ft2")
    a, b, c = COEFFICIENTS[geometry]
    if 2 * a * area + b <= 0 or a * area * area + b * area + c <= 0:
        raise ValueError(
            "MODEL_OUT_OF_RANGE: descending/nonpositive quadratic regime; not a valid extrapolation"
        )
    if allow_unverified is not True:
        raise ValueError(
            "MODEL_APPLICABILITY_UNVERIFIED: published area range not verified. Explicit allow_unverified=True required for a provisional scenario; monotonicity is not source validation"
        )
    return a * area * area + b * area + c
