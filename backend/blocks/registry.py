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
    if block_id == "opex":
        from backend.opex.indexes.garrett.model import CATEGORIES, PLANT_BASE

        config = state.get("plan", {}).get("operating_economics", {})
        # Detailed items replace their blanket factor, just as in the canonical OPEX adapter.
        if config.get("avoided_costs"):
            result.append("revenue")
        itemized = {
            i.get("category")
            for g in ("materials", "labour", "additional_expenses")
            for i in config.get(g, [])
        }
        if config.get("energy"):
            itemized.add("utilities")
        for definition in CATEGORIES:
            if not definition.base or definition.id in itemized:
                continue
            if definition.id not in config.get("garrett_factors", {}):
                continue
            # Even a zero percentage has a declared base in the existing input contract.
            if definition.base == "annual_revenue":
                result.append("revenue")
            elif definition.base in {
                "fixed_capital",
                "purchased_equipment",
                PLANT_BASE,
            }:
                result.append("capex")
    return list(dict.fromkeys(result))
