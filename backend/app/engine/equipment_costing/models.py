"""Price with an explicit equipment, currency, scope and original index basis."""

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.engine.price_escalation.models import CostIndex


class EquipmentPrice(BaseModel):
    model_config = ConfigDict(
        extra="forbid", allow_inf_nan=False, str_strip_whitespace=True
    )
    equipment_id: str = Field(min_length=1, max_length=200, pattern=r"\S")
    amount: Decimal = Field(ge=0, le=Decimal("1e18"))
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    scope: Literal["base_purchase", "purchased", "installed", "bare_module", "other"]
    method: str = Field(min_length=1, max_length=100, pattern=r"\S")
    source_reference: str = Field(min_length=1, max_length=2000, pattern=r"\S")
    reference_index: CostIndex | None = None
    notes: list[str] = Field(default_factory=list, max_length=30)
