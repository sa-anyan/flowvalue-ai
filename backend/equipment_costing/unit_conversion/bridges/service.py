"""Canonical, source-traceable user-input conversion previews and costing handoff."""

import math
from dataclasses import asdict
from backend.equipment_costing.registry import list_equipment_models
from .. import ConversionContext, Measurement, convert, identify_unit
from . import liquid, gas, thermal, mechanical

PARAMETERS = {
    "density_kg_m3": "kg/m3",
    "residence_time_h": "h",
    "working_fraction": "fraction",
    "hydraulic_loading_m_h": "m3/m2/h",
    "differential_pressure_bar": "bar difference",
    "efficiency": "fraction",
    "power_density_kw_m3": "kW/m3",
    "temperature_k": "K",
    "absolute_pressure_bar": "bar absolute",
    "compressibility_z": "fraction",
    "molecular_weight_kg_kmol": "kg/kmol",
    "gas_residence_time_s": "s",
    "overall_u_w_m2_k": "W/m2/K",
    "lmtd_k": "K difference",
    "lmtd_correction": "fraction",
    "inside_diameter_m": "m",
    "wall_thickness_m": "m",
    "straight_length_m": "m",
    "material_density_kg_m3": "kg/m3",
    "heads_and_auxiliaries_kg": "kg",
}
RECIPES = {
    "direct": (
        "Same-dimension unit conversion",
        None,
        [],
        "output = canonical unit conversion(input)",
    ),
    "liquid_flow": (
        "Liquid duty flow",
        "volume_flow",
        ["density_kg_m3"],
        "Q = mass_flow / density",
    ),
    "gas_flow": (
        "Actual gas duty flow",
        "volume_flow",
        [
            "molecular_weight_kg_kmol",
            "temperature_k",
            "absolute_pressure_bar",
            "compressibility_z",
        ],
        "Q = n R T Z / P_absolute",
    ),
    "vessel_volume": (
        "Vessel hold-up volume",
        "volume",
        ["density_kg_m3", "residence_time_h", "working_fraction"],
        "V = (mass_flow / density) * residence_time / working_fraction",
    ),
    "dryer_volume": (
        "Dryer chamber volume",
        "volume",
        [
            "molecular_weight_kg_kmol",
            "temperature_k",
            "absolute_pressure_bar",
            "compressibility_z",
            "gas_residence_time_s",
        ],
        "V_chamber = Q_gas_actual * residence_time_seconds / 3600",
    ),
    "filter_area": (
        "Filter area",
        "area",
        ["density_kg_m3", "hydraulic_loading_m_h"],
        "A = Q_liquid / hydraulic_loading",
    ),
    "exchanger_area": (
        "Thermal transfer area",
        "area",
        ["overall_u_w_m2_k", "lmtd_k", "lmtd_correction"],
        "A = abs(H_out - H_in or supplied duty)_kW * 1000 / (U * LMTD * F)",
    ),
    "pump_coordinate": (
        "Pump flow-pressure coordinate",
        "flow_pressure_product",
        ["density_kg_m3", "differential_pressure_bar"],
        "coordinate = Q_gpm * differential_pressure_psi / 1000",
    ),
    "pump_power": (
        "Pump shaft power",
        "power",
        ["density_kg_m3", "differential_pressure_bar", "efficiency"],
        "P_shaft_kW = Q_m3_h / 3600 * differential_pressure_bar * 100 / efficiency",
    ),
    "mixing_power": (
        "Mixing power from explicit volume loading",
        "power",
        [
            "density_kg_m3",
            "residence_time_h",
            "working_fraction",
            "power_density_kw_m3",
        ],
        "P_kW = V_m3 * selected_power_density_kW_m3",
    ),
    "vessel_mass": (
        "Supplied shell geometry to weight",
        "mass",
        [
            "inside_diameter_m",
            "wall_thickness_m",
            "straight_length_m",
            "material_density_kg_m3",
            "heads_and_auxiliaries_kg",
        ],
        "m = pi*((D/2+t)^2-(D/2)^2)*L*rho + heads_and_auxiliaries",
    ),
}


def model_contract(model_id):
    model = next((m for m in list_equipment_models("all") if m["id"] == model_id), None)
    if model is None:
        raise ValueError("Select an existing costing model configuration")
    requirements = model.get("input_requirements", [])
    size = next((q for q in requirements if q.get("required", True)), {})
    target = size.get("target_unit", size.get("unit"))
    if not target or size.get("issue"):
        raise ValueError(size.get("issue") or "Model coordinate is unresolved")
    return model, size, target


