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
    schema = obj(
        {
            "equipment": {
                "type": "array",
                "items": obj(
                    {
                        "equipment_key": TEXT,
                        "curve_id": {
                            "type": ["string", "null"],
                            "enum": [m["id"] for m in models] + [None],
                        },
                        "rationale": TEXT,
                        "uncertainty": TEXT,
                        "size": NULL_NUMBER,
                        "size_unit": NULL_TEXT,
                        "sizing_method": {
                            "type": "string",
                            "enum": ["direct", "volume_residence", "stream_property"],
                        },
                        "stream_key": NULL_TEXT,
                        "residence_time_h": NULL_NUMBER,
                        "working_fraction": NULL_NUMBER,
                        "stream_property": NULL_TEXT,
                        "allow_unverified": {"type": "boolean"},
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
    instructions += """\nThis call uses a dedicated equipment + CAPEX schema. Return EVERY parsed equipment
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
    value = provider.generate(instructions=instructions, context=context, schema=schema)
    validate(value, schema)
    rows = []
    for row in value["equipment"]:
        options = {"allow_unverified": row["allow_unverified"]}
        bases = {
            k: row[k] for k in ("input_gallon_basis", "target_gallon_basis") if row[k]
        }
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
        item = {
            "equipment_key": row["equipment_key"],
            "curve_id": row["curve_id"],
            "size": row["size"],
            "size_unit": row["size_unit"],
            "quantity": 1,
            "rationale": row["rationale"],
            "uncertainty": row["uncertainty"],
            "costing_options": options,
        }
        if row["sizing_method"] != "direct":
            item["sizing"] = {
                "method": row["sizing_method"],
                "stream_key": row["stream_key"],
                "residence_time_h": row["residence_time_h"],
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
