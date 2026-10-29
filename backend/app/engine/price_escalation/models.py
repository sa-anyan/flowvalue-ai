"""Explicit index observations; no live-index default or automatic verification."""

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CostIndex(BaseModel):
    model_config = ConfigDict(
        extra="forbid", allow_inf_nan=False, str_strip_whitespace=True
    )
    series: str = Field(min_length=1, max_length=100, pattern=r"\S")
    basis: str = Field(min_length=1, max_length=200, pattern=r"\S")
    value: Decimal = Field(gt=0, le=Decimal("1e9"))
    period: str = Field(pattern=r"^\d{4}(-(0[1-9]|1[0-2]))?$")
    source: str = Field(min_length=1, max_length=2000, pattern=r"\S")
    status: Literal["assumption", "verified"]
