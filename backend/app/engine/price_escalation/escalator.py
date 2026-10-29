"""Translate a sourced price to an explicit target index/date, not a vendor quote."""

from decimal import Decimal, localcontext

from pydantic import BaseModel, ConfigDict

from app.engine.equipment_costing.models import EquipmentPrice
from app.engine.price_escalation.models import CostIndex


class EscalatedPrice(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    original_price: EquipmentPrice
    target_index: CostIndex
    index_ratio: Decimal
    adjusted_amount: Decimal
    currency: str
    qualification: str


def escalate_price(price: EquipmentPrice, target_index: CostIndex) -> EscalatedPrice:
    """For any equipment type. Original basis must exist; series must match.

    Does not guess CEPCI from a price/year, convert currency, resize equipment,
    change scope or label an assumption as today's observed market price.
    Original inputs are retained and never mutated. Ratios are not rounded to cents.
    """
    original = price.reference_index
    if original is None:
        raise ValueError(
            "Original price index basis is missing; cannot escalate safely"
        )
    if (original.series.casefold(), original.basis.casefold()) != (
        target_index.series.casefold(),
        target_index.basis.casefold(),
    ):
        raise ValueError("Index series/bases differ; supply compatible observations")
    with localcontext() as context:
        context.prec = 34
        ratio = target_index.value / original.value
        amount = price.amount * ratio
    assumed = original.status == "assumption" or target_index.status == "assumption"
    return EscalatedPrice(
        original_price=price.model_copy(deep=True),
        target_index=target_index.model_copy(deep=True),
        index_ratio=ratio,
        adjusted_amount=amount,
        currency=price.currency,
        qualification=(
            "Planning estimate using an assumed index basis. "
            if assumed
            else "Index-adjusted estimate using supplied verified-status records. "
        )
        + f"Target period: {target_index.period}. Not a current supplier quotation; input verification is external. Currency and cost scope unchanged.",
    )
