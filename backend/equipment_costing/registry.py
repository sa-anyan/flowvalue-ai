"""Canonical Python entry point for costing, with explicit source selection."""

from .indexes.openpytea.registry import (
    list_models as _openpytea_models,
    get_model as _openpytea_model,
)
from .indexes.openpytea.adapter import estimate_cost as _openpytea_cost


from .indexes.additional_models.registry import (
    list_models as _additional_models,
    estimate_cost as _additional_cost,
)

import copy
from dataclasses import asdict, replace
from functools import lru_cache
from math import isclose

from .indexes.nottingham.model import (
    estimate_cost as _nottingham_cost,
    list_models as _nottingham_models,
)
from .indexes.garrett.input_requirements import input_requirements
from .indexes.garrett.integrated import estimate_cost as _garrett_cost
from .indexes.garrett.integrated import list_factors, list_models
from .indexes.garrett.pressure_adjustment import (
    PressureAdjustment,
    list_pressure_methods,
)
from .unit_conversion import (
    ConversionContext,
    Measurement,
    InputRequirement,
    UnitResolutionError,
    convert,
    resolve_inputs,
)


@lru_cache(maxsize=1)
def _model_index():
    models = list_models()
    for model in models:
        model["input_requirements"] = [asdict(r) for r in input_requirements(model)]
    return {m["id"]: m for m in models}


def _not_found(curve_id):
    raise ValueError("Unknown Nottingham model: " + curve_id)


def model_source(model_id, fallback="garrett"):
    if str(model_id).startswith("openpytea:"):
        return "openpytea"
    if model_id in {m["id"] for m in _additional_models()}:
        return "additional_models"
    if str(model_id).startswith("N501-"):
        return "nottingham"
    return fallback


def _model(curve_id, source):
    source = model_source(curve_id, source)
    if source == "openpytea":
        return _openpytea_model(curve_id)
    if source == "additional_models":
        model = next((m for m in _additional_models() if m["id"] == curve_id), None)
        if model is None:
            raise ValueError("Unknown additional model: " + str(curve_id))
        return model
    if source == "nottingham":
        models = [m for m in _nottingham_models() if m["id"] == curve_id]
        return models[0] if models else _not_found(curve_id)
    if source != "garrett":
        raise ValueError("Unsupported equipment costing source")
    if curve_id not in _model_index():
        raise ValueError("Unknown Garrett curve ID")
    return _model_index()[curve_id]


def list_equipment_models(source="garrett"):
    if source == "openpytea":
        return _openpytea_models()
    if source == "additional_models":
        return copy.deepcopy(_additional_models())
    if source == "nottingham":
        return copy.deepcopy(_nottingham_models())
    if source == "all":
        return copy.deepcopy(
            list(_model_index().values())
            + _nottingham_models()
            + _additional_models()
            + _openpytea_models()
        )
    if source != "garrett":
        raise ValueError("Unsupported equipment costing source")
    return copy.deepcopy(list(_model_index().values()))


def resolve_equipment_inputs(curve_id, measurements, *, context=None, source="garrett"):
    source = model_source(curve_id, source)
    model = _model(curve_id, source)
    if source == "openpytea":
        requirements = tuple(
            InputRequirement(q["name"], q["quantity"], q["unit"])
            for q in model["input_requirements"]
        )
        return resolve_inputs(requirements, measurements, context=context)
    if source == "additional_models":
        requirement = model["input_requirements"][0]
        return resolve_inputs(
            (InputRequirement("size", requirement["quantity"], requirement["unit"]),),
            measurements,
            context=context,
        )
    if source == "nottingham":
        if "size" not in measurements:
            raise UnitResolutionError("Nottingham method requires explicit size")
        return resolve_inputs((), measurements, context=context)
    return resolve_inputs(input_requirements(model), measurements, context=context)


