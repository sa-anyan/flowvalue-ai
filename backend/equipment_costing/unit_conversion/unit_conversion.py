"""Shared dimensional conversion; no equipment sizing or curve selection."""

import copy
import math
import re
from dataclasses import replace

from .models import ConversionContext, ConversionResult, Measurement
from .unit_aliases import ALIASES, UNITS, WORDS, key


class UnitResolutionError(ValueError):
    """Conversion requires missing/ambiguous engineering information."""


def _definition(unit, context, role, assumptions):
    name = key(unit).replace(" per ", "/")
    if name in ALIASES:
        return UNITS[ALIASES[name]]
    if name.lower() in WORDS:
        return UNITS[WORDS[name.lower()]]
    # Exact bounded scale prefix, never eval/exec or dimensional inference.
    scaled = re.fullmatch(r"(1000|1,000|10|million)\s+(.+)", name)
    if scaled:
        factor = {"1000": 1000, "1,000": 1000, "10": 10, "million": 1e6}[scaled[1]]
        base = _definition(scaled[2], context, role, assumptions)
        if base.offset:
            raise UnitResolutionError("Scaled absolute temperatures are unsupported")
        return replace(
            base, symbol=f"{factor:g} {base.symbol}", factor=base.factor * factor
        )
    if name.lower() in ["ton", "tons", "t"]:
        basis = getattr(context, f"{role}_ton_basis")
        choices = {
            "metric": "tonne",
            "short": "short_ton",
            "long": "long_ton",
            "refrigeration": "refrigeration_ton",
        }
        if basis not in choices:
            raise UnitResolutionError(
                "Ambiguous ton: specify metric, short, long or refrigeration basis"
            )
        assumptions.append(f"{role} ton interpreted as {basis}, explicitly supplied")
        return UNITS[choices[basis]]
    if name.lower() in ["gal", "gallon", "gallons", "gpm", "gpm_psi"]:
        basis = getattr(context, f"{role}_gallon_basis")
        if basis not in ["US", "Imperial"]:
            raise UnitResolutionError(
                "Ambiguous gallon: specify US or Imperial basis for " + role
            )
        assumptions.append(f"{role} gallon interpreted as {basis}, explicitly supplied")
        symbol = (
            ("US_gpm_psi" if basis == "US" else "Imp_gpm_psi")
            if name.lower() == "gpm_psi"
            else (
                ("US_gpm" if basis == "US" else "Imp_gpm")
                if name.lower() == "gpm"
                else ("US_gal" if basis == "US" else "Imp_gal")
            )
        )
        return UNITS[symbol]
    if name in ["Btu", "BTU", "btu"]:
        if context.btu_basis not in ["IT", "thermochemical"]:
            raise UnitResolutionError(
                "Ambiguous Btu: specify IT or thermochemical basis"
            )
        assumptions.append("Btu basis explicitly supplied: " + context.btu_basis)
        return UNITS["Btu_IT" if context.btu_basis == "IT" else "Btu_th"]
    if name.count("/") == 1:
        numerator, denominator = name.split("/")
        time = {
            "s": "s",
            "sec": "s",
            "second": "s",
            "seconds": "s",
            "min": "min",
            "minute": "min",
            "minutes": "min",
            "h": "h",
            "hr": "h",
            "hour": "h",
            "hours": "h",
            "d": "day",
            "day": "day",
            "days": "day",
        }.get(denominator.strip().lower())
        if time:
            base = _definition(numerator.strip(), context, role, assumptions)
            candidate = f"{base.symbol}/{time}"
            if candidate in UNITS:
                return UNITS[candidate]
    raise UnitResolutionError("Unsupported or unrecognized unit: " + unit)


def identify_unit(unit, *, context=None, role="input"):
    if role not in ["input", "target"]:
        raise ValueError("role must be input or target")
    return _definition(unit, context or ConversionContext(), role, [])


