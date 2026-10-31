"""COOLERS / QUENCHERS — GARRETT, PRINTED P. 274 / PDF P. 24

Standalone purchased-cost equations (early-1987 USD, CE Index 320):
spray chamber: 358 * Q + 65000; quencher: 335 * Q + 12200.
Q is inlet flow in THOUSANDS of cfm according to the chart's flow axis.
The printed '$(' symbol is a currency symbol, NOT a multiplier of five.
The equation abbreviates flow as M scf; standard/actual reference conditions
are not resolved here. Supply flow at a reviewed, consistent source basis.
Cascade cooler and dilution-air-port curves are graph-only and unsupported.
"""

from ...models import CostEstimate, positive
from .general import SOURCE_FILENAME, SOURCE_SHA256, SOURCE_TITLE, scale_cost

EQUATIONS = {"spray_chamber": (358.0, 65000.0), "quencher": (335.0, 12200.0)}


def estimate_cost(
    inlet_flow_1000_cfm: float,
    *,
    variant: str,
    valid_flow_range: tuple[float, float],
    extrapolation_exponent: float = 1.0,
) -> CostEstimate:
    """Caller-reviewed flow interval required: no source validity limits are printed.

    Outside that interval, the boundary price is calculated from the equation,
    then scaled. Default n=1 is a disclosed linear-term assumption, NOT the
    exact elasticity of the affine cost equation or a printed size exponent.
    """
    q = positive(inlet_flow_1000_cfm, "inlet_flow_1000_cfm")
    if variant not in EQUATIONS:
        raise ValueError(
            "Only spray_chamber and quencher have supported price equations"
        )
    if not isinstance(valid_flow_range, tuple) or len(valid_flow_range) != 2:
        raise ValueError("A caller-reviewed (lower, upper) flow interval is required")
    low, high = valid_flow_range
    positive(low, "lower flow bound")
    positive(high, "upper flow bound")
    if low > high:
        raise ValueError("Flow interval is reversed")
    positive(extrapolation_exponent, "extrapolation_exponent")
    slope, intercept = EQUATIONS[variant]
    anchor = min(max(q, low), high)
    anchor_cost = slope * anchor + intercept
    extrapolated = q != anchor
    amount = (
        scale_cost(anchor_cost, anchor, q, extrapolation_exponent)
        if extrapolated
        else anchor_cost
    )
    return CostEstimate(
        equipment="coolers_quenchers",
        variant=variant,
        amount=positive(amount, "cost"),
        currency="USD",
        cost_index=320,
        period="early 1987",
        size=q,
        size_unit="1000_cfm_inlet",
        cost_scope="purchased_equipment",
        formula="C_boundary * (Q / Q_boundary)**n"
        if extrapolated
        else f"{slope:g} * Q + {intercept:g}",
        printed_page=274,
        pdf_page=24,
        source_title=SOURCE_TITLE,
        source_filename=SOURCE_FILENAME,
        source_sha256=SOURCE_SHA256,
        exponent=extrapolation_exponent if extrapolated else None,
        extrapolated=extrapolated,
        anchor_size=anchor if extrapolated else None,
        anchor_cost=anchor_cost if extrapolated else None,
        exponent_basis="caller-supplied or default linear-term extrapolation assumption"
        if extrapolated
        else "direct equation",
        notes=(
            "Mild steel; no installation/module/material adjustments.",
            "Caller-reviewed flow bounds are not a textbook-validated range.",
            "No automatic standard/actual inlet-flow conversion.",
            *(
                ("EXTRAPOLATED from a boundary price; accuracy is unvalidated.",)
                if extrapolated
                else ()
            ),
        ),
    )
