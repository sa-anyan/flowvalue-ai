"""Canonical annual financial modelling public interface."""

from .engine import calculate_financials
from .registry import get_model, list_models
from .snapshots import (
    freeze_inputs,
    restore_inputs,
    revise_inputs,
    save_assessment,
    snapshot_id,
)

__all__ = [
    "calculate_financials",
    "freeze_inputs",
    "get_model",
    "list_models",
    "restore_inputs",
    "revise_inputs",
    "save_assessment",
    "snapshot_id",
]