def measurements(report, equipment_key):
    entities = {e["key"]: e for e in report.get("entities", [])}
    e = entities.get(equipment_key)
    if not e or e.get("kind") != "equipment":
        raise ValueError("Equipment is absent from the engineering register")
    rows = []
    for entity in [e] + [
        entities[k] for k in e.get("stream_keys", []) if k in entities
    ]:
        for v in entity.get("values", []):
            if v.get("status") == "unresolved":
                continue
            number = v.get("normalized_value")
            unit = v.get("normalized_unit")
            if number is None or not unit:
                number, unit = v.get("original_value"), v.get("original_unit")
            if (
                isinstance(number, bool)
                or not isinstance(number, (int, float))
                or not math.isfinite(number)
                or not unit
            ):
                continue
            rows.append(
                {
                    "id": v["id"],
                    "entity_key": entity["key"],
                    "tag": entity["identifier"],
                    "property": v["property"],
                    "value": number,
                    "unit": unit,
                    "sheet": v.get("sheet"),
                    "cell": v.get("cell"),
                    "status": v.get("status"),
                    "original_value": v.get("original_value"),
                    "original_unit": v.get("original_unit"),
                }
            )
    return rows


def describe(report, equipment_key, model_id=None):
    rows = measurements(report, equipment_key)
    target = None
    quantity = None
    issue = None
    requirements = []
    model_info = None
    if model_id:
        try:
            model, size, target = model_contract(model_id)
            model_info = {
                k: model.get(k)
                for k in (
                    "equipment",
                    "configuration",
                    "source",
                    "printed_page",
                    "observed_size_range",
                    "limitation",
                )
            }
            quantity = size["quantity"]
            requirements = model.get("input_requirements", [])
        except ValueError as exc:
            issue = str(exc)
    recipes = [
        {
            "id": key,
            "label": v[0],
            "quantity": v[1],
            "parameters": [
                {
                    "name": n,
                    "unit": PARAMETERS[n],
                    "status": "user_input",
                    "value": None,
                }
                for n in v[2]
            ],
            "equation": v[3],
            "implementation": "backend/equipment_costing/unit_conversion/"
            + (
                "unit_conversion.py"
                if key == "direct"
                else "bridges/"
                + (
                    "gas.py"
                    if key in {"gas_flow", "dryer_volume"}
                    else (
                        "thermal.py"
                        if key == "exchanger_area"
                        else "mechanical.py" if key == "vessel_mass" else "liquid.py"
                    )
                )
            ),
        }
        for key, v in RECIPES.items()
        if v[1] is None or v[1] == quantity
    ]
    by_key = {e["key"]: e for e in report.get("entities", [])}
    equipment = by_key[equipment_key]
    stream_context = []
    for key in equipment.get("stream_keys", []):
        stream = by_key.get(key, {})
        stream_context.append(
            {
                "entity_key": key,
                "tag": stream.get("identifier"),
                "descriptions": [
                    {
                        "evidence_id": v.get("id"),
                        "text": v.get("normalized_value") or v.get("original_value"),
                        "sheet": v.get("sheet"),
                        "cell": v.get("cell"),
                    }
                    for v in stream.get("values", [])
                    if v.get("property") in {"description", "name", "phase"}
                ],
                "connections": [
                    c
                    for c in report.get("connections", [])
                    if c.get("stream_key") == key
                    and c.get("equipment_key") == equipment_key
                ],
            }
        )
    conventions = []
    if target and ("gal" in target or "gpm" in target):
        conventions.append(
            "target_gallon_basis: US or Imperial; must be explicitly selected"
        )
    if target and "ton/" in target:
        conventions.append(
            "target_ton_basis: metric, short or long; must be explicitly selected"
        )
    return {
        "required_unit_conventions": conventions,
        "stream_context": stream_context,
        "model_id": model_id,
        "model": model_info,
        "target_unit": target,
        "target_quantity": quantity,
        "requirements": requirements,
        "issue": issue,
        "measurements": rows,
        "recipes": recipes,
        "notice": "User inputs are assumptions, not workbook observations. Choose service, phase and source streams explicitly. Preview does not change pricing.",
    }


