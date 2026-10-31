"""Canonical immutable financial inputs and the single annual ledger."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from backend.capex.models import number
from backend.revenue.models import Assumption


def numeric(instance, names):
    for name in names:
        object.__setattr__(instance, name, number(getattr(instance, name), name))


def tuples(instance, pairs):
    for name, cls in pairs:
        value = getattr(instance, name)
        if not isinstance(value, tuple) or not all(isinstance(x, cls) for x in value):
            raise TypeError(name + " must be an immutable tuple of " + cls.__name__)


def contracts(instance, pairs):
    for name, cls in pairs:
        if not isinstance(getattr(instance, name), cls):
            raise TypeError(name + " must be " + cls.__name__)


@dataclass(frozen=True)
class Money:
    amount: Decimal | None
    currency: str
    price_year: int
    source: str

    def __post_init__(self):
        if self.amount is not None:
            numeric(self, ("amount",))
        if (
            not isinstance(self.currency, str)
            or not self.currency.strip()
            or not isinstance(self.source, str)
            or not self.source.strip()
        ):
            raise ValueError("Money needs currency and source")
        if (
            len(self.currency) != 3
            or not self.currency.isalpha()
            or not self.currency.isupper()
        ):
            raise ValueError("Use an explicit uppercase three-letter currency code")
        if (
            isinstance(self.price_year, bool)
            or not isinstance(self.price_year, int)
            or not 1900 <= self.price_year <= 9999
        ):
            raise ValueError("Explicit price year required")


@dataclass(frozen=True)
class ExchangeRate:
    currency: str
    calendar_year: int
    project_currency_per_unit: Assumption

    def __post_init__(self):
        contracts(self, (("project_currency_per_unit", Assumption),))
        if type(self.calendar_year) is not int or not self.currency:
            raise ValueError("Explicit currency and calendar year required for FX")


@dataclass(frozen=True)
class Spend:
    year: int
    fraction: Assumption

    def __post_init__(self):
        contracts(self, (("fraction", Assumption),))
        if type(self.year) is not int or self.year < 0:
            raise ValueError("Spending year must be a nonnegative integer")


@dataclass(frozen=True)
class DatedMoney:
    year: int
    money: Money

    def __post_init__(self):
        contracts(self, (("money", Money),))
        if type(self.year) is not int or self.year < 0:
            raise ValueError("Money year must be a nonnegative integer")


@dataclass(frozen=True)
class DepreciationPolicy:
    method: str
    service_year: int
    life: int
    depreciable_fraction: Assumption
    residual_basis: Money
    declining_factor: Assumption | None
    switch_to_straight_line: bool
    macrs_rates: tuple[Assumption, ...]
    source: str
    jurisdiction_and_convention: str

    def __post_init__(self):
        tuples(self, (("macrs_rates", Assumption),))
        contracts(
            self, (("depreciable_fraction", Assumption), ("residual_basis", Money))
        )
        if self.declining_factor is not None and not isinstance(
            self.declining_factor, Assumption
        ):
            raise TypeError("Declining factor must be Assumption or None")
        if (
            type(self.switch_to_straight_line) is not bool
            or type(self.service_year) is not int
            or type(self.life) is not int
        ):
            raise TypeError(
                "Explicit depreciation integer years and boolean switch required"
            )


@dataclass(frozen=True)
class CapitalItem:
    id: str
    kind: str
    amount: Money
    spend: tuple[Spend, ...]
    depreciation: DepreciationPolicy
    disposal_year: int
    disposal_proceeds: Money
    startup_treatment: str
    price_treatment: str
    escalation: Assumption | None = None
    disposal_price_treatment: str = "actual"
    disposal_escalation: Assumption | None = None

    def __post_init__(self):
        tuples(self, (("spend", Spend),))
        contracts(
            self,
            (
                ("amount", Money),
                ("depreciation", DepreciationPolicy),
                ("disposal_proceeds", Money),
            ),
        )


@dataclass(frozen=True)
class Activity:
    id: str
    value: Decimal
    unit: str
    source: str

    def __post_init__(self):
        numeric(self, ("value",))


@dataclass(frozen=True)
class ProductSales:
    id: str
    unit: str
    produced: Decimal
    saleable: Decimal
    sold: Decimal
    revenue: Money
    source: str
    price_treatment: str = "actual"
    escalation: Assumption | None = None
    revenue_category: str = "product_sales"

    def __post_init__(self):
        numeric(self, ("produced", "saleable", "sold"))
        contracts(self, (("revenue", Money),))


@dataclass(frozen=True)
class OperatingCost:
    id: str
    category: str
    behavior: str
    classification: str
    amount: Money
    method: str
    driver_id: str
    reference_activity: Decimal | None
    driver_unit: str
    price_treatment: str
    escalation: Assumption | None = None

    def __post_init__(self):
        contracts(self, (("amount", Money),))
        if self.reference_activity is not None:
            numeric(self, ("reference_activity",))


@dataclass(frozen=True)
class Operation:
    year: int
    products: tuple[ProductSales, ...]
    costs: tuple[OperatingCost, ...]
    activities: tuple[Activity, ...]
    source: str

    def __post_init__(self):
        tuples(
            self,
            (
                ("products", ProductSales),
                ("costs", OperatingCost),
                ("activities", Activity),
            ),
        )
        if type(self.year) is not int or self.year < 0:
            raise ValueError("Financial operation year must be a nonnegative integer")


@dataclass(frozen=True)
class TaxPolicy:
    jurisdiction: str
    annual_rates: tuple[tuple[int, Assumption], ...]
    carry_losses: bool
    loss_expiry_years: int | None
    max_loss_offset: Assumption
    interest_deductible: bool
    closure_deductible: bool
    disposal_gains_taxable: bool
    depreciation_cogs_fraction: Assumption
    source: str
    annual_nonrefundable_credits: tuple[DatedMoney, ...] = ()
    credit_policy_source: str = ""

    def __post_init__(self):
        tuples(self, (("annual_nonrefundable_credits", DatedMoney),))
        if not isinstance(self.annual_rates, tuple) or not all(
            isinstance(x, tuple) and len(x) == 2 and isinstance(x[1], Assumption)
            for x in self.annual_rates
        ):
            raise TypeError(
                "Annual tax rates must be immutable (year, Assumption) pairs"
            )


@dataclass(frozen=True)
class WorkingCapitalPlan:
    requirements: tuple[DatedMoney, ...]
    recovery_year: int
    recovery_fraction: Assumption
    source: str

    def __post_init__(self):
        tuples(self, (("requirements", DatedMoney),))


@dataclass(frozen=True)
class DebtPlan:
    draws: tuple[DatedMoney, ...]
    interest_rate: Assumption
    repayment_start_year: int
    repayment_years: int
    method: str
    draw_timing: str
    balloon_at_shutdown: bool
    equity_mode: str
    equity_contributions: tuple[DatedMoney, ...]
    source: str

    def __post_init__(self):
        tuples(self, (("draws", DatedMoney), ("equity_contributions", DatedMoney)))


@dataclass(frozen=True)
class FinancialAssumptions:
    start_date: date
    construction_years: int
    commissioning_date: date
    first_production_date: date
    operating_years: int
    currency: str
    financial_base_year: int
    price_mode: str
    inflation: Assumption
    project_discount_rate: Assumption
    equity_discount_rate: Assumption
    discount_convention: str
    mirr_finance_rate: Assumption
    mirr_reinvestment_rate: Assumption
    exchange_rates: tuple[ExchangeRate, ...]
    tax: TaxPolicy
    working_capital: WorkingCapitalPlan
    debt: DebtPlan
    closure_cost: Money
    source: str
    closure_price_treatment: str = "actual"
    closure_escalation: Assumption | None = None

    def __post_init__(self):
        tuples(self, (("exchange_rates", ExchangeRate),))
        contracts(
            self,
            (
                ("tax", TaxPolicy),
                ("working_capital", WorkingCapitalPlan),
                ("debt", DebtPlan),
                ("closure_cost", Money),
            ),
        )
        for key in (
            "inflation",
            "project_discount_rate",
            "equity_discount_rate",
            "mirr_finance_rate",
            "mirr_reinvestment_rate",
        ):
            contracts(self, ((key, Assumption),))
        for value in (
            self.start_date,
            self.commissioning_date,
            self.first_production_date,
        ):
            if type(value) is not date:
                raise TypeError("Use explicit date objects, not ambiguous date strings")


@dataclass(frozen=True)
class FinancialInputs:
    id: str
    assumptions: FinancialAssumptions
    capital: tuple[CapitalItem, ...]
    operations: tuple[Operation, ...]
    model_id: str = "garrett"
    revision: int = 1
    parent_snapshot_id: str = ""
    actor: str = "user"
    change_reason: str = "Initial financial scenario"
    source_references: tuple[str, ...] = ()
    upstream_snapshots_json: str = "{}"

    def __post_init__(self):
        if not isinstance(self.assumptions, FinancialAssumptions):
            raise TypeError("FinancialAssumptions required")
        tuples(
            self,
            (
                ("capital", CapitalItem),
                ("operations", Operation),
                ("source_references", str),
            ),
        )


@dataclass(frozen=True)
class Period:
    year: int
    start: date
    end: date
    calendar_year: int
    operating_fraction: Decimal


@dataclass(frozen=True)
class Metric:
    value: Decimal | None
    unit: str
    status: str
    basis: str
    alternatives: tuple[Decimal, ...] = ()


@dataclass(frozen=True)
class TaxResult:
    taxable_before_losses: Decimal
    losses_used: Decimal
    tax: Decimal
    carry_lots: tuple[tuple[int, Decimal], ...]
    credit_used: Decimal = Decimal(0)


@dataclass(frozen=True)
class DebtRow:
    opening: Decimal
    draw: Decimal
    interest: Decimal
    principal: Decimal
    closing: Decimal


@dataclass(frozen=True)
class AnnualLedger:
    period: Period
    products: tuple[ProductSales, ...]
    cost_breakdown: tuple[tuple[str, str, Decimal], ...]
    capital_breakdown: tuple[tuple[str, str, Decimal], ...]
    revenue: Decimal
    fixed_opex: Decimal
    variable_opex: Decimal
    cogs: Decimal | None
    gross_profit: Decimal | None
    startup_expense: Decimal
    closure_expense: Decimal
    ebitda: Decimal
    depreciation: Decimal
    ebit: Decimal
    disposal_gain: Decimal
    interest: Decimal
    profit_before_tax: Decimal
    income_tax: Decimal
    net_income: Decimal
    project_tax: Decimal
    project_loss_carry: Decimal
    equity_loss_carry: Decimal
    capex: Decimal
    disposal_proceeds: Decimal
    working_capital_opening: Decimal
    working_capital_change: Decimal
    working_capital_recovery: Decimal
    working_capital_closing: Decimal
    debt: DebtRow
    cfads: Decimal
    dscr: Metric
    operating_cash_flow: Decimal
    investing_cash_flow: Decimal
    financing_cash_flow: Decimal
    fcff: Decimal
    fcfe: Decimal
    equity_contribution: Decimal
    equity_distribution: Decimal
    closing_cash: Decimal
    recurring_project_cash: Decimal
    point_project_cash: Decimal
    recurring_equity_cash: Decimal
    point_equity_cash: Decimal
    cumulative_project_cash: Decimal
    cumulative_equity_cash: Decimal
    discounted_project_cash: Decimal
    discounted_equity_cash: Decimal
    project_credit_used: Decimal
    equity_credit_used: Decimal


@dataclass(frozen=True)
class FinancialResult:
    model_id: str
    snapshot_id: str
    status: str
    ledger: tuple[AnnualLedger, ...]
    metrics: tuple[tuple[str, Metric], ...]
    issues: tuple[str, ...]
    warnings: tuple[str, ...]
    assumptions_json: str
    sources: tuple[str, ...]
    currency: str
    price_mode: str
    financial_base_year: int
    discount_convention: str
