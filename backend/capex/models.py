"""CAPEX contracts; no live costing calls or financial arithmetic by an LLM."""

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any


def number(value, name="value"):
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal, str)):
        raise TypeError(name + " must be a finite nonnegative number")
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError(name + " must be numeric") from exc
    if not result.is_finite() or result < 0:
        raise ValueError(name + " must be finite and nonnegative")
    return result


@dataclass(frozen=True)
class Source:
    reference: str
    filename: str
    sha256: str
    printed_page: int
    pdf_page: int
    note: str = ""


@dataclass(frozen=True)
class Factor:
    id: str
    minimum: str | None
    maximum: str | None
    base: str
    stage: str
    formula: str
    applicability: str
    source: Source
    alternatives: tuple[dict, ...] = ()
    additive: bool = True


@dataclass(frozen=True)
class Model:
    id: str
    title: str
    process_types: tuple[str, ...]
    requires_delivered_equipment: bool
    source: Source
    method: str
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class EquipmentCost:
    tag: str
    purchased_cost: Any
    currency: str
    period: str
    index_series: str
    index_value: Any
    quantity: Any = 1
    cost_scope: str = "purchased_equipment"
    delivery_basis: str = "unspecified"
    included_categories: tuple[str, ...] = ()
    provenance: dict = field(default_factory=dict)
    provisional: bool = False


@dataclass(frozen=True)
class Override:
    fraction: Any = None
    amount: Any = None
    rationale: str = ""
    source: str = "user assumption"


@dataclass(frozen=True)
class WorkingCapital:
    method: str = "model_default"
    fraction: Any = None
    annual_opex: Any = None
    installed_equipment_cost: Any = None
    months: Any = None
    amount: Any = None
    rationale: str = ""
    excluded: bool = False


@dataclass(frozen=True)
class CapexInputs:
    equipment: tuple[EquipmentCost, ...]
    process_type: str | None = None
    process_description: str = ""
    equipment_information: dict = field(default_factory=dict)
    factor_selection: str = "selected"
    selected_factors: dict = field(default_factory=dict)
    overrides: dict[str, Override] = field(default_factory=dict)
    exclusions: dict[str, str] = field(default_factory=dict)
    indirect_basis: str = "purchased_equipment"
    factor_basis_mode: str = "published_table"
    working_capital: WorkingCapital = field(default_factory=WorkingCapital)
    offsite_scope_confirmation: str | None = None


@dataclass(frozen=True)
class CostLine:
    id: str
    amount: Decimal | None
    fraction: Decimal | None
    base: str
    base_amount: Decimal | None
    formula: str
    status: str
    rationale: str
    source: Source


@dataclass(frozen=True)
class CapexResult:
    model_id: str
    process_type: str | None
    status: str
    purchased_equipment: Decimal | None
    direct_costs: Decimal | None
    indirect_costs: Decimal | None
    plant_cost: Decimal | None
    fixed_capital: Decimal | None
    startup_expenses: Decimal | None
    working_capital: Decimal | None
    total_capex: Decimal | None
    currency: str | None
    period: str | None
    index_series: str | None
    index_value: Decimal | None
    lines: tuple[CostLine, ...]
    issues: tuple[str, ...]
    assumptions: tuple[str, ...]
    evidence: dict
