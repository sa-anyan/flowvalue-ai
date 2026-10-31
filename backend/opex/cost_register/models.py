"""Canonical expense ownership, shared inputs and alternative estimates."""

from dataclasses import dataclass
from decimal import Decimal

from ..models import Assumption, Basis, Exclusion, number, text_fields


def typed_tuple(value, cls, name):
    if not isinstance(value, tuple) or not all(isinstance(x, cls) for x in value):
        raise TypeError(name + " must be an immutable tuple of " + cls.__name__)


@dataclass(frozen=True)
class Evidence:
    kind: str  # garrett_allowance, user_assumption, supplier_quotation, engineering_calculation
    reference: str
    as_of: str  # ISO date; source/quote/assumption date, not proof of validity
    rationale: str
    uncertainty: str
    applicability: str
    # A citation or quotation never automatically earns verified status.

    def __post_init__(self):
        text_fields(
            self,
            ("kind", "reference", "as_of", "rationale", "uncertainty", "applicability"),
        )


@dataclass(frozen=True)
class SharedInput:
    id: str
    kind: str  # annual_quantity, demand, hours, headcount, unit_price, salary, fraction, annual_amount, capital_amount
    value: Decimal | None
    unit: str
    evidence: Evidence
    basis: Basis | None = None  # required for monetary inputs only

    def __post_init__(self):
        text_fields(self, ("id", "kind", "unit"))
        if self.value is not None:
            object.__setattr__(self, "value", number(self.value, self.id))
        if not isinstance(self.evidence, Evidence):
            raise TypeError("Shared input evidence required")
        if self.basis is not None and not isinstance(self.basis, Basis):
            raise TypeError("basis must be Basis or None")


@dataclass(frozen=True)
class AnnualConsumption:
    """A single shared demand × operating-hours result, not arbitrary expressions."""

    id: str
    demand_id: str
    hours_id: str
    unit: str  # explicit annual output unit, validated against demand units
    evidence: Evidence

    def __post_init__(self):
        text_fields(self, ("id", "demand_id", "hours_id", "unit"))
        if not isinstance(self.evidence, Evidence):
            raise TypeError("Engineering evidence required")


@dataclass(frozen=True)
class Binding:
    field: str  # amount, quantity or rate
    input_id: str

    def __post_init__(self):
        text_fields(self, ("field", "input_id"))


@dataclass(frozen=True)
class EstimateLine:
    template: Assumption
    bindings: tuple[Binding, ...] = ()

    def __post_init__(self):
        if not isinstance(self.template, Assumption):
            raise TypeError("template must be a canonical Assumption")
        typed_tuple(self.bindings, Binding, "bindings")


@dataclass(frozen=True)
class EstimateOption:
    id: str
    title: str
    lines: tuple[EstimateLine, ...]
    evidence: tuple[Evidence, ...]

    def __post_init__(self):
        text_fields(self, ("id", "title"))
        typed_tuple(self.lines, EstimateLine, "lines")
        typed_tuple(self.evidence, Evidence, "evidence")


@dataclass(frozen=True)
class Expense:
    id: str
    title: str
    category: str
    required_scopes: tuple[str, ...]
    options: tuple[EstimateOption, ...]
    active_option_id: str | None = None
    reviewed: bool = False
    selection_reason: str = ""

    def __post_init__(self):
        text_fields(self, ("id", "title", "category", "selection_reason"))
        typed_tuple(self.required_scopes, str, "required_scopes")
        typed_tuple(self.options, EstimateOption, "options")
        if self.active_option_id is not None and not isinstance(
            self.active_option_id, str
        ):
            raise TypeError("active_option_id must be text or None")
        if not isinstance(self.reviewed, bool):
            raise TypeError("reviewed must be boolean")


@dataclass(frozen=True)
class BaseBinding:
    base_id: str  # existing OPEX engine's named base, never a duplicate amount
    input_id: str

    def __post_init__(self):
        text_fields(self, ("base_id", "input_id"))


@dataclass(frozen=True)
class CostRegister:
    id: str
    basis: Basis
    expenses: tuple[Expense, ...] = ()
    inputs: tuple[SharedInput, ...] = ()
    annual_consumption: tuple[AnnualConsumption, ...] = ()
    bases: tuple[BaseBinding, ...] = ()
    exclusions: tuple[Exclusion, ...] = ()
    reviewed_categories: tuple[str, ...] = ()
    model_id: str = "garrett"
    process_description: str = ""
    location: str = ""
    engineering_context_json: str = "{}"
    revision: int = 1
    parent_snapshot_id: str = ""
    change_reason: str = "Initial draft"
    actor: str = "user"

    def __post_init__(self):
        text_fields(
            self,
            (
                "id",
                "model_id",
                "process_description",
                "location",
                "engineering_context_json",
                "parent_snapshot_id",
                "change_reason",
                "actor",
            ),
        )
        if not isinstance(self.basis, Basis):
            raise TypeError("basis must be Basis")
        if (
            isinstance(self.revision, bool)
            or not isinstance(self.revision, int)
            or self.revision < 1
        ):
            raise ValueError("revision must be a positive integer")
        for key, cls in (
            ("expenses", Expense),
            ("inputs", SharedInput),
            ("annual_consumption", AnnualConsumption),
            ("bases", BaseBinding),
            ("exclusions", Exclusion),
            ("reviewed_categories", str),
        ):
            typed_tuple(getattr(self, key), cls, key)
