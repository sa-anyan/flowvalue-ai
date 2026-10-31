"""Interchangeable model boundary; only Garrett currently implemented."""

import copy

from .engine import calculate_revenue
from .indexes.garrett.model import MODEL


def get_model(model_id="garrett"):
    if model_id != "garrett":
        raise ValueError("Unsupported revenue methodology: " + str(model_id))
    model = copy.deepcopy(MODEL)
    model["categories"] = list(list_categories())
    return model


def list_models():
    return [get_model()]


__all__ = ["calculate_revenue", "get_model", "list_models"]


def list_categories():
    from .validation import CATEGORIES

    return CATEGORIES


def get_category(category):
    from importlib import import_module

    if category not in list_categories():
        raise ValueError("Unsupported revenue category: " + str(category))
    return import_module("backend.revenue.categories." + category).calculate
