"""Canonical, source-traceable user-input conversion previews and costing handoff."""

import copy
import math
from dataclasses import asdict, replace
from backend.equipment_costing.registry import list_equipment_models
from backend.engineering_sizing.versioning import method_metadata
from .. import ConversionContext, ConversionResult, Measurement, convert, identify_unit
from . import liquid, gas, thermal, mechanical, heat_exchanger, production_sizing

PARAMETERS = {
    "motor_efficiency": "fraction",
    "head_m": "m",
    "product_rate_kg_h": "kg/h",
    "volumetric_productivity_kg_m3_h": "kg/m3/h",
    "production_allocation_fraction": "fraction",
    **{name: "K" for name in heat_exchanger.TEMPERATURES.values()},
    "heat_duty_kw": "kW",
    "specific_heat_kj_kg_k": "kJ/kg/K",
    "latent_heat_kj_kg": "kJ/kg",
    "phase_change_fraction": "fraction",
    "sensible_enthalpy_change_kj_kg": "kJ/kg",
    "utility_allocation_fraction": "fraction",
    "duty_balance_tolerance_fraction": "fraction",
    "reference_temperature_k": "K",
    "reference_pressure_bar": "bar absolute",
    "reference_compressibility_z": "fraction",
    "discharge_pressure_bar": "bar absolute",
    "heat_capacity_ratio": "fraction",
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
    "dryer_evaporation": (
        "Dryer net water evaporation",
        "mass_flow",
        [],
        "evaporation = selected feed water component mass flow - selected product water component mass flow; assumes no other water paths or reaction",
    ),
    "electrical_to_shaft_power": (
        "Electrical input to shaft output",
        "power",
        ["motor_efficiency"],
        "P_shaft=P_electrical*motor_efficiency; explicit motor efficiency",
    ),
    "shaft_to_electrical_power": (
        "Shaft output to electrical input",
        "power",
        ["motor_efficiency"],
        "P_electrical=P_shaft/motor_efficiency; explicit motor efficiency",
    ),
    "pump_hydraulic_power": (
        "Pump hydraulic power",
        "power",
        ["density_kg_m3", "differential_pressure_bar"],
        "P_hydraulic=Q*deltaP; no shaft/electrical substitution",
    ),
    "pump_flow_head": (
        "Pump flow × square-root head",
        "flow_sqrt_head",
        ["density_kg_m3", "head_m", "differential_pressure_bar"],
        "S = Q * sqrt(H); explicit head, or H = differential_pressure/(rho*9.80665); operating pressure is not differential pressure",
    ),
    "clarifier_area": (
        "Clarifier surface overflow area",
        "area",
        ["density_kg_m3", "hydraulic_loading_m_h"],
        "A = Q_liquid / surface_overflow_rate; explicit hydraulic_loading_m_h; solids-loading/design review separate",
    ),
    "vessel_productivity": (
        "Production/productivity vessel scenario",
        "volume",
        [
            "product_rate_kg_h",
            "volumetric_productivity_kg_m3_h",
            "production_allocation_fraction",
            "working_fraction",
        ],
        "V_design = product_rate * allocation / volumetric_productivity / working_fraction; explicit preliminary assumptions, not measured broth flow",
    ),
    "standard_gas_flow": (
        "Gas flow at explicit reference conditions",
        "standard_volume_flow",
        [
            "molecular_weight_kg_kmol",
            "reference_temperature_k",
            "reference_pressure_bar",
            "reference_compressibility_z",
        ],
        "Canonical gas relation at explicit reference T/P/Z; actual volumetric inputs additionally require inlet T/P/Z",
    ),
    "gas_compression": (
        "Gas-compression power screening",
        "power",
        [
            "molecular_weight_kg_kmol",
            "temperature_k",
            "absolute_pressure_bar",
            "discharge_pressure_bar",
            "heat_capacity_ratio",
            "efficiency",
            "compressibility_z",
        ],
        "Canonical ideal-gas isentropic compression; explicit inlet/outlet absolute pressures, k, Z and efficiency; single-stage screening only",
    ),
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
        "A = selected positive duty_kW * 1000 / (U * LMTD * F)",
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
                    "component": v.get("component"),
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
    model = {}
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
                    "source_year",
                    "capacity_limits",
                    "secondary_capacity_limits",
                    "cost_scope",
                    "coefficients",
                    "reference",
                    "pressure_limits",
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
                "bridges/drying.py"
                if key == "dryer_evaporation"
                else (
                    "bridges/production_sizing.py"
                    if key == "vessel_productivity"
                    else (
                        "unit_conversion.py"
                        if key == "direct"
                        else "bridges/"
                        + (
                            "gas.py"
                            if key in {"gas_flow", "dryer_volume"}
                            else (
                                "heat_exchanger.py"
                                if key == "exchanger_area"
                                else (
                                    "mechanical.py"
                                    if key == "vessel_mass"
                                    else "liquid.py"
                                )
                            )
                        )
                    )
                )
            ),
        }
        for key, v in RECIPES.items()
        if (v[1] is None or v[1] == quantity)
        and (
            key != "dryer_evaporation" or "evapor" in str(size.get("role", "")).lower()
        )
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
                "composition": [
                    {
                        "evidence_id": v.get("id"),
                        "component": v.get("component"),
                        "property": v.get("property"),
                        "value": v.get("normalized_value"),
                        "unit": v.get("normalized_unit"),
                        "status": v.get("status"),
                        "sheet": v.get("sheet"),
                        "cell": v.get("cell"),
                    }
                    for v in stream.get("values", [])
                    if str(v.get("property", "")).startswith("component_")
                    or v.get("property") in {"mass_fraction", "mole_fraction"}
                ][:100],
                "composition_truncated": sum(
                    str(v.get("property", "")).startswith("component_")
                    or v.get("property") in {"mass_fraction", "mole_fraction"}
                    for v in stream.get("values", [])
                )
                > 100,
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
        "secondary_requirement": (
            requirements[1]
            if model.get("source") == "openpytea" and len(requirements) > 1
            else None
        ),
        "required_unit_conventions": conventions,
        "stream_context": stream_context,
        "thermal_input_requirements": {
            "all_thermal_cases": ["overall_u_w_m2_k", "lmtd_correction"],
            "enthalpy_difference": "Selected same-side inlet/outlet roles, explicit common-reference confirmation; shared utilities require allocation",
            "sensible_heat": ["specific_heat_kj_kg_k"],
            "phase_change": [
                "latent_heat_kj_kg",
                "phase_change_fraction",
                "sensible_enthalpy_change_kj_kg",
            ],
            "assumed_duty": ["heat_duty_kw"],
            "missing_terminal_stream": "Use null for absent stream and an explicit corresponding *_temperature_k assumption; never repeat inlet as outlet",
            "explicit_lmtd": ["lmtd_k"],
            "notice": "These are required model inputs, not supplied values. Proposed assumptions retain units, rationale and limitations. Isothermal boiling/condensation can have nonzero latent duty.",
        },
        "thermal_workflow": "For exchanger_area, thermal_basis assigns linked hot/cold inlet/outlet stream keys. Python computes signed same-side enthalpy differences and terminal-temperature LMTD. Sensible/latent heat or explicit duty are alternative disclosed assumptions. Do not use derivation bindings for enthalpy differences; the thermal adapter handles these directly.",
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
    from ..sizing_parameters import normalize_parameters, TARGETS
    from .derivations import derive
    from .basis_validation import validate_bulk_liquid_basis
    from .drying import water_evaporation
    from .observation_selection import select_observation

    # Engineering families only: unit-only recipes do not acquire a fabricated
    # engineering method ID. Preserve the recipe to distinguish execution paths.
    method_id = {
        "vessel_mass": "vessel_mass",
        "vessel_productivity": "vessel_productivity",
        "mixing_power": "mixing_power",
        "gas_compression": "gas_compression",
        "gas_flow": "gas_volume",
        "standard_gas_flow": "gas_volume",
        "dryer_volume": "dryer_chamber",
        "dryer_evaporation": "evaporated_water",
        "vessel_volume": "vessel_hold_up",
        "filter_area": "filter_area",
        "clarifier_area": "filter_area",
        "exchanger_area": "exchanger_area",
        "pump_power": "pump_duty",
        "pump_coordinate": "pump_duty",
        "pump_hydraulic_power": "pump_duty",
    }.get(method)
    engineering_metadata = (
        method_metadata(
            method_id,
            evaluate,
            execution_layer="equipment_bridge",
            contract={"recipe_id": method},
            dependencies=(
                normalize_parameters,
                derive,
                validate_bulk_liquid_basis,
                water_evaporation,
                select_observation,
            ),
        )
        if method_id
        else None
    )
    if RECIPES[method][1] not in (None, size["quantity"]):
        raise ValueError("Equation output dimension does not match this model")
    if model["id"] == "fermenter_reactor_turton_2001" and method != "direct":
        if spec.get("operating_mode") != "continuous":
            raise ValueError(
                "Fermenter flow-to-volume sizing requires explicit continuous operating_mode; batch/unknown mode needs documented per-vessel volume or a supported batch sizing basis"
            )
        if method not in {"vessel_volume", "vessel_productivity"}:
            raise ValueError(
                "Fermenter preliminary continuous volume needs an explicit hold-up or production/productivity sizing basis"
            )
    inputs = spec.get("inputs") or {}
    if not isinstance(inputs, dict) or set(inputs) - set(PARAMETERS):
        raise ValueError("Unknown user input")
    context = ConversionContext(**(spec.get("unit_context") or {}))
    inputs, parameter_conversions = normalize_parameters(inputs, context=context)
    inputs = {
        name: (
            record["value"] if name in TARGETS and isinstance(record, dict) else record
        )
        for name, record in inputs.items()
    }
    for k, v in inputs.items():
        if v is not None and (
            isinstance(v, bool)
            or not isinstance(v, (int, float))
            or not math.isfinite(v)
        ):
            raise ValueError("User inputs must be finite numbers")
    if method == "standard_gas_flow":
        required = [
            "reference_temperature_k",
            "reference_pressure_bar",
            "reference_compressibility_z",
        ]
        if any(
            not isinstance(inputs.get(name), (int, float)) or inputs[name] <= 0
            for name in required
        ):
            raise ValueError(
                "Standard gas flow requires explicit positive reference T, absolute P and Z"
            )
        reference = "; ".join(
            f"{name}={inputs[name]} {PARAMETERS[name]}" for name in required
        )
        context = replace(
            context, input_gas_reference=reference, target_gas_reference=reference
        )
    sources = {v["id"]: v for v in measurements(report, equipment_key)}
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
    if method == "dryer_evaporation":
        if "evapor" not in str(size.get("role", "")).lower():
            raise ValueError(
                "Net water evaporation is not this model's sizing coordinate"
            )
        if source is None or outlet is None:
            raise ValueError(
                "Select both dryer feed and product water component measurements"
            )
        value, unit, details = water_evaporation(source, outlet, cv)
        evidence.extend([source, outlet])
    elif method == "exchanger_area" and spec.get("thermal_basis"):
        value, unit, details = heat_exchanger.calculate_basis(
            list(sources.values()),
            describe(report, equipment_key, spec.get("model_id"))["stream_context"],
            spec["thermal_basis"],
            inputs,
            cv,
        )
        inputs = details["resolved_inputs"]
        derived_inputs.extend(details["derived_inputs"])
        evidence.extend(details["source_measurements"])
    elif method == "vessel_productivity":
        value, unit, details = production_sizing.vessel_productivity(inputs)
    elif method == "vessel_mass":
        value, unit, details = mechanical.evaluate(inputs)
    else:
        if source is None:
            raise ValueError(
                "Select a supported measurement from this equipment or its linked streams"
            )
        validate_bulk_liquid_basis(report, equipment_key, source, method)
        evidence.append(source)
        value, unit = source["value"], source["unit"]
        if method in {"electrical_to_shaft_power", "shaft_to_electrical_power"}:
            efficiency = inputs.get("motor_efficiency")
            if (
                isinstance(efficiency, bool)
                or not isinstance(efficiency, (int, float))
                or not 0 < efficiency <= 1
            ):
                raise ValueError("Explicit motor_efficiency must be in (0,1]")
            value = cv(value, unit, "kW") * (
                efficiency if method == "electrical_to_shaft_power" else 1 / efficiency
            )
            unit = "kW"
            details = {"formula": RECIPES[method][3], "motor_efficiency": efficiency}
        elif method == "direct":
            if "evapor" in str(size.get("role", "")).lower() and source[
                "property"
            ] not in {"evaporation_rate", "water_evaporation_rate"}:
                raise ValueError(
                    "EVAPORATION_BASIS_REQUIRED: wet-feed mass flow is not evaporation; select dryer_evaporation with feed/product water component measurements"
                )
            if model.get("source") == "openpytea":
                role = size.get("role", "").lower()
                prop = source["property"]
                if (
                    (
                        any(k in role for k in ("shaft", "brake", "driver"))
                        and prop
                        in {"electrical_power", "motor_power", "heat_duty", "duty"}
                    )
                    or (
                        "fluid power" in role
                        and prop in {"shaft_power", "motor_power", "electrical_power"}
                    )
                    or (
                        any(k in role for k in ("heat", "duty"))
                        and prop in {"shaft_power", "motor_power", "electrical_power"}
                    )
                ):
                    raise ValueError(
                        "POWER_ROLE_MISMATCH: select a supported efficiency/hydraulic conversion; electrical, shaft and heat duties are not interchangeable"
                    )
            if source["property"] == "enthalpy_flow":
                raise ValueError(
                    "A standalone stream enthalpy flow is not equipment heat duty or motor power"
                )
            details = {"formula": RECIPES[method][3]}
        elif method in {
            "gas_flow",
            "dryer_volume",
            "gas_compression",
            "standard_gas_flow",
        }:
            if method == "gas_compression":
                phases = [
                    str(
                        v.get("normalized_value") or v.get("original_value") or ""
                    ).casefold()
                    for e in report["entities"]
                    if e.get("key") == source["entity_key"]
                    for v in e.get("values", [])
                    if v.get("property") == "phase"
                ]
                if any(
                    phase in {"liquid", "solid", "l", "s", "two_phase", "two-phase"}
                    for phase in phases
                ):
                    raise ValueError(
                        "Ideal-gas compression is incompatible with a source-declared liquid, solid or two-phase stream"
                    )
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
            value, unit, details = liquid.evaluate(
                "filter_area" if method == "clarifier_area" else method,
                value,
                unit,
                inputs,
                cv,
            )
    if size.get("manual_coordinate"):
        if method != "direct" or unit != target:
            raise ValueError(
                "MISSING_SIZING_INPUT: supply explicit source-native composite coordinate in "
                + target
            )
        result = ConversionResult(
            "converted",
            Measurement(value, unit),
            target,
            value,
            "source_coordinate",
            unit,
            target,
            None,
            issues=(),
            assumptions=(
                "Explicit composite coordinate; no unverified dimensional derivation performed",
            ),
        )
    else:
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
    second = None
    if (
        model.get("source") == "openpytea"
        and len(model.get("input_requirements", [])) > 1
    ):
        from backend.equipment_costing.indexes.openpytea.adapter import native_input

        requirement = model["input_requirements"][1]
        proposal = spec.get("secondary_input") or {}
        observation = sources.get(proposal.get("measurement_id"))
        if observation:
            v, u = observation["value"], observation["unit"]
            provenance = {"status": "EXTRACTED", "measurement": observation}
        else:
            if (
                not proposal.get("rationale")
                or proposal.get("value") is None
                or not proposal.get("unit")
            ):
                raise ValueError(
                    "MISSING_SIZING_INPUT: independently identify second model coordinate or supply a justified assumption"
                )
            v, u = proposal["value"], proposal["unit"]
            provenance = {"status": "ASSUMED", "rationale": proposal["rationale"]}
        converted, trace = native_input(v, u, requirement, context, provenance)
        second = {
            "second_size": converted,
            "second_size_unit": requirement["unit"],
            "second_input_provenance": trace,
        }
    return {
        **(second or {}),
        **(
            {"engineering_method": engineering_metadata} if engineering_metadata else {}
        ),
        "validation": {
            "dimensional_consistency": "checked_by_python",
            "physical_checks": "basic_equation_constraints_only",
            "observed_chart_range": observed,
            "observed_range_status": range_status,
            "engineering_design_validated": False,
            "notice": "Observed chart bounds are not certified design limits; canonical costing applies its own validity and extrapolation rules.",
        },
        "derived_inputs": derived_inputs,
        "parameter_unit_conversions": parameter_conversions,
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
        "original_user_inputs": copy.deepcopy(spec.get("inputs") or {}),
        "unit_context": asdict(context),
        "rationale": spec.get("rationale", ""),
        "notice": "User-input sizing scenario, not a validated design. No costing equation or workbook observation changed.",
    }
