"""B08 validation contracts for explicit handoff metadata and review fixtures."""

from datetime import date
from decimal import Decimal
from typing import Annotated, Literal, Self

from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, Field, model_validator


def decimal_input(value):
    if not isinstance(value, (Decimal, str, int)) or isinstance(value, bool):
        raise ValueError("Use Decimal, integer or decimal text")
    return value


def bounded_decimal(value: Decimal) -> Decimal:
    """Cap absolute magnitude at 1E+30, far above project-scale inputs.

    This catches unit and exponent errors without rounding valid decimals.
    """
    if value.is_finite() and value.copy_abs() > Decimal("1E+30"):
        raise ValueError("Decimal magnitude exceeds 1E+30")
    return value


ExactDecimal = Annotated[Decimal, BeforeValidator(decimal_input), AfterValidator(bounded_decimal)]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False, str_strip_whitespace=True)


class PriceBasis(Contract):
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    price_year: int = Field(strict=True, ge=1900, le=9999)
    price_date: date | None = None
    index_series: str | None = Field(default=None, min_length=1)
    index_value: ExactDecimal | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def consistent(self) -> Self:
        if self.price_date and self.price_date.year != self.price_year:
            raise ValueError("Price date and year disagree")
        if (self.index_series is None) != (self.index_value is None):
            raise ValueError("Index series and value must be supplied together")
        return self


class MonetaryLine(Contract):
    record_key: str = Field(min_length=1)
    amount: ExactDecimal | None
    status: Literal["present", "missing", "unresolved", "excluded", "not_applicable"]
    authority: Literal["provisional", "approved", "unknown"]
    representation: Literal["unit_price", "extended_total"]
    scope: str = Field(min_length=1)
    native_basis: PriceBasis
    comparison_basis: PriceBasis | None = None
    comparison_amount: ExactDecimal | None = None
    translation_ref: str | None = Field(default=None, min_length=1)
    unit: str | None = Field(default=None, min_length=1)
    quantity: ExactDecimal | None = Field(default=None, ge=0)
    quantity_unit: str | None = Field(default=None, min_length=1)
    source_ref: str = Field(min_length=1)
    approval_ref: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def consistent(self) -> Self:
        if (self.amount is not None) != (self.status == "present"):
            raise ValueError("Only present lines carry an amount")
        translated = (self.comparison_basis, self.comparison_amount, self.translation_ref)
        if any(value is not None for value in translated) and (
            self.amount is None or any(value is None for value in translated)
        ):
            raise ValueError("A translation requires native and comparison amounts, basis and reference")
        if (self.quantity is None) != (self.quantity_unit is None):
            raise ValueError("Quantity and quantity unit must be supplied together")
        if self.representation == "unit_price":
            if not self.unit or (self.quantity_unit and self.unit != self.quantity_unit):
                raise ValueError("Unit price requires a denominator matching any quantity unit")
        elif self.unit is not None:
            raise ValueError("Extended totals have no unit-price denominator")
        if self.authority == "approved" and self.status in {"missing", "unresolved"}:
            raise ValueError("Cannot approve a missing or unresolved amount")
        if (self.authority == "approved") != (self.approval_ref is not None):
            raise ValueError("Approval authority requires an approval reference")
        return self

    def comparison_issues(self, other: Self) -> tuple[str, ...]:
        """Check metadata compatibility only. Inclusion and summation require policy."""
        left = self.comparison_basis or self.native_basis
        right = other.comparison_basis or other.native_basis
        return tuple(
            label for label, matches in (
                ("amount_status", self.status == other.status == "present"),
                ("currency", left.currency == right.currency),
                ("price_period", (left.price_year, left.price_date) == (right.price_year, right.price_date)),
                ("index", (left.index_series, left.index_value) == (right.index_series, right.index_value)),
                ("scope", self.scope == other.scope),
                ("representation", self.representation == other.representation),
                ("unit", self.unit == other.unit),
            ) if not matches
        )


class TimelinePeriod(Contract):
    project_year: int = Field(strict=True, ge=0)
    calendar_year: int = Field(strict=True, ge=1, le=9999)
    operating_year: int | None = Field(default=None, strict=True, ge=1)
    phase: Literal["pre_operation", "construction", "startup", "operation", "closure"]

    @model_validator(mode="after")
    def consistent(self) -> Self:
        if self.phase == "operation" and self.operating_year is None:
            raise ValueError("An operating period requires an operating index")
        if self.operating_year is not None and self.phase not in {"startup", "operation"}:
            raise ValueError("Operating index belongs to a startup or operating period")
        return self


PHASE_ORDER = ("pre_operation", "construction", "startup", "operation", "closure")


class Timeline(Contract):
    periods: tuple[TimelinePeriod, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def consistent(self) -> Self:
        phase_order = [PHASE_ORDER.index(period.phase) for period in self.periods]
        if phase_order != sorted(phase_order):
            raise ValueError("Invalid timeline phase order")
        for previous, current in zip(self.periods, self.periods[1:]):
            if current.project_year != previous.project_year + 1 or current.calendar_year != previous.calendar_year + 1:
                raise ValueError("Project and calendar years must advance together")
        operating = tuple(p.project_year for p in self.periods if p.operating_year is not None)
        if self.periods[-1].phase == "closure" and not operating:
            raise ValueError("Invalid timeline phase order: closure requires prior operation")
        if operating:
            if operating != tuple(range(operating[0], operating[-1] + 1)):
                raise ValueError("Operating periods must be contiguous")
            indices = tuple(p.operating_year for p in self.periods if p.operating_year is not None)
            if indices != tuple(range(1, len(operating) + 1)):
                raise ValueError("Operating indices must start at 1 and advance consecutively")
        return self

    def uncovered_operating_years(self, approved_years: set[int]) -> tuple[int, ...]:
        return tuple(
            p.operating_year for p in self.periods
            if p.operating_year is not None and p.operating_year not in approved_years
        )
