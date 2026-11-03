"""Live metadata over canonical sizing and costing functions; no duplicate equations.

No project assumption becomes a library default. Candidate descriptions are search
hints only: service, scope, pressure/material and model range require review.
"""

from functools import lru_cache

from backend.engineering_sizing.registry import list_methods
from backend.equipment_costing.registry import list_equipment_models


@lru_cache(maxsize=1)
def library():
    return {
        "sizing_methods": list_methods(),
        "cost_models": list_equipment_models(),
        "method_hierarchy": [
            "direct_correlation",
            "specialised_model",
            "documented_benchmark",
            "engineering_analogy",
            "manual_user_price",
        ],
        "default_assumption_ranges": [],
        "notice": "No universal residence times, properties or cost benchmarks are assumed. Current executable catalogue is Garrett; methodology names do not imply implemented Turton/Guthrie/Seider correlations.",
        "failure_modes": {
            "missing_size": "Use source dimension, linked stream derivation, reviewed design assumption, or explicit per-unit quotation",
            "out_of_range": "Never clamp; use supported boundary scaling with rationale or an independently sourced alternative",
            "phase_change": "Require supplied latent/sensible enthalpy at applicable pressure/composition or common-reference inlet/outlet enthalpy",
            "unsupported_package": "Obtain a scoped benchmark or user quote; a vessel shell is not a complete package",
            "scope_conflict": "Confirm distinct assets/aliases and package boundaries before final totals",
        },
    }
