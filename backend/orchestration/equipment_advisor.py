"""Compatibility imports; all equipment matching delegates to the canonical matcher.

The previous mixed matching/sizing LLM implementation has been removed. Validation
helpers remain for existing independent economics and research consumers.
"""

import json
import math

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
    """Legacy entry point; never run a second equipment matching implementation."""
    from backend.equipment_matching.service import match_report, apply_matches

    class Uncached:
        def cached(self, context, call):
            return call(), False

    result = match_report(
        context["report"], context.get("description", ""), Uncached(), provider
    )
    rows = apply_matches(context.get("plan", {}).get("equipment", []), result)
    return {
        "sections": [
            {
                "section": "equipment",
                "value_json": json.dumps(rows),
                "rationale": "Canonical conceptual matching",
                "units": "No sizing generated",
                "evidence_ids": [],
                "uncertainty": result["notice"],
            }
        ],
        "source_review": [],
        "questions": [],
    }