def convert(
    value, from_unit, to_unit, *, context=None, source=None, pressure_basis=None
):
    """Convert numeric measurements, returning issues instead of fabricated values.

    Gauge/absolute changes require an explicitly supplied local atmospheric
    pressure. Standard-gas reference changes and actual/standard conversion are
    deliberately unsupported (thermodynamic information is required).
    """
    context = context or ConversionContext()
    if not isinstance(context, ConversionContext):
        raise TypeError("context must be ConversionContext")
    original = Measurement(
        value, from_unit, copy.deepcopy(source or {}), pressure_basis
    )
    assumptions = []
    a = b = None
    try:
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
        ):
            raise UnitResolutionError("Value must be a finite number, not a boolean")
        a = _definition(from_unit, context, "input", assumptions)
        b = _definition(to_unit, context, "target", assumptions)
        if a.quantity != b.quantity:
            raise UnitResolutionError(
                f"Incompatible quantities: {a.quantity} and {b.quantity}; conversion cannot perform sizing or thermodynamics"
            )
        if a.quantity == "standard_volume_flow":
            if not context.input_gas_reference or not context.target_gas_reference:
                raise UnitResolutionError(
                    "Standard/normal gas conversion requires explicit input and target reference conditions"
                )
            if context.input_gas_reference != context.target_gas_reference:
                raise UnitResolutionError(
                    "Changing gas reference conditions needs a separate thermodynamic calculation"
                )
            assumptions.append(
                "Identical gas reference conditions explicitly supplied: "
                + context.input_gas_reference
            )
        si = value * a.factor + a.offset
        if a.symbol == "degF":
            # Origin form avoids a negative rounding residue at -459.67 F.
            si = (value + 459.67) * a.factor
        result_basis = None
        if a.quantity == "pressure":
            declared = [
                x
                for x in [
                    a.pressure_basis,
                    pressure_basis,
                    context.input_pressure_basis,
                ]
                if x is not None
            ]
            if any(x not in ["gauge", "absolute"] for x in declared):
                raise UnitResolutionError("Pressure basis must be gauge or absolute")
            if len(set(declared)) > 1:
                raise UnitResolutionError("Conflicting input pressure bases")
            input_basis = declared[0] if declared else None
            if context.target_pressure_basis not in [None, "gauge", "absolute"]:
                raise UnitResolutionError(
                    "Target pressure basis must be gauge or absolute"
                )
            if (
                b.pressure_basis
                and context.target_pressure_basis
                and b.pressure_basis != context.target_pressure_basis
            ):
                raise UnitResolutionError("Conflicting target pressure bases")
            result_basis = (
                b.pressure_basis or context.target_pressure_basis or input_basis
            )
            if input_basis is None and result_basis is not None:
                raise UnitResolutionError("Input pressure basis is missing")
            if input_basis == "absolute" and si < 0:
                raise UnitResolutionError("Absolute pressure cannot be negative")
            if result_basis != input_basis:
                atm = context.atmospheric_pressure_pa
                if (
                    isinstance(atm, bool)
                    or not isinstance(atm, (int, float))
                    or not math.isfinite(atm)
                    or atm <= 0
                ):
                    raise UnitResolutionError(
                        "Gauge/absolute conversion requires explicit positive atmospheric_pressure_pa"
                    )
                absolute = si + atm if input_basis == "gauge" else si
                if absolute < 0:
                    raise UnitResolutionError(
                        "Gauge pressure implies negative absolute pressure"
                    )
                si = absolute - atm if result_basis == "gauge" else absolute
                assumptions.append(
                    f"Explicit atmospheric pressure {atm:g} Pa used for gauge/absolute conversion"
                )
            if input_basis is None:
                assumptions.append(
                    "Pressure basis unspecified; units converted without changing reference basis"
                )
        elif a.quantity == "temperature" and si < 0:
            raise UnitResolutionError("Temperature is below absolute zero")
        elif (
            a.quantity
            not in [
                "temperature",
                "temperature_difference",
                "power",
                "energy",
                "mass_flow",
                "volume_flow",
                "molar_flow",
                "standard_volume_flow",
            ]
            and value < 0
        ):
            raise UnitResolutionError("Negative value is invalid for this quantity")
        converted = (si - b.offset) / b.factor
        if not math.isfinite(converted):
            raise UnitResolutionError("Converted value exceeds numerical limits")
        return ConversionResult(
            "converted",
            original,
            to_unit,
            converted,
            a.quantity,
            a.symbol,
            b.symbol,
            result_basis,
            tuple(assumptions),
        )
    except (ValueError, OverflowError) as exc:
        return ConversionResult(
            "unresolved",
            original,
            to_unit,
            None,
            a.quantity if a else None,
            a.symbol if a else None,
            b.symbol if b else None,
            None,
            tuple(assumptions),
            (str(exc),),
        )


def resolve_inputs(requirements, measurements, *, context=None):
    """Match explicit field names only. Operating pressure never fills design pressure."""
    from .models import ResolvedInputs

    values = {}
    conversions = {}
    issues = []
    for requirement in requirements:
        measurement = measurements.get(requirement.name)
        if measurement is None:
            if requirement.required:
                issues.append("Missing required input: " + requirement.name)
            continue
        if not isinstance(measurement, Measurement):
            issues.append(
                requirement.name + ": expected a Measurement with value/unit/source"
            )
            continue
        if requirement.issue or requirement.target_unit is None:
            issues.append(
                requirement.name
                + ": "
                + (requirement.issue or "No supported target unit")
            )
            continue
        result = convert(
            measurement.value,
            measurement.unit,
            requirement.target_unit,
            context=context,
            source=measurement.source,
            pressure_basis=measurement.pressure_basis,
        )
        conversions[requirement.name] = result
        if result.status == "converted" and result.quantity == requirement.quantity:
            values[requirement.name] = result.value
        else:
            issues.append(
                requirement.name
                + ": "
                + ("; ".join(result.issues) or "Input has the wrong physical quantity")
            )
    return ResolvedInputs(
        "resolved" if not issues else "needs_review", values, conversions, tuple(issues)
    )
