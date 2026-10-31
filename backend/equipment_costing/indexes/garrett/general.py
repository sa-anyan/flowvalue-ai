"""GARRETT — GENERAL COST–SIZE SCALING

Garrett (1989), Chemical Engineering Economics, Appendix 1, printed p. 255,
PDF p. 5: C2 = C1 * (S2 / S1)**n.

This changes equipment SIZE at a fixed price-date/currency/configuration basis.
It is NOT inflation escalation, an absolute price correlation or the universal
six-tenths rule. A known C1/S1 and a supported, equipment-specific n are required.
"""

from collections.abc import Callable
from math import isfinite

from ...models import CostEstimate, ReferenceCost, positive

SOURCE_TITLE = "Donald E. Garrett, Chemical Engineering Economics (1989), Appendix 1"
SOURCE_FILENAME = (
    "Chemical Engineering Economics - Appendix 1 - Equipment Cost Estimates (1).pdf"
)
SOURCE_SHA256 = "720cca1e5e8927c4dc010812548953e622235dac0185f1d6d1f18eba4412ea51"


def estimate_from_equation(
    *,
    equipment: str,
    variant: str,
    size: float,
    size_unit: str,
    equation: Callable[[float], float],
    formula: str,
    valid_size_range: tuple[float, float],
    exponent: float,
    printed_page: int,
    scope: str = "purchased_equipment",
    notes: tuple[str, ...] = (),
) -> CostEstimate:
    """Historical direct equation with explicitly reviewed boundary anchors.

    The caller's interval is not a source-validated range. Never evaluate the
    equation at an out-of-range target. No graph-axis limits are assumed.
    """
    target = positive(size, "size")
    if not isinstance(valid_size_range, tuple) or len(valid_size_range) != 2:
        raise ValueError("A caller-reviewed (lower, upper) size interval is required")
    low, high = (positive(v, "size bound") for v in valid_size_range)
    if low > high:
        raise ValueError("Size interval is reversed")
    positive(exponent, "exponent")
    # Check endpoints as well: affine equations may yield nonphysical prices.
    positive(equation(low), "lower boundary cost")
    positive(equation(high), "upper boundary cost")
    anchor = min(max(target, low), high)
    anchor_cost = positive(equation(anchor), "equation cost")
    extrapolated = target != anchor
    amount = (
        scale_cost(anchor_cost, anchor, target, exponent)
        if extrapolated
        else anchor_cost
    )
    return CostEstimate(
        equipment=equipment,
        variant=variant,
        amount=amount,
        currency="USD",
        cost_index=320,
        period="early 1987",
        size=target,
        size_unit=size_unit,
        cost_scope=scope,
        formula=f"C_anchor * (S / S_anchor)**n; anchor equation: {formula}"
        if extrapolated
        else formula,
        printed_page=printed_page,
        pdf_page=printed_page - 250,
        source_title=SOURCE_TITLE,
        source_filename=SOURCE_FILENAME,
        source_sha256=SOURCE_SHA256,
        exponent=exponent,
        extrapolated=extrapolated,
        anchor_size=anchor if extrapolated else None,
        anchor_cost=anchor_cost if extrapolated else None,
        exponent_basis="printed exponent extended as an unvalidated extrapolation assumption"
        if extrapolated
        else "direct equation; printed size exponent retained",
        notes=(
            "Caller-reviewed interval is not a textbook-validated applicability range.",
            "No inflation, installation, material or pressure adjustments applied.",
            *(
                ("EXTRAPOLATED from nearest boundary; accuracy is unvalidated.",)
                if extrapolated
                else ()
            ),
            *notes,
        ),
    )


def scale_cost(
    reference_cost: float, reference_size: float, target_size: float, exponent: float
) -> float:
    c1 = positive(reference_cost, "reference_cost")
    s1 = positive(reference_size, "reference_size")
    s2 = positive(target_size, "target_size")
    if (
        isinstance(exponent, bool)
        or not isinstance(exponent, (int, float))
        or not isfinite(exponent)
    ):
        raise ValueError("exponent must be finite")
    try:
        amount = c1 * (s2 / s1) ** exponent
    except (OverflowError, ZeroDivisionError) as exc:
        raise ValueError("Scaling exceeds numerical limits") from exc
    return positive(amount, "scaled cost")


def estimate_from_reference(
    *,
    equipment: str,
    variant: str,
    target_size: float,
    reference: ReferenceCost,
    exponent: float,
    size_unit: str,
    printed_page: int,
    scope: str = "purchased_equipment",
    source_range: tuple[float, float] | None = None,
    notes: tuple[str, ...] = (),
) -> CostEstimate:
    positive(target_size, "target_size")
    if (
        reference.equipment,
        reference.variant,
        reference.size_unit,
        reference.cost_scope,
    ) != (equipment, variant, size_unit, scope):
        raise ValueError(
            "Reference equipment/variant/size unit/cost scope does not match this method"
        )
    low, high = reference.valid_size_range
    if source_range:
        low, high = max(low, source_range[0]), min(high, source_range[1])
    if low > high or not low <= reference.size <= high:
        raise ValueError("Reference must lie within the usable reference/source range")
    anchor = min(max(target_size, low), high)
    anchor_cost = scale_cost(reference.amount, reference.size, anchor, exponent)
    extrapolated = target_size != anchor
    amount = scale_cost(anchor_cost, anchor, target_size, exponent)
    return CostEstimate(
        equipment=equipment,
        variant=variant,
        amount=amount,
        extrapolated=extrapolated,
        exponent_basis="printed size exponent extended beyond the usable range as an extrapolation assumption"
        if extrapolated
        else "printed size exponent",
        anchor_size=anchor if extrapolated else None,
        anchor_cost=anchor_cost if extrapolated else None,
        currency=reference.currency,
        cost_index=reference.cost_index,
        period=reference.period,
        size=target_size,
        size_unit=size_unit,
        cost_scope=scope,
        formula="C2 = C1 * (S2 / S1)**n",
        printed_page=printed_page,
        pdf_page=printed_page - 250,
        source_title=SOURCE_TITLE,
        source_filename=SOURCE_FILENAME,
        source_sha256=SOURCE_SHA256,
        exponent=exponent,
        reference=reference,
        notes=(
            "Preliminary reference-price scaling; no graph price was digitized.",
            "Price date/index/currency and configuration remain those of the supplied reference.",
            "Caller-declared size limits are not independently validated applicability ranges.",
            "No automatic material, pressure, installation or module-factor adjustments.",
            *(
                (
                    "EXTRAPOLATED beyond the usable size range using a boundary anchor; accuracy is unvalidated.",
                )
                if extrapolated
                else ()
            ),
            *notes,
        ),
    )
