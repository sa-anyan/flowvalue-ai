"""Explicit same-series cost-index ratio. No index feed or current default."""

from ..models import positive
from .cost_translation import indexed_amount


def adjust_cost(
    amount,
    *,
    base_index,
    target_index,
    base_series,
    target_series,
    target_period,
    target_source,
):
    if not base_series or base_series != target_series:
        raise ValueError("Base and target indices must use the same named series")
    if not isinstance(target_period, str) or not target_period.strip():
        raise ValueError("Target index period is required")
    if not isinstance(target_source, str) or not target_source.strip():
        raise ValueError("Target index source is required")
    return positive(
        float(
            indexed_amount(
                positive(amount, "amount"),
                base_index=positive(base_index, "base index"),
                target_index=positive(target_index, "target index"),
            )
        ),
        "adjusted amount",
    )
