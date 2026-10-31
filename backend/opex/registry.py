"""Common offline model interface. No active application integration."""

import copy
from dataclasses import asdict

from .engine import calculate
from .indexes.garrett.model import CATEGORIES, GROUP_CHECKS, MODEL
from .models import OpexInputs

_MODELS = {"garrett": (MODEL, CATEGORIES, GROUP_CHECKS)}


def get_model(model_id="garrett"):
    if model_id not in _MODELS:
        raise ValueError("Unsupported OPEX methodology: " + str(model_id))
    return copy.deepcopy(_MODELS[model_id][0])


def list_models():
    return [get_model(key) for key in _MODELS]


def get_factor_ranges(model_id="garrett", process_type=None):
    get_model(model_id)
    if process_type is not None:
        raise ValueError("Garrett Ch.4 does not publish separate process-type profiles")
    return [
        dict(
            asdict(row),
            formula="annual_cost = fraction × base"
            if row.base
            else "itemized annual cost",
        )
        for row in _MODELS[model_id][1]
    ]


def calculate_opex(model_id="garrett", inputs=None):
    get_model(model_id)
    if not isinstance(inputs, OpexInputs):
        raise TypeError("inputs must be OpexInputs")
    _, categories, checks = _MODELS[model_id]
    return calculate(model_id, categories, checks, inputs)