def evaluate(report, equipment_key, spec):
    model, size, target = model_contract(spec.get("model_id"))
    method = spec.get("method", "direct")
    if method not in RECIPES:
        raise ValueError("Unsupported conversion equation")
    if RECIPES[method][1] not in (None, size["quantity"]):
        raise ValueError("Equation output dimension does not match this model")
    inputs = spec.get("inputs") or {}
    if not isinstance(inputs, dict) or set(inputs) - set(PARAMETERS):
        raise ValueError("Unknown user input")
    for k, v in inputs.items():
        if v is not None and (
            isinstance(v, bool)
            or not isinstance(v, (int, float))
            or not math.isfinite(v)
        ):
            raise ValueError("User inputs must be finite numbers")
    context = ConversionContext(**(spec.get("unit_context") or {}))
    sources = {v["id"]: v for v in measurements(report, equipment_key)}
    from .derivations import derive

    inputs, derived_inputs = derive(
        spec.get("derivations") or [],
        list(sources.values()),
        inputs,
        spec.get("unit_context") or {},
    )
    source = sources.get(spec.get("measurement_id"))
    outlet = sources.get(spec.get("outlet_measurement_id"))

    def cv(value, unit, target_unit=None):
        if value == "quantity":
            return identify_unit(unit, context=context).quantity
        result = convert(value, unit, target_unit, context=context)
        if result.status != "converted":
            # Canonical converter also reports unchanged values as converted.
            if result.value is None:
                raise ValueError("; ".join(result.issues) or "Conversion unresolved")
        return result.value

    evidence = []
    if method == "vessel_mass":
        value, unit, details = mechanical.evaluate(inputs)
    else:
        if source is None:
            raise ValueError(
                "Select a supported measurement from this equipment or its linked streams"
            )
        evidence.append(source)
        value, unit = source["value"], source["unit"]
        if method == "direct":
            if source["property"] == "enthalpy_flow":
                raise ValueError(
                    "A standalone stream enthalpy flow is not equipment heat duty or motor power"
                )
            details = {"formula": RECIPES[method][3]}
        elif method in {"gas_flow", "dryer_volume"}:
            value, unit, details = gas.evaluate(method, value, unit, inputs, cv)
        elif method == "exchanger_area":
            if source["property"] == "enthalpy_flow":
                if (
                    outlet is None
                    or outlet["property"] != "enthalpy_flow"
                    or outlet["id"] == source["id"]
                ):
                    raise ValueError(
                        "Select distinct same-side inlet and outlet enthalpy-flow measurements"
                    )
                if spec.get("same_side_reference_confirmed") is not True:
                    raise ValueError(
                        "Confirm same-side streams and common enthalpy reference"
                    )
                evidence.append(outlet)
            elif source["property"] not in {"heat_duty", "duty"}:
                raise ValueError(
                    "Thermal area needs a heat-duty measurement or enthalpy-flow difference"
                )
            value, unit, details = thermal.evaluate(
                value,
                unit,
                inputs,
                cv,
                outlet if source["property"] == "enthalpy_flow" else None,
            )
        else:
            value, unit, details = liquid.evaluate(method, value, unit, inputs, cv)
    result = convert(value, unit, target, context=context)
    if result.value is None:
        raise ValueError("; ".join(result.issues) or "Target unit unresolved")
    if result.value <= 0:
        raise ValueError("Model size must be positive")
    auxiliaries = []
    for observation in sources.values():
        target_context_unit = {"pressure": "psi", "temperature": "degF"}.get(
            observation["property"]
        )
        if target_context_unit:
            converted = convert(
                observation["value"],
                observation["unit"],
                target_context_unit,
                context=context,
            )
            auxiliaries.append(
                {
                    "measurement": observation,
                    "conversion": asdict(converted),
                    "role": "Operating context only; never substituted for design pressure",
                }
            )
    observed = model.get("observed_size_range")
    range_status = "not_available"
    if (
        isinstance(observed, (list, tuple))
        and len(observed) == 2
        and all(isinstance(v, (int, float)) for v in observed)
    ):
        range_status = (
            "within_observed_points"
            if observed[0] <= result.value <= observed[1]
            else "outside_observed_points"
        )
    return {
        "validation": {
            "dimensional_consistency": "checked_by_python",
            "physical_checks": "basic_equation_constraints_only",
            "observed_chart_range": observed,
            "observed_range_status": range_status,
            "engineering_design_validated": False,
            "notice": "Observed chart bounds are not certified design limits; canonical costing applies its own validity and extrapolation rules.",
        },
        "derived_inputs": derived_inputs,
        "input_provenance": spec.get("input_provenance", {}),
        "auxiliary_conversions": auxiliaries,
        "status": "ready",
        "model_id": model["id"],
        "size": result.value,
        "size_unit": result.canonical_target_unit or target,
        "model_target_unit": target,
        "intermediate": {"value": value, "unit": unit},
        "equation": details,
        "conversion": asdict(result),
        "source_measurements": evidence,
        "user_inputs": inputs,
        "unit_context": asdict(context),
        "rationale": spec.get("rationale", ""),
        "notice": "User-input sizing scenario, not a validated design. No costing equation or workbook observation changed.",
    }
