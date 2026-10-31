"""Offline CAPEX model selection. No routes, frontend calls or live activation."""

import copy
from dataclasses import asdict

from .engine import calculate
from .indexes.garrett.model import MODEL as GARRETT
from .indexes.garrett.model import factors as garrett_factors
from .indexes.nottingham.model import LANG, lang_factors
from .indexes.nottingham.model import MODEL as NOTTINGHAM
from .indexes.nottingham.model import factors as nottingham_factors
from .models import CapexInputs

_MODELS = {
    "garrett": (GARRETT, garrett_factors),
    "nottingham": (NOTTINGHAM, nottingham_factors),
    "nottingham_lang": (LANG, lang_factors),
}


def list_models():
    return [
        dict(**asdict(spec), default=key == "garrett", activation="offline_only")
        for key, (spec, _) in _MODELS.items()
    ]


def get_model(model_id="garrett"):
    if model_id not in _MODELS:
        raise ValueError("Unsupported CAPEX methodology: " + str(model_id))
    return copy.deepcopy(_MODELS[model_id][0])


def get_factor_ranges(model_id="garrett", process_type=None):
    spec = get_model(model_id)
    if process_type not in spec.process_types:
        raise ValueError("Select a documented process_type for this CAPEX model")
    return [asdict(f) for f in _MODELS[model_id][1](process_type)]


def calculate_capex(model_id="garrett", inputs=None):
    spec = get_model(model_id)
    if not isinstance(inputs, CapexInputs):
        raise TypeError("inputs must be CapexInputs")
    rows = (
        _MODELS[model_id][1](inputs.process_type, inputs)
        if inputs.process_type in spec.process_types
        else ()
    )
    return calculate(spec, rows, inputs)
