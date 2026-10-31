"""ACTIVATED CARBON ADSORBERS — GARRETT, PRINTED P. 256 / PDF P. 6

Mild steel, including instruments and controls. Wc is carbon weight in lb,
NOT the chart's displayed thousands of lb. Prices are USD, early 1987,
CE Index 320. Source prints strict bounds and leaves Wc=10,000 unassigned;
10,000 lb remains ambiguous and is rejected. Outer limits can be evaluated as
anchors for explicit, flagged extrapolation. Formula powers used outside the
range are extrapolation assumptions, not source-validated cost-size exponents.
"""

from ...models import CostEstimate, positive
from .general import SOURCE_FILENAME, SOURCE_SHA256, SOURCE_TITLE, scale_cost


def estimate_cost(
    carbon_weight_lb: float, *, extrapolation_exponent: float | None = None
) -> CostEstimate:
    w = positive(carbon_weight_lb, "carbon_weight_lb")
    extrapolated = w <= 250 or w >= 200000
    anchor = None
    anchor_cost = None
    exponent = None
    if 250 < w < 10000:
        amount = 15200 + 1100 * w**0.481
        formula = "15200 + 1100 * Wc**0.481"
    elif 10000 < w < 200000:
        amount = 76200 + 0.422 * w**1.2
        formula = "76200 + 0.422 * Wc**1.2"
    elif extrapolated:
        anchor = 250.0 if w <= 250 else 200000.0
        anchor_cost = (
            (15200 + 1100 * anchor**0.481)
            if w <= 250
            else (76200 + 0.422 * anchor**1.2)
        )
        exponent = (
            extrapolation_exponent
            if extrapolation_exponent is not None
            else (0.481 if w <= 250 else 1.2)
        )
        positive(exponent, "extrapolation_exponent")
        amount = scale_cost(anchor_cost, anchor, w, exponent)
        formula = "C_boundary * (Wc / W_boundary)**n"
    else:
        raise ValueError(
            "Wc=10000 lb is ambiguous between two printed branches; provide a reviewed method"
        )
    return CostEstimate(
        equipment="activated_carbon_adsorbers",
        variant="mild_steel",
        amount=positive(amount, "cost"),
        currency="USD",
        cost_index=320,
        period="early 1987",
        size=w,
        size_unit="lb_carbon",
        cost_scope="purchased_equipment",
        formula=formula,
        source_title=SOURCE_TITLE,
        source_filename=SOURCE_FILENAME,
        source_sha256=SOURCE_SHA256,
        printed_page=256,
        pdf_page=6,
        exponent=exponent,
        extrapolated=extrapolated,
        anchor_size=anchor,
        anchor_cost=anchor_cost,
        exponent_basis=(
            "user-supplied extrapolation exponent"
            if extrapolation_exponent is not None
            else "assumed from power term of boundary equation, not a validated overall cost exponent"
        )
        if extrapolated
        else "direct equation",
        notes=(
            "Mild steel construction, including instruments and controls.",
            "Historical preliminary equipment estimate, not today's quotation.",
            "No installation/module/material/pressure uplift applied.",
            *(
                (
                    "EXTRAPOLATED: outer equation evaluated at its limiting boundary as an anchor; no out-of-range correlation evaluation.",
                    "Exponent is an explicit extrapolation assumption; the additive intercept means it is not the exact overall cost elasticity.",
                )
                if extrapolated
                else ()
            ),
        ),
    )
