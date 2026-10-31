"""Shared conversion API; equipment-specific requirements stay with their models."""

from .models import (
    ConversionContext,
    ConversionResult,
    InputRequirement,
    Measurement,
    ResolvedInputs,
)
from .unit_conversion import UnitResolutionError, convert, identify_unit, resolve_inputs

__all__ = [
    "ConversionContext",
    "ConversionResult",
    "InputRequirement",
    "Measurement",
    "ResolvedInputs",
    "UnitResolutionError",
    "convert",
    "identify_unit",
    "resolve_inputs",
]
