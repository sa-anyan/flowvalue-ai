"""Finite engineering inputs; no silent defaults or dimensional substitutions."""

from math import isfinite


class SizingError(ValueError):
    """Base for sizing failures. Subclasses ValueError so existing callers still catch it.

    `kind` gives each failure a machine-readable state (roadmap milestone M1.4),
    so a missing input is never reported the same way as an invalid one.
    """

    kind = "invalid_input"


class MissingInputError(SizingError):
    kind = "missing_input"


class InvalidInputError(SizingError):
    kind = "invalid_input"


class UnsupportedMethodError(SizingError):
    kind = "unsupported_method"


def failure_kind(error):
    """State for any exception raised by sizing: missing, invalid or unsupported."""
    return getattr(error, "kind", "invalid_input")


def reject_boolean(value, name):
    """Reject Boolean semantics before coercion, without importing NumPy.

    NumPy and compatible Boolean dtypes advertise kind "b". Numeric integer and
    floating scalar dtypes retain their existing handling in the caller.
    """
    boolean_dtype = getattr(getattr(value, "dtype", None), "kind", None) == "b"
    if isinstance(value, bool) or boolean_dtype:
        raise InvalidInputError(
            name + " cannot be boolean"
        )  # noqa: TRY004 -- uniform engineering validation


def positive(value, name, zero=False):
    reject_boolean(value, name)
    if value is None:
        raise MissingInputError(name + " is required")
    try:
        value = float(value)
    except (ValueError, TypeError):
        raise InvalidInputError(name + " is required") from None
    if not isfinite(value) or (value < 0 if zero else value <= 0):
        raise InvalidInputError(
            name + " must be finite and " + ("nonnegative" if zero else "positive")
        )
    return value
