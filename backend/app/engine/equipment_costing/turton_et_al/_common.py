"""Shared Turton arithmetic and result envelope; no equipment-specific constants."""

from math import isfinite, log10

from app.engine.equipment_costing.models import EquipmentPrice
from app.engine.price_escalation.models import CostIndex


def polynomial(
    coefficients: tuple, size: float, *, allow_extrapolation: bool = False
) -> float:
    if not isfinite(size) or size <= 0:
        raise ValueError("Characteristic size must be finite and positive")
    k1, k2, k3, _, _, lower, upper, _ = coefficients
    if not allow_extrapolation and not lower <= size <= upper:
        raise ValueError(
            f"Characteristic size outside correlation range [{lower}, {upper}]"
        )
    exponent = k1 + k2 * log10(size) + k3 * log10(size) ** 2
    if not -280 <= exponent <= 280:
        raise ValueError("Extrapolation exceeds numerical cost limits")
    return 10**exponent


def reference_price(
    equipment_id: str, amount: float, size: float, size_unit: str
) -> EquipmentPrice:
    """Unadjusted reference purchase cost; no installation/material/pressure uplift."""
    return EquipmentPrice(
        equipment_id=equipment_id,
        amount=str(amount),
        currency="USD",
        scope="base_purchase",
        method="turton_et_al",
        source_reference="Turton et al., Table A.1; provenance in docs/calculation_basis.md",
        reference_index=CostIndex(
            series="CEPCI",
            basis="1957-1959=100",
            value=397,
            period="2001",
            source="Existing correlation reference; independently verify before issuing estimates",
            status="assumption",
        ),
        notes=[
            "Reference material/pressure basis only; excludes service-specific adjustments and installation.",
            f"Characteristic size {size:g} {size_unit}; no extrapolation allowed.",
        ],
    )
