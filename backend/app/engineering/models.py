"""Unit investigations and versioned, explicitly provisional review records."""

from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator

from app.engine.costing import Model

MaterialChoice = Literal[
    "unknown", "carbon_steel", "ss304", "ss316l", "polymer", "other"
]


class UnitService(Model):
    duty_description: str = Field(default="", max_length=1500)
    fluid_composition: str = Field(default="", max_length=2000)
    concentration_basis: str = Field(default="", max_length=1000)
    phase: Literal["unknown", "liquid", "gas", "multiphase", "solid"] = "unknown"
    normal_temperature_c: float | None = Field(default=None, ge=-273.15, le=2500)
    design_temperature_c: float | None = Field(default=None, ge=-273.15, le=2500)
    design_pressure_barg: float | None = Field(default=None, ge=0, le=1000)
    food_contact: bool | None = None
    cleaning_regime: str = Field(default="", max_length=1500)
    corrosion_conditions: str = Field(default="", max_length=1500)
    wetted_material: MaterialChoice = "unknown"
    shell_material: MaterialChoice = "unknown"
    lining_or_cladding: str = Field(default="", max_length=1000)
    material_rationale: str = Field(default="", max_length=2500)
    compatibility_reviewed: bool = False
    mechanical_scope_reviewed: bool = False

    @model_validator(mode="after")
    def temperature_basis(self):
        if (
            self.normal_temperature_c is not None
            and self.design_temperature_c is not None
            and self.design_temperature_c < self.normal_temperature_c
        ):
            raise ValueError(
                "Design temperature cannot be below the stated normal temperature"
            )
        return self


class EngineeringBaseline(Model):
    digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    reviewed_at: datetime
    reviewer: str = Field(min_length=1, max_length=150)
    actor_id: str | None = None
    basis: str = Field(min_length=1, max_length=2000)
    equipment: dict
    status: Literal["user_reviewed_preliminary"] = "user_reviewed_preliminary"


class EngineeringCase(Model):
    unit_id: str = Field(min_length=1, max_length=100, pattern=r"\S")
    unit_kind: Literal[
        "heat_exchanger", "vessel", "reactor", "pump", "compressor", "valve", "other"
    ] = "other"
    service: UnitService = Field(default_factory=UnitService)
    proposed_equipment: dict[str, float | str] = Field(
        default_factory=dict, max_length=30
    )
    evidence_ids: list[str] = Field(default_factory=list, max_length=20)
    hypothesis: str = Field(default="", max_length=2000)
    counter_evidence: str = Field(default="", max_length=2000)
    baseline_history: list[EngineeringBaseline] = Field(
        default_factory=list, max_length=20
    )

    @model_validator(mode="after")
    def pressure_temperature(self):
        s = self.service
        if (
            s.normal_temperature_c is not None
            and s.design_temperature_c is not None
            and s.design_temperature_c < s.normal_temperature_c
        ):
            raise ValueError(
                "Design temperature cannot be below the stated normal temperature"
            )
        if len(set(self.evidence_ids)) != len(self.evidence_ids):
            raise ValueError("Duplicate engineering evidence reference")
        return self
