"""Typed CAPEX proposal adapter, with routing fields required by the Python bridge."""

import json
from backend.capex import get_factor_ranges
from backend.revenue.advisor import TEXT, obj
from .equipment_advisor import validate
from .planning_context import compact_transport


def generate(provider, instructions, context):
    factors = {
        f["id"]: {
            "type": "number",
            "minimum": float(f["minimum"]),
            "maximum": float(f["maximum"]),
        }
        for f in get_factor_ranges("garrett", "mixed")
        if f["minimum"] is not None and f["additive"]
    }
    schema = obj(
        {
            "process_type": {"type": "string", "enum": ["solids", "mixed", "fluids"]},
            "delivery_basis": {"type": "string", "enum": ["delivered", "ex_works"]},
            "selected_factors": obj(factors),
            "rationale": TEXT,
            "uncertainty": TEXT,
        }
    )
    response = provider.generate(
        instructions=instructions
        + "\nReturn a Garrett detailed CAPEX input proposal using this strict contract. Select every applicable fraction from its supplied published range, explaining provisional scope, plant location/integration and equipment basis. delivery_basis is the equipment delivery assumption, not a price escalation. Never invent equipment prices or capital totals. Working capital uses Garrett model_default. This is a provisional engineering proposal, not user approval.",
        context=compact_transport(context),
        schema=schema,
    )
    validate(response, schema)
    plan = {
        "model_id": "garrett",
        "process_type": response["process_type"],
        "delivery_basis": response["delivery_basis"],
        "factor_selection": "selected",
        "selected_factors": response["selected_factors"],
        "working_capital": {
            "method": "model_default",
            "rationale": "Garrett documented default; provisional engineering planning basis",
        },
    }
    return {
        "sections": [
            {
                "section": "capex",
                "value_json": json.dumps(plan),
                "rationale": response["rationale"],
                "units": "Canonical factor fractions and published calculation bases",
                "evidence_ids": [],
                "uncertainty": response["uncertainty"],
            }
        ],
        "source_review": [],
        "questions": [],
    }
