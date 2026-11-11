"""Finite engineering inputs; no silent defaults or dimensional substitutions."""

from math import isfinite


def positive(value, name, zero=False):
    if isinstance(value, bool):
        raise ValueError(name + " cannot be boolean")  # noqa: TRY004 -- uniform engineering validation
    try:
        value = float(value)
    except (ValueError, TypeError):
        raise ValueError(name + " is required") from None
    if not isfinite(value) or (value < 0 if zero else value <= 0):
        raise ValueError(
            name + " must be finite and " + ("nonnegative" if zero else "positive")
        )
    return value
