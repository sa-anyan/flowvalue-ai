"""Frozen revenue contracts. Commercial assumptions are not physical evidence."""

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from backend.equipment_costing.unit_conversion import ConversionContext
from backend.opex.models import Basis, text_fields


def immutable(values, cls, name):
    if not isinstance(values, tuple) or not all(isinstance(v, cls) for v in values):
        raise TypeError(name + " must be a tuple of " + cls.__name__)


@dataclass(frozen=True)
class Assumption:
    value: Decimal | None
    unit: str
    rationale: str
    source: str
    uncertainty: str
    status: str = "user_assumption"
    as_of: str = ""

    def __post_init__(self):
        text_fields(
            self, ("unit", "rationale", "source", "uncertainty", "status", "as_of")
        )
        if self.value is not None:
            if isinstance(self.value, bool) or not isinstance(
                self.value, (Decimal, int, float, str)
            ):
                raise TypeError("Assumption value must be finite numeric or None")
            try:
                value = Decimal(str(self.value))
            except InvalidOperation as exc:
                raise ValueError("Invalid numeric assumption") from exc
            if not value.is_finite():
                raise ValueError("Nonfinite assumption")
            object.__setattr__(self, "value", value)


@dataclass(frozen=True)
class Stream:
    id: str
    name: str
    flow: Assumption
    source_references: tuple[str, ...]
    boundary: str = "unresolved"
    specifications: str = ""
    conversion_context: ConversionContext = field(default_factory=ConversionContext)

    def __post_init__(self):
        text_fields(self, ("id", "name", "boundary", "specifications"))
        immutable(self.source_references, str, "source_references")
        if not isinstance(self.flow, Assumption) or not isinstance(
            self.conversion_context, ConversionContext
        ):
            raise TypeError(
                "Stream needs a sourced flow and canonical conversion context"
            )


@dataclass(frozen=True)
class OperatingYear:
    year: int
    operating_hours: Assumption
    throughput_fraction: Assumption

    def __post_init__(self):
        if (
            isinstance(self.year, bool)
            or not isinstance(self.year, int)
            or self.year < 1
        ):
            raise ValueError("Use positive integer operating years")
        if not isinstance(self.operating_hours, Assumption) or not isinstance(
            self.throughput_fraction, Assumption
        ):
            raise TypeError("Annual operation requires explicit assumptions")


@dataclass(frozen=True)
class Adjustment:
    id: str
    cost_scope: str
    direction: str  # premium or deduction
    method: str  # per_unit or fraction_of_quote
    assumption: Assumption
    accounting: str = "revenue"  # revenue, opex, included_in_quote

    def __post_init__(self):
        text_fields(self, ("id", "cost_scope", "direction", "method", "accounting"))
        if not isinstance(self.assumption, Assumption):
            raise TypeError("Adjustment assumption required")


@dataclass(frozen=True)
class MarketStudy:
    geography: str
    customer_requirements: str
    competitors_and_capacity: tuple[str, ...] = ()
    prospective_customers: tuple[str, ...] = ()
    historical_context: str = ""
    base_year: int = 1
    base_demand: Assumption | None = None
    annual_growth: Assumption | None = None
    reference: str = ""

    def __post_init__(self):
        text_fields(
            self,
            ("geography", "customer_requirements", "historical_context", "reference"),
        )
        immutable(self.competitors_and_capacity, str, "competitors")
        immutable(self.prospective_customers, str, "prospective customers")
        if (
            isinstance(self.base_year, bool)
            or not isinstance(self.base_year, int)
            or self.base_year < 1
        ):
            raise ValueError("Market base year must be a positive integer")
        for value in (self.base_demand, self.annual_growth):
            if value is not None and not isinstance(value, Assumption):
                raise TypeError("Market quantities require assumptions")


@dataclass(frozen=True)
class ProductYear:
    year: int
    selling_price: Assumption
    sales_method: str  # fraction_of_saleable, explicit_quantity, market_share
    sales_assumption: Assumption
    adjustments: tuple[Adjustment, ...] = ()

    def __post_init__(self):
        if (
            isinstance(self.year, bool)
            or not isinstance(self.year, int)
            or self.year < 1
        ):
            raise ValueError("Product year must be a positive integer")
        if not isinstance(self.selling_price, Assumption) or not isinstance(
            self.sales_assumption, Assumption
        ):
            raise TypeError("Selling price and sales assumptions required")
        immutable(self.adjustments, Adjustment, "adjustments")


@dataclass(frozen=True)
class Product:
    id: str
    name: str
    stream_id: str
    role: str  # main_product or byproduct
    quantity_unit: str
    allocation_fraction: Assumption
    saleable_fraction: Assumption
    specification_basis: str
    specification_status: str
    price_basis: str  # net_fob or gross_quote
    price_terms: str
    included_charges: tuple[str, ...]
    additional_charge_scopes: tuple[str, ...]
    market: MarketStudy
    years: tuple[ProductYear, ...]
    included: bool = True
    reviewed: bool = False
    review_reason: str = ""
    exclusion_reason: str = ""

    def __post_init__(self):
        text_fields(
            self,
            (
                "id",
                "name",
                "stream_id",
                "role",
                "quantity_unit",
                "specification_basis",
                "specification_status",
                "price_basis",
                "price_terms",
                "review_reason",
                "exclusion_reason",
            ),
        )
        for name in ("allocation_fraction", "saleable_fraction"):
            if not isinstance(getattr(self, name), Assumption):
                raise TypeError(name + " assumption required")
        if not isinstance(self.market, MarketStudy):
            raise TypeError("Market study context required")
        immutable(self.included_charges, str, "included charges")
        immutable(self.additional_charge_scopes, str, "additional charges")
        immutable(self.years, ProductYear, "product years")
        if not isinstance(self.included, bool) or not isinstance(self.reviewed, bool):
            raise TypeError("Inclusion/review flags must be boolean")


