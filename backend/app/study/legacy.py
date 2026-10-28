"""Private, cached workbook reference data. Never executable calculation logic."""
from typing import Annotated, Literal

from pydantic import Field, model_validator

from app.engine.costing import Model

Scalar = Annotated[str, Field(max_length=6000)] | float | bool | None
class LegacyCell(Model):
    value: Scalar
    cached: bool = False
    original_value: Scalar = None
    modified: bool = False

class LegacySheet(Model):
    name: str = Field(min_length=1, max_length=100)
    cells: dict[Annotated[str, Field(pattern=r"^[A-Z]{1,3}[1-9][0-9]{0,5}$")], LegacyCell] = Field(max_length=20000)

class LegacyReference(Model):
    schema_version: Literal["flowvalue-legacy-reference-v1"]
    source_name: str = Field(min_length=1, max_length=300)
    source_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    currency: Literal["GBP"] = "GBP"
    sheets: list[LegacySheet] = Field(min_length=1, max_length=30)

    @model_validator(mode="after")
    def unique_sheets(self):
        if len({s.name for s in self.sheets}) != len(self.sheets):
            raise ValueError("Duplicate legacy sheet name")
        return self
