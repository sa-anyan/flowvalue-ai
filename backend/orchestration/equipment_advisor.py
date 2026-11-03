"""Typed equipment/CAPEX recommendations; engineering reasoning, canonical Python maths."""

import json
import math

from backend.capex import get_factor_ranges
from backend.revenue.advisor import TEXT, obj

NULL_TEXT = {"type": ["string", "null"]}
NULL_NUMBER = {"type": ["number", "null"]}


def validate(value, schema):
    kind = schema["type"]
    types = kind if isinstance(kind, list) else [kind]
    if value is None and "null" in types:
        return
    if "object" in types:
        if not isinstance(value, dict) or set(value) != set(schema["properties"]):
            raise ValueError("Unexpected recommendation fields")
        for k, s in schema["properties"].items():
            validate(value[k], s)
    elif "array" in types:
        if not isinstance(value, list) or len(value) > 500:
            raise ValueError("Invalid recommendation array")
        for v in value:
            validate(v, schema["items"])
    elif "number" in types:
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
        ):
            raise ValueError("Finite numeric assumption required")
        if (
            "minimum" in schema
            and value < schema["minimum"]
            or "maximum" in schema
            and value > schema["maximum"]
        ):
            raise ValueError("Factor outside published range")
    elif "boolean" in types:
        if not isinstance(value, bool):
            raise ValueError("Boolean required")
    elif "string" in types:
        if not isinstance(value, str) or len(value) > 10000:
            raise ValueError("Invalid recommendation text")
    if "enum" in schema and value not in schema["enum"]:
        raise ValueError("Unavailable recommendation selection")


