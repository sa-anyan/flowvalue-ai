"""VESSELS — TURTON ET AL.

Existing reference-purchase screening correlation; see docs/calculation_basis.md.
No sizing, escalation, installation or automatic service-specific modifications.
Reactor use is only a vessel-shell proxy; no internals or biological equipment included.
"""

from ._common import polynomial, reference_price

KIND = "vessel"
IMPLEMENTATION_STATUS = "screening_method"
# K1, K2, K3, B1, B2, lower size, upper size, characteristic-size unit.
CORRELATION = (3.4974, 0.4485, 0.1074, 2.25, 1.82, 0.3, 520, "m3")
MATERIAL_FACTORS = {"carbon_steel": 1, "stainless_steel": 3.1}


def base_purchase_cost(size: float, *, allow_extrapolation: bool = False) -> float:
    return polynomial(CORRELATION, size, allow_extrapolation=allow_extrapolation)


def estimate_base_price(equipment_id: str, size: float):
    return reference_price(equipment_id, base_purchase_cost(size), size, CORRELATION[7])