def estimate_from_parsed_inputs(
    curve_id, measurements, *, unit_context=None, source="garrett", **options
):
    """Explicit parser/context adapter. No fuzzy field or equipment inference."""
    source = model_source(curve_id, source)
    if source == "openpytea":
        item = measurements.get("size")
        if not isinstance(item, Measurement):
            raise UnitResolutionError(
                "MISSING_SIZING_INPUT: explicit size Measurement required"
            )
        second = measurements.get("second_size")
        if second is not None:
            if not isinstance(second, Measurement):
                raise UnitResolutionError("Second coordinate must be a Measurement")
            options.update(
                second_size=second.value,
                second_size_unit=second.unit,
                second_input_provenance=second.source,
            )
        return _openpytea_cost(
            curve_id,
            item.value,
            size_unit=item.unit,
            unit_context=unit_context,
            input_provenance=item.source,
            **options,
        )
    if source == "additional_models":
        item = measurements.get("size")
        if not isinstance(item, Measurement):
            raise UnitResolutionError(
                "Additional model requires explicit size Measurement"
            )
        return _additional_cost(
            curve_id,
            item.value,
            size_unit=item.unit,
            unit_context=unit_context,
            input_provenance=item.source,
            **options,
        )
    if source == "nottingham":
        item = measurements.get("size")
        if not isinstance(item, Measurement):
            raise UnitResolutionError(
                "Nottingham requires an explicit size Measurement"
            )
        if unit_context is not None:
            raise UnitResolutionError("Nottingham requires source-native size units")
        return estimate_cost(
            curve_id, item.value, source=source, size_unit=item.unit, **options
        )
    resolved = resolve_equipment_inputs(
        curve_id, measurements, context=unit_context, source=source
    )
    if resolved.status != "resolved":
        raise UnitResolutionError("; ".join(resolved.issues))
    request = options.get("pressure_adjustment")
    if isinstance(request, PressureAdjustment) and "design_pressure" in measurements:
        context = ConversionContext(
            target_pressure_basis=request.reference_pressure_basis,
            atmospheric_pressure_pa=request.atmospheric_pressure_pa,
        )
        supplied = measurements["design_pressure"]
        target = request.target_design_pressure
        if not isinstance(target, Measurement):
            raise UnitResolutionError(
                "Pressure-adjustment target must be a Measurement"
            )
        a = convert(
            supplied.value,
            supplied.unit,
            "psi",
            context=context,
            pressure_basis=supplied.pressure_basis,
        )
        b = convert(
            target.value,
            target.unit,
            "psi",
            context=context,
            pressure_basis=target.pressure_basis,
        )
        if (
            a.status != "converted"
            or b.status != "converted"
            or not isclose(a.value, b.value, rel_tol=1e-9, abs_tol=1e-8)
        ):
            raise UnitResolutionError(
                "Parsed design pressure conflicts with the explicit pressure-adjustment target or basis"
            )
    model = _model(curve_id, source)
    result = _garrett_cost(
        curve_id, resolved.values["size"], size_unit=model["size_unit"], **options
    )
    evidence = copy.deepcopy(result.evidence)
    evidence["unit_conversion"] = {
        name: asdict(c) for name, c in resolved.conversions.items()
    }
    evidence["normalized_context"] = dict(resolved.values)
    evidence["context_usage"] = (
        "Size drives the selected curve; context conversions do not select curves or prove design suitability. Only an explicit pressure_adjustment request changes pressure costing; its target must agree with supplied design pressure."
    )
    return replace(result, evidence=evidence)


def estimate_cost(
    curve_id,
    size,
    *,
    source="garrett",
    unit_context=None,
    input_provenance=None,
    **options,
):
    source = model_source(curve_id, source)
    if source == "openpytea":
        return _openpytea_cost(
            curve_id,
            size,
            unit_context=unit_context,
            input_provenance=input_provenance,
            **options,
        )
    if source == "additional_models":
        return _additional_cost(
            curve_id,
            size,
            unit_context=unit_context,
            input_provenance=input_provenance,
            **options,
        )
    if source == "nottingham":
        if unit_context is not None:
            raise ValueError(
                "Nottingham requires explicit native size units; unit_context is not implemented"
            )
        return _nottingham_cost(
            curve_id,
            size,
            size_unit=options["size_unit"],
            **{k: v for k, v in options.items() if k != "size_unit"},
        )
    if source != "garrett":
        raise ValueError("Unknown or unimplemented costing source")
    # Preserve the existing explicit source-coordinate API. Non-native units and
    # supplied conversion context use the same shared parser adapter.
    model = _model(curve_id, source)
    if options.get("size_unit") != model["size_unit"] or unit_context is not None:
        size_unit = options.pop("size_unit", None)
        return estimate_from_parsed_inputs(
            curve_id,
            {"size": Measurement(size, size_unit, input_provenance or {})},
            unit_context=unit_context,
            source=source,
            **options,
        )
    result = _garrett_cost(curve_id, size, **options)
    if input_provenance is not None:
        evidence = copy.deepcopy(result.evidence)
        evidence["native_input"] = {
            "value": size,
            "unit": options["size_unit"],
            "source": copy.deepcopy(input_provenance),
            "status": "explicit source coordinate; not inferred or unit-normalized",
        }
        result = replace(result, evidence=evidence)
    return result


__all__ = [
    "PressureAdjustment",
    "estimate_cost",
    "estimate_from_parsed_inputs",
    "list_equipment_models",
    "list_factors",
    "list_pressure_methods",
    "resolve_equipment_inputs",
]
