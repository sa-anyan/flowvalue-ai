"""Typed units, source measurements and auditable conversion results."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class UnitDefinition:
    symbol: str
    quantity: str
    factor: float
    offset: float = 0.0
    pressure_basis: str | None = None


@dataclass(frozen=True)
class ConversionContext:
    input_gallon_basis: str | None = None
    target_gallon_basis: str | None = None
    input_ton_basis: str | None = None
    target_ton_basis: str | None = None
    input_pressure_basis: str | None = None
    target_pressure_basis: str | None = None
    atmospheric_pressure_pa: float | None = None
    input_gas_reference: str | None = None
    target_gas_reference: str | None = None
    btu_basis: str | None = None


@dataclass(frozen=True)
class Measurement:
    value: float
    unit: str
    source: dict[str, Any] = field(default_factory=dict)
    pressure_basis: str | None = None


@dataclass(frozen=True)
class ConversionResult:
    status: str
    original: Measurement
    target_unit: str
    value: float | None
    quantity: str | None
    canonical_input_unit: str | None
    canonical_target_unit: str | None
    pressure_basis: str | None
    assumptions: tuple[str, ...] = ()
    issues: tuple[str, ...] = ()
    reference: str = "NIST SP 811 Appendix B; definitions and limitations in unit_conversion/README.md"


@dataclass(frozen=True)
class InputRequirement:
    name: str
    quantity: str
    target_unit: str | None
    required: bool = True
    role: str = "cost model size"
    issue: str | None = None


@dataclass(frozen=True)
class ResolvedInputs:
    status: str
    values: dict[str, float]
    conversions: dict[str, ConversionResult]
    issues: tuple[str, ...]
