"""COMPRESSORS — TURTON ET AL.

Existing reference-purchase screening correlation; see docs/calculation_basis.md.
No sizing, escalation, installation or automatic service-specific modifications.

"""

from ._common import polynomial, reference_price

KIND = "compressor"
IMPLEMENTATION_STATUS = "screening_method"
# K1, K2, K3, B1, B2, lower size, upper size, characteristic-size unit.
CORRELATION = (2.2897, 1.3604, -0.1027, 0, 2.7, 450, 3000, "kW fluid")
MATERIAL_FACTORS = {"carbon_steel": 1, "stainless_steel": 2.111111111111111}


def base_purchase_cost(size: float, *, allow_extrapolation: bool = False) -> float:
    return polynomial(CORRELATION, size, allow_extrapolation=allow_extrapolation)


def estimate_base_price(equipment_id: str, size: float):
    return reference_price(equipment_id, base_purchase_cost(size), size, CORRELATION[7])
