"""Offline OPEX engine; disconnected from frontend and existing calculations."""

from .registry import calculate_opex, get_factor_ranges, get_model, list_models

__all__ = ["calculate_opex", "get_factor_ranges", "get_model", "list_models"]
