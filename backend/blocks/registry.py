"""Declared boundaries and lazy entry points. Listing blocks executes nothing."""

from importlib import import_module

BLOCKS = {
    "engineering_data": {
        "label": "Engineering data",
        "page": "/data/equipment",
        "requires": [],
        "owns": "Workbook extraction, streams, equipment register and source evidence",
    },
    "equipment": {
        "label": "Equipment",
        "page": "/capex/equipment",
        "requires": ["engineering_data"],
        "owns": "Equipment sizing, unit conversion, model selection and equipment costs",
    },
    "capex": {
        "label": "CAPEX",
        "page": "/capex",
        "requires": ["equipment"],
        "owns": "Capital factors and project investment",
    },
    "revenue": {
        "label": "Revenue",
        "page": "/revenue",
        "requires": ["engineering_data"],
        "owns": "User-stated payment methods, billable quantities and income",
    },
    "opex": {
        "label": "OPEX",
        "page": "/opex",
        "requires": ["engineering_data"],
        "owns": "Consumption, utilities, staffing and annual operating expenses",
    },
    "financial": {
        "label": "Financial model",
        "page": "/financial-modelling",
        "requires": ["capex", "revenue", "opex"],
        "owns": "Annual financial ledger and investment indicators",
    },
}


def list_blocks():
    return [dict(id=key, **value) for key, value in BLOCKS.items()]


def get_runner(block_id):
    if block_id not in BLOCKS:
        raise ValueError("Unknown stage: " + block_id)
    return import_module("backend.blocks." + block_id + ".runner").calculate


def dependencies(block_id, state):
    if block_id not in BLOCKS:
        raise ValueError("Unknown stage: " + block_id)
    result = list(BLOCKS[block_id]["requires"])
    # CAPEX/revenue are optional OPEX bases. Their absence leaves affected
    # factor lines unresolved; independently supported operating costs still run.
    return list(dict.fromkeys(result))
