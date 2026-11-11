"""Finite engineering inputs; no silent defaults or dimensional substitutions."""

from math import isfinite


def reject_boolean(value, name):
    """Reject Boolean semantics before coercion, without importing NumPy.

    NumPy and compatible Boolean dtypes advertise kind "b". Numeric integer and
    floating scalar dtypes retain their existing handling in the caller.
    """
    boolean_dtype = getattr(getattr(value, "dtype", None), "kind", None) == "b"
    if isinstance(value, bool) or boolean_dtype:
        raise ValueError(
            name + " cannot be boolean"
        )  # noqa: TRY004 -- uniform engineering validation


def positive(value, name, zero=False):
    reject_boolean(value, name)
    try:
        value = float(value)
    except (ValueError, TypeError):
        raise ValueError(name + " is required") from None
    if not isfinite(value) or (value < 0 if zero else value <= 0):
        raise ValueError(
            name + " must be finite and " + ("nonnegative" if zero else "positive")
        )
    return value
