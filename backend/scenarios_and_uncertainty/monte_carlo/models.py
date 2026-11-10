"""Strict, bounded simulation contracts; distributions are assumptions, not facts."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Parameter(Contract):
    @model_validator(mode="before")
    @classmethod
    def reject_boolean_quantities(cls, value):
        if isinstance(value, dict):
            for field in (
                "minimum",
                "mode",
                "maximum",
                "stddev",
                "hard_min",
                "hard_max",
            ):
                if isinstance(value.get(field), bool):
                    raise ValueError(
                        "Boolean is not a numerical assumption"
                    )  # noqa: TRY004 -- schema validation error
            if any(
                isinstance(v, bool)
                for field in ("choices", "probabilities")
                for v in value.get(field, [])
            ):
                raise ValueError("Boolean is not a numerical choice")
            if any(
                isinstance(v, bool) for path in value.get("targets", []) for v in path
            ):
                raise ValueError("Boolean is not a calculation path")
        return value

    id: str = Field(min_length=1, max_length=180)
    enabled: bool = False
    label: str = Field(max_length=240)
    targets: list[list[str | int]] = Field(min_length=1, max_length=100)
    unit: str = Field(max_length=80)
    distribution: Literal[
        "triangular", "uniform", "normal", "lognormal", "discrete"
    ] = "triangular"
    minimum: float | None = None
    mode: float | None = None
    maximum: float | None = None
    stddev: float | None = None
    choices: list[float | str] = Field(default_factory=list, max_length=40)
    probabilities: list[float] = Field(default_factory=list, max_length=40)
    source: str = Field(default="", max_length=3000)
    rationale: str = Field(default="", max_length=3000)
    uncertainty: str = Field(default="Not independently validated", max_length=2000)
    confidence: str = Field(
        default="Uncalibrated engineering assumption; no numeric confidence assigned",
        max_length=1000,
    )
    review_required: str = Field(default="", max_length=1500)
    hard_min: float | None = None
    hard_max: float | None = None
    strictly_positive: bool = False
    kind: Literal["engineering", "economic", "configuration"] = "engineering"


class Correlation(Contract):
    a: str
    b: str
    rho: float = Field(ge=-1, le=1)
    rationale: str = Field(min_length=1, max_length=2000)


class Alias(Contract):
    equipment_key: str
    target_key: str
    rationale: str = Field(min_length=1, max_length=2000)


class Distinct(Contract):
    equipment_key: str
    rationale: str = Field(min_length=1, max_length=2000)


class Settings(Contract):
    baseline_revision: int | None = None
    parameters: list[Parameter] = Field(default_factory=list, max_length=2_000)
    correlations: list[Correlation] = Field(default_factory=list, max_length=1000)
    distinct: list[Distinct] = Field(default_factory=list, max_length=100)
    aliases: list[Alias] = Field(default_factory=list, max_length=100)
    iterations: Literal[1000, 5000, 10000] = 1000
    seed: int = Field(default=42, ge=0, le=4294967295)
    operating_years: int = Field(default=20, ge=1, le=50)
    target_irr: float = Field(default=0.1, ge=-0.99, le=10)
    label: str = Field(default="Monte Carlo study", max_length=160)
