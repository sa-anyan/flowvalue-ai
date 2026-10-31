"""Immutable annual OPEX contracts. Amounts use one explicitly stated price basis."""

import hashlib
import json
from dataclasses import asdict, dataclass, replace
from decimal import Decimal

from backend.capex.models import Source, number


def text_fields(instance, names):
    for name in names:
        if not isinstance(getattr(instance, name), str):
            raise TypeError(name + " must be text")


@dataclass(frozen=True)
class Category:
    id: str
    minimum: str | None
    maximum: str | None
    base: str | None
    applicability: str
    source: Source
    accounting: str = "cash"
    required: bool = True
    note: str = ""


@dataclass(frozen=True)
class Basis:
    currency: str
    price_period: str

    def __post_init__(self):
        text_fields(self, ("currency", "price_period"))
        if not self.currency.strip() or not self.price_period.strip():
            raise ValueError("Currency and price period are required")


@dataclass(frozen=True)
class MoneyBase:
    id: str
    amount: Decimal
    basis: Basis
    source: str

    def __post_init__(self):
        text_fields(self, ("id", "source"))
        object.__setattr__(self, "amount", number(self.amount, self.id))
        if not self.id or not self.source.strip() or not isinstance(self.basis, Basis):
            raise ValueError("Named money bases need provenance and a price basis")


@dataclass(frozen=True)
class Assumption:
    id: str
    category: str
    method: str
    behavior: str  # fixed or variable; split mixed costs into explicit lines
    basis: Basis
    rationale: str
    source: str
    uncertainty: str
    # Namespaced scopes such as utilities:electricity; a bare category covers it all.
    scopes: tuple[str, ...]
    amount: Decimal | None = None
    quantity: Decimal | None = None  # annual consumption or FTE headcount
    rate: Decimal | None = None  # price/unit, annual salary/FTE, or fraction
    quantity_unit: str = ""
    rate_unit: str = ""
    base: str = ""  # named capital/revenue base, category:<id>, or item:<id>
    scope: str = "recurring"  # recurring, capex, working_capital
    override: bool = False
    override_reason: str = ""
    evidence: tuple[str, ...] = ()
    engineering_formula: str = ""  # evidence only; never evaluated

    def __post_init__(self):
        text_fields(
            self,
            (
                "id",
                "category",
                "method",
                "behavior",
                "rationale",
                "source",
                "uncertainty",
                "quantity_unit",
                "rate_unit",
                "base",
                "scope",
                "override_reason",
                "engineering_formula",
            ),
        )
        if not isinstance(self.override, bool):
            raise TypeError("override must be boolean")
        for key in ("amount", "quantity", "rate"):
            value = getattr(self, key)
            if value is not None:
                object.__setattr__(self, key, number(value, key))
        for key in ("scopes", "evidence"):
            value = getattr(self, key)
            if not isinstance(value, tuple) or not all(
                isinstance(v, str) for v in value
            ):
                raise TypeError(key + " must be an immutable tuple of strings")
        if not isinstance(self.basis, Basis):
            raise TypeError("basis must be Basis")


@dataclass(frozen=True)
class Exclusion:
    category: str
    rationale: str

    def __post_init__(self):
        text_fields(self, ("category", "rationale"))


@dataclass(frozen=True)
class OpexInputs:
    basis: Basis
    assumptions: tuple[Assumption, ...] = ()
    bases: tuple[MoneyBase, ...] = ()
    exclusions: tuple[Exclusion, ...] = ()
    reviewed_categories: tuple[str, ...] = ()
    process_description: str = ""
    location: str = ""
    # Serialized canonical engineering evidence retained unchanged, not interpreted.
    engineering_context_json: str = "{}"

    def __post_init__(self):
        text_fields(
            self, ("process_description", "location", "engineering_context_json")
        )
        if not isinstance(self.basis, Basis):
            raise TypeError("basis must be Basis")
        for name, cls in (
            ("assumptions", Assumption),
            ("bases", MoneyBase),
            ("exclusions", Exclusion),
        ):
            values = getattr(self, name)
            if not isinstance(values, tuple) or not all(
                isinstance(v, cls) for v in values
            ):
                raise TypeError(name + " must be an immutable tuple of " + cls.__name__)
        if not isinstance(self.reviewed_categories, tuple) or not all(
            isinstance(x, str) for x in self.reviewed_categories
        ):
            raise TypeError("reviewed_categories must be a tuple of strings")
        json.loads(self.engineering_context_json)


@dataclass(frozen=True)
class CostLine:
    id: str
    category: str
    amount: Decimal
    behavior: str
    accounting: str
    scope: str
    method: str
    calculation_base: str
    base_amount: Decimal | None
    source: str
    rationale: str
    uncertainty: str
    evidence: tuple[str, ...]
    scopes: tuple[str, ...]
    quantity: Decimal | None
    rate: Decimal | None
    quantity_unit: str
    rate_unit: str
    override_reason: str
    engineering_formula: str


@dataclass(frozen=True)
class OpexResult:
    model_id: str
    status: str
    basis: Basis
    snapshot_id: str
    cash_fixed: Decimal | None
    cash_variable: Decimal | None
    annual_cash_opex: Decimal | None
    depreciation: Decimal | None
    financing: Decimal | None
    annual_expense_including_depreciation_and_financing: Decimal | None
    resolved_cash_subtotal: Decimal
    excluded_capital: Decimal
    excluded_working_capital: Decimal
    lines: tuple[CostLine, ...]
    issues: tuple[str, ...]
    warnings: tuple[str, ...]
    methodology_source: Source


def freeze_assumptions(inputs):
    """Portable JSON snapshot, including source lineage; no mutable references."""
    if not isinstance(inputs, OpexInputs):
        raise TypeError("inputs must be OpexInputs")
    return json.dumps(
        asdict(inputs), default=str, sort_keys=True, separators=(",", ":")
    )


def snapshot_id(inputs):
    return hashlib.sha256(freeze_assumptions(inputs).encode()).hexdigest()


def restore_assumptions(snapshot):
    data = json.loads(snapshot)
    data["basis"] = Basis(**data["basis"])
    data["assumptions"] = tuple(
        Assumption(
            **dict(
                row,
                basis=Basis(**row["basis"]),
                scopes=tuple(row["scopes"]),
                evidence=tuple(row["evidence"]),
            )
        )
        for row in data["assumptions"]
    )
    data["bases"] = tuple(
        MoneyBase(**dict(row, basis=Basis(**row["basis"]))) for row in data["bases"]
    )
    data["exclusions"] = tuple(Exclusion(**row) for row in data["exclusions"])
    data["reviewed_categories"] = tuple(data["reviewed_categories"])
    return OpexInputs(**data)


def scenario(inputs, *, assumptions=None, **changes):
    """Return a new immutable scenario; the original baseline is untouched."""
    return replace(
        inputs,
        assumptions=inputs.assumptions if assumptions is None else assumptions,
        **changes,
    )