def generate(provider, instructions, context):
    models = context["available_models"]
    factors = context["available_factor_options"]
    capex_factors = get_factor_ranges("garrett", "mixed")
    selections = {
        f["id"]: {
            "type": "number",
            "minimum": float(f["minimum"]),
            "maximum": float(f["maximum"]),
        }
        for f in capex_factors
        if f["additive"]
    }
    from backend.engineering_sizing import list_methods
    from backend.engineering_sizing.registry import PARAMETER_UNITS

    methods = list_methods()
    context = dict(
        context,
        engineering_sizing_methods=methods,
        sizing_parameter_units=PARAMETER_UNITS,
    )
    stream_keys = [
        e["key"]
        for e in context["report"]["entities"]
        if e["kind"] in {"material", "energy"}
    ]
    equipment_keys = context.get("equipment_batch", {}).get(
        "keys",
        [e["key"] for e in context["report"]["entities"] if e["kind"] == "equipment"],
    )
    all_equipment_keys = [
        e["key"] for e in context.get("project_equipment_overview", [])
    ] or equipment_keys
    schema = obj(
        {
            "equipment": {
                "type": "array",
                "items": obj(
                    {
                        "equipment_key": {"type": "string", "enum": equipment_keys},
                        "curve_id": {
                            "type": ["string", "null"],
                            "enum": [m["id"] for m in models] + [None],
                        },
                        "quantity": {"type": "number", "minimum": 1, "maximum": 1000},
                        "quantity_rationale": TEXT,
                        "rationale": TEXT,
                        "uncertainty": TEXT,
                        "size": NULL_NUMBER,
                        "size_unit": NULL_TEXT,
                        "sizing_method": {
                            "type": "string",
                            "enum": [
                                "direct",
                                "volume_residence",
                                "mass_residence",
                                "mass_to_volume_flow",
                                "stream_property",
                                *[m["id"] for m in methods],
                            ],
                        },
                        "stream_key": {
                            "type": ["string", "null"],
                            "enum": stream_keys + [None],
                        },
                        "outlet_stream_key": {
                            "type": ["string", "null"],
                            "enum": stream_keys + [None],
                        },
                        "sizing_parameters": {
                            "type": "array",
                            "items": obj(
                                {
                                    "name": {
                                        "type": "string",
                                        "enum": list(PARAMETER_UNITS),
                                    },
                                    "value": {"type": "number"},
                                    "unit": TEXT,
                                    "low": NULL_NUMBER,
                                    "high": NULL_NUMBER,
                                    "rationale": TEXT,
                                    "source": TEXT,
                                }
                            ),
                        },
                        "candidate_curve_ids": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": [m["id"] for m in models],
                            },
                        },
                        "scope_decision": {
                            "type": "string",
                            "enum": ["include", "alias", "unresolved"],
                        },
                        "alias_of": {
                            "type": ["string", "null"],
                            "enum": all_equipment_keys + [None],
                        },
                        "residence_time_h": NULL_NUMBER,
                        "density_kg_m3": NULL_NUMBER,
                        "working_fraction": NULL_NUMBER,
                        "stream_property": NULL_TEXT,
                        "allow_unverified": {"type": "boolean"},
                        "target_ton_basis": {
                            "type": ["string", "null"],
                            "enum": ["metric", "short", "long", None],
                        },
                        "input_gallon_basis": {
                            "type": ["string", "null"],
                            "enum": ["US", "Imperial", None],
                        },
                        "target_gallon_basis": {
                            "type": ["string", "null"],
                            "enum": ["US", "Imperial", None],
                        },
                        "factors": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": [f["id"] for f in factors],
                            },
                        },
                        "factor_basis_confirmation": TEXT,
                        "extrapolation_exponent": NULL_NUMBER,
                        "extrapolation_justification": TEXT,
                    }
                ),
            },
            "capex": obj(
                {
                    "process_type": {
                        "type": "string",
                        "enum": ["solids", "mixed", "fluids"],
                    },
                    "delivery_basis": {
                        "type": "string",
                        "enum": ["delivered", "ex_works"],
                    },
                    "rationale": TEXT,
                    "selected_factors": obj(selections),
                    "offsite_scope_confirmation": NULL_TEXT,
                }
            ),
            "questions": {"type": "array", "items": TEXT},
        }
    )
    instructions += """\nThis is a PRELIMINARY SCREENING estimate, not a final mechanical design approval.
When identity/service is known, missing U, filtration loading, liquid density,
storage duration, pump head or residence time should normally become explicit,
bounded engineering assumptions with rationale, NOT a reason to withhold every
price. Specialist concerns are scope/risk conditions, not automatic vetoes on a
clearly labelled screening scenario. Do not invent measured data or claim these
assumptions were researched. Unknown identity, incompatible pressure/phase,
missing dedicated models or unsupported extrapolation can still remain unresolved.
For an executable sizing method, provide its required parameters; empty parameter
arrays with a selected curve are not a calculated design. pump_duty is explicitly
US gpm·psi coordinate; select and disclose target_gallon_basis US for that scenario.
This call uses a dedicated equipment + CAPEX schema. Return EVERY parsed equipment
record, with a selected curve/provisional sizing scenario where physically defensible,
otherwise curve_id=null and explain the remaining design need. Models are available
configurations; choose by DUTY, not spelling. No need for equipment names to match a
catalogue name. Distinguish vessel shell, agitation, cooling and ancillary omissions.
Read the independent analyst_reviews: incorporate or explicitly challenge material,
hygiene, safety and sizing recommendations in each equipment rationale. Explain wetted
versus external materials, applicable alternatives and remaining compatibility checks.
Do not claim the team researched or approved a material merely because it proposed it.
Use volume_residence only with the actual liquid volume-flow stream, not a dilute
reagent stream or a gas stream. Python derives V=Q*t/working_fraction; DO NOT put your
mental arithmetic into size or round/clamp it to a curve boundary. Explain residence
assumptions and scenario uncertainty. For missing storage capacity, consider whether
an explicitly assumed storage duration on the actual delivered volumetric stream is
defensible. If it is not, leave unpriced and state the design question.
Where liquid total MASS flow is available but volume flow is absent, mass_residence
may use an EXPLICIT justified density_kg_m3 and residence_time_h/working_fraction.
Python computes V=(mass flow/density)*residence/working_fraction. mass_to_volume_flow
uses an explicit justified density_kg_m3 to compute volume throughput. Density is a
conditional engineering assumption, not a measured workbook fact; do not use liquid
density for gas or invent missing gas conditions. Cite its rationale and uncertainty.
Parallel AB/base aliases: do not price both as independent installed equipment
without a justified quantity/scope. Leave alias-only duplicates unpriced with reason.
Gas sizing from gauge pressure requires an explicit atmospheric_pressure_bar assumption (e.g. standard-atmosphere scenario, not a site measurement), unless absolute_pressure_bar is explicitly supplied. Use only actual stream/equipment keys allowed by the schema.
Select an allowlisted engineering_sizing_methods id when physical derivation is needed.
Use sizing_parameters with the exact SI parameter names from the registry, explicit
units, rationale/source and plausible low/high bounds; parameters are engineering
assumptions unless tied to supplied evidence. Python does ALL arithmetic.
exchanger_area: source heat_duty kW, or inlet/outlet enthalpy_flow kW on one side
using outlet_stream_key; otherwise explicit sensible Cp and temperature change are
permitted ONLY for sensible heating, not phase change. U/LMTD/F need justified
assumptions. pump_duty uses liquid volume (or explicit density) and DIFFERENTIAL
pressure, never operating pressure. filter_area uses explicit hydraulic loading.
gas_volume uses explicit MW, absolute pressure, temperature and Z. dryer_chamber
uses actual gas volume (or gas equation assumptions) and gas residence seconds.
Use vessel_hold_up for process-dependent residence/storage assumptions: M&E alone
usually cannot establish kinetic residence time. Show rationale, bounds and gaps.
Keep candidate_curve_ids even when sizing is unresolved. scope_decision alias with
alias_of must reference an actual registered equipment key with evidence/reason;
do not count AB/base aliases twice or infer two units merely from AB.
A missing design input should trigger a defensible preliminary scenario, not an
empty match, where a scenario is physically supportable. Truly unsupported models
remain unresolved and research is offered separately with consent.
Direct size is allowed only as an explicit supplied/provisional design input. Unknown
correlation/sizing methods are not executable. For out-of-range estimates, choose an
explicit justified exponent where appropriate, with uncertainty; do not clamp the
engineering capacity. Published exponents take priority in the Python engine.
CAPEX selected_factors are ONLY the canonical CAPEX factor IDs in the schema, NOT
costing model installation/module factors. Choose each fraction within its published
range. Delivery basis is a documented SCENARIO if unknown. Do not stack installation
and module multipliers; the canonical engine separates purchased/installed costs.
Provisional digitised graph data can use allow_unverified=true with disclosed caveats.
Historical Garrett USD basis remains historical. No arbitrary current price index.
"""
    from .planning_context import compact_transport

    instructions += "\nCost catalogues use column arrays: each row follows the matching available_models_columns or available_factor_options_columns header. All original IDs and factors remain exact."
    value = provider.generate(
        instructions=instructions, context=compact_transport(context), schema=schema
    )
    validate(value, schema)
    rows = []
    for row in value["equipment"]:
        if (
            row["curve_id"] is None
            and len(row.get("candidate_curve_ids", [])) == 1
            and row.get("scope_decision") == "include"
            and row["sizing_method"] != "direct"
        ):
            row["curve_id"] = row["candidate_curve_ids"][0]
            row["rationale"] += (
                " Single candidate retained for preliminary sizing validation; not a verified configuration."
            )
        options = {"allow_unverified": row["allow_unverified"]}
        bases = {
            k: row[k] for k in ("input_gallon_basis", "target_gallon_basis") if row[k]
        }
        if row.get("target_ton_basis"):
            bases["target_ton_basis"] = row["target_ton_basis"]
        if bases:
            options["unit_context"] = bases
        if row["factors"]:
            options.update(
                factors=row["factors"],
                factor_basis_confirmation=row["factor_basis_confirmation"],
            )
        if row["extrapolation_exponent"] is not None:
            options.update(
                extrapolation_exponent=row["extrapolation_exponent"],
                extrapolation_justification=row["extrapolation_justification"],
            )
        if row.get("quantity", 1) != int(row.get("quantity", 1)):
            raise ValueError("Equipment count must be an integer")
        item = {
            "equipment_key": row["equipment_key"],
            "candidate_curve_ids": row.get("candidate_curve_ids", []),
            "scope_decision": row.get("scope_decision", "include"),
            "alias_of": row.get("alias_of"),
            "curve_id": row["curve_id"],
            "size": row["size"],
            "size_unit": row["size_unit"],
            "quantity": row.get("quantity", 1),
            "quantity_rationale": row.get(
                "quantity_rationale", "Quantity assumption needs review"
            ),
            "rationale": row["rationale"],
            "uncertainty": row["uncertainty"],
            "costing_options": options,
        }
        if row["sizing_method"] != "direct":
            item["sizing"] = {
                "method": row["sizing_method"],
                "stream_key": row["stream_key"],
                "residence_time_h": row["residence_time_h"],
                "density_kg_m3": row.get("density_kg_m3"),
                "outlet_stream_key": row.get("outlet_stream_key"),
                "parameters": {
                    p["name"]: {**p, "status": "llm_estimate"}
                    for p in row.get("sizing_parameters", [])
                },
                "working_fraction": row["working_fraction"],
                "property": row["stream_property"],
            }
        rows.append(item)
    cap = value["capex"]
    rationale = cap.pop("rationale")
    cap.update(model_id="garrett", factor_selection="selected")
    return {
        "sections": [
            {
                "section": "equipment",
                "value_json": json.dumps(rows),
                "rationale": "Process-aware engineering model selection; see each equipment basis",
                "units": "Original model units or Python-derived SI dimensions",
                "evidence_ids": [],
                "uncertainty": "Conditional preliminary sizing/proxy costs; not industrially validated",
            },
            {
                "section": "capex",
                "value_json": json.dumps(cap),
                "rationale": rationale,
                "units": "Garrett historical USD; fractions of their documented bases",
                "evidence_ids": [],
                "uncertainty": "Preliminary factorial scenario",
            },
        ],
        "source_review": [],
        "questions": value["questions"],
    }
