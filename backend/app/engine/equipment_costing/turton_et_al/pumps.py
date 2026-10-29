"""PUMPS — TURTON ET AL.

Existing reference-purchase screening correlation; see docs/calculation_basis.md.
No sizing, escalation, installation or automatic service-specific modifications.

"""

from ._common import polynomial, reference_price

KIND = "pump"
IMPLEMENTATION_STATUS = "screening_method"
# K1, K2, K3, B1, B2, lower size, upper size, characteristic-size unit.
CORRELATION = (3.3892, 0.0536, 0.1538, 1.89, 1.35, 1, 300, "kW shaft")
MATERIAL_FACTORS = {"carbon_steel": 1, "stainless_steel": 2.3}


def base_purchase_cost(size: float, *, allow_extrapolation: bool = False) -> float:
    return polynomial(CORRELATION, size, allow_extrapolation=allow_extrapolation)


def estimate_base_price(equipment_id: str, size: float):
    return reference_price(equipment_id, base_purchase_cost(size), size, CORRELATION[7])
