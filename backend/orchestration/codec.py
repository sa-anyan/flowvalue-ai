"""Strict, allowlisted construction of canonical dataclasses from JSON (never code)."""

import dataclasses
import types
import typing
from datetime import date
from decimal import Decimal, InvalidOperation


def plain(value):
    if dataclasses.is_dataclass(value):
        return {
            f.name: plain(getattr(value, f.name)) for f in dataclasses.fields(value)
        }
    if isinstance(value, (tuple, list)):
        return [plain(v) for v in value]
    if isinstance(value, dict):
        return {str(k): plain(v) for k, v in value.items()}
    if isinstance(value, (Decimal, date)):
        return str(value)
    return value


def construct(cls, value):
    """Only instantiate caller-selected types; reject extra fields and coercion surprises."""
    if cls is typing.Any or cls is object:
        return value
    origin, args = typing.get_origin(cls), typing.get_args(cls)
    if origin in (typing.Union, types.UnionType):
        if value is None and type(None) in args:
            return None
        for option in args:
            try:
                return construct(option, value)
            except (ValueError, TypeError, KeyError):
                pass
        raise ValueError("Value does not match declared alternatives")
    if cls is type(None):
        if value is not None:
            raise TypeError("Expected null")
        return None
    if origin is tuple:
        if not isinstance(value, (tuple, list)):
            raise TypeError("Expected array")
        if len(args) == 2 and args[1] is Ellipsis:
            return tuple(construct(args[0], x) for x in value)
        if len(value) != len(args):
            raise ValueError("Wrong tuple length")
        return tuple(construct(t, x) for t, x in zip(args, value))
    if origin is dict or cls is dict:
        if not isinstance(value, dict):
            raise TypeError("Expected object")
        return (
            {construct(args[0], k): construct(args[1], v) for k, v in value.items()}
            if args
            else value
        )
    if dataclasses.is_dataclass(cls):
        if not isinstance(value, dict):
            raise TypeError("Expected " + cls.__name__ + " object")
        fields = {f.name: f for f in dataclasses.fields(cls)}
        if set(value) - set(fields):
            raise ValueError("Unknown fields for " + cls.__name__)
        hints = typing.get_type_hints(cls)
        return cls(**{k: construct(hints[k], v) for k, v in value.items()})
    if cls is Decimal:
        if isinstance(value, bool):
            raise TypeError("Boolean is not a number")
        try:
            number = Decimal(str(value))
        except InvalidOperation as exc:
            raise ValueError("Finite numeric input required") from exc
        if not number.is_finite():
            raise ValueError("Finite number required")
        return number
    if cls is date:
        return date.fromisoformat(value)
    if cls in (int, bool, str):
        if type(value) is not cls:
            raise TypeError("Expected " + cls.__name__)
        return value
    if cls is float:
        return float(construct(Decimal, value))
    raise TypeError("Unsupported contract " + str(cls))
