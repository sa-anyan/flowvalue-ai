"""Canonical Turton module registry; existing imports remain compatible."""

from . import compressors, heat_exchangers, pumps, vessels

METHODS = {
    "heat_exchanger": heat_exchangers,
    "vessel": vessels,
    "pump": pumps,
    "compressor": compressors,
}
CORRELATIONS = {kind: module.CORRELATION for kind, module in METHODS.items()}
MATERIAL_FACTORS = {kind: module.MATERIAL_FACTORS for kind, module in METHODS.items()}


def _method(kind):
    if kind not in METHODS:
        raise ValueError(f"Unsupported Turton equipment type: {kind}")
    return METHODS[kind]


def base_purchase_cost(
    kind: str, size: float, *, allow_extrapolation: bool = False
) -> float:
    return _method(kind).base_purchase_cost(
        size, allow_extrapolation=allow_extrapolation
    )


def estimate_base_price(equipment_id: str, kind: str, size: float):
    return _method(kind).estimate_base_price(equipment_id, size)