@dataclass(frozen=True)
class PaymentYear:
    """Explicit operating-year billing schedule. Missing numbers remain None."""

    year: int
    quantity: Assumption
    rate: Assumption
    fixed_payment: Assumption
    minimum_quantity: Assumption
    minimum_payment: Assumption
    availability: Assumption
    escalation: Assumption
    periods: int = 1

    def __post_init__(self):
        if type(self.year) is not int or self.year < 1:
            raise ValueError("Positive integer commercial year required")
        for key in (
            "quantity",
            "rate",
            "fixed_payment",
            "minimum_quantity",
            "minimum_payment",
            "availability",
            "escalation",
        ):
            if not isinstance(getattr(self, key), Assumption):
                raise TypeError(
                    "Commercial billing values must use canonical Assumption"
                )


@dataclass(frozen=True)
class CommercialLine:
    id: str
    name: str
    category: str
    payment_id: str
    quantity_unit: str
    rate_period: str
    arrangement: str
    rationale: str
    source_references: tuple[str, ...]
    years: tuple[PaymentYear, ...]
    stream_id: str = ""
    included: bool = True
    fixed_variable_distinct: bool = False
    eligibility_basis: str = ""
    exclusion_reason: str = ""

    def __post_init__(self):
        text_fields(
            self,
            (
                "id",
                "name",
                "category",
                "payment_id",
                "quantity_unit",
                "rate_period",
                "arrangement",
                "rationale",
                "stream_id",
                "eligibility_basis",
                "exclusion_reason",
            ),
        )
        immutable(self.years, PaymentYear, "commercial years")
        immutable(self.source_references, str, "commercial sources")


@dataclass(frozen=True)
class AvoidedCost:
    id: str
    target_opex_id: str
    rationale: str
    years: tuple[tuple[int, Assumption], ...]
    already_applied: bool = False

    def __post_init__(self):
        text_fields(self, ("id", "target_opex_id", "rationale"))
        if not isinstance(self.years, tuple) or any(
            not isinstance(pair, tuple)
            or len(pair) != 2
            or type(pair[0]) is not int
            or not isinstance(pair[1], Assumption)
            for pair in self.years
        ):
            raise TypeError("Savings require immutable integer-year/Assumption pairs")


@dataclass(frozen=True)
class CommercialRevenue:
    line_id: str
    category: str
    payment_id: str
    year: int
    quantity: Decimal
    quantity_unit: str
    rate: Decimal
    fixed_payment: Decimal
    revenue: Decimal
    status: str
    source_references: tuple[str, ...]


@dataclass(frozen=True)
class RevenueProject:
    id: str
    basis: Basis
    streams: tuple[Stream, ...]
    schedule: tuple[OperatingYear, ...]
    products: tuple[Product, ...] = ()
    process_description: str = ""
    location: str = ""
    model_id: str = "garrett"
    revision: int = 1
    parent_snapshot_id: str = ""
    actor: str = "user"
    change_reason: str = "Initial draft"
    commercial_lines: tuple[CommercialLine, ...] = ()
    avoided_costs: tuple[AvoidedCost, ...] = ()

    def __post_init__(self):
        text_fields(
            self,
            (
                "id",
                "process_description",
                "location",
                "model_id",
                "parent_snapshot_id",
                "actor",
                "change_reason",
            ),
        )
        if not isinstance(self.basis, Basis):
            raise TypeError("Use canonical OPEX Basis for currency and price period")
        for key, cls in (
            ("streams", Stream),
            ("schedule", OperatingYear),
            ("products", Product),
            ("commercial_lines", CommercialLine),
            ("avoided_costs", AvoidedCost),
        ):
            immutable(getattr(self, key), cls, key)
        if (
            isinstance(self.revision, bool)
            or not isinstance(self.revision, int)
            or self.revision < 1
        ):
            raise ValueError("revision must be a positive integer")


@dataclass(frozen=True)
class ProductRevenue:
    product_id: str
    stream_id: str
    year: int
    quantity_unit: str
    normalized_flow_per_hour: Decimal
    produced_quantity: Decimal
    saleable_quantity: Decimal
    quantity_sold: Decimal
    unsold_saleable_quantity: Decimal
    market_demand: Decimal | None
    market_share: Decimal | None
    quoted_price: Decimal
    premium_per_unit: Decimal
    deduction_per_unit: Decimal
    net_selling_price: Decimal
    gross_sales: Decimal
    net_sales_revenue: Decimal
    opex_charges_separate: tuple[tuple[str, Decimal], ...]
    source_references: tuple[str, ...]


@dataclass(frozen=True)
class AnnualRevenue:
    year: int
    sales_revenue: Decimal
    separate_opex_charges: Decimal


@dataclass(frozen=True)
class RevenueResult:
    model_id: str
    snapshot_id: str
    status: str
    basis: Basis
    products: tuple[ProductRevenue, ...]
    annual: tuple[AnnualRevenue, ...]
    issues: tuple[str, ...]
    warnings: tuple[str, ...]
    source_reference: str
    commercial: tuple[CommercialRevenue, ...] = ()
    avoided_costs: tuple[AvoidedCost, ...] = ()
