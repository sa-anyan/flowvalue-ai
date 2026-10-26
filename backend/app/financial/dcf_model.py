"""Unlevered, constant-dollar DCF and reproducible project-level cost uncertainty."""

from math import expm1, fsum

import numpy as np
from pydantic import Field, model_validator
from scipy.optimize import brentq
from scipy.special import logsumexp
from scipy.stats import uniform

from app.engine.costing import Model


class FinancialAssumptions(Model):
    fixed_opex_usd_per_year: float = Field(default=0, ge=0, le=1e15)
    variable_opex_usd_per_year: float = Field(default=0, ge=0, le=1e15)
    # These are components of variable OPEX, not additional expenses.
    feedstock_opex_usd_per_year: float = Field(default=0, ge=0, le=1e15)
    utility_opex_usd_per_year: float = Field(default=0, ge=0, le=1e15)
    plant_capacity_units_per_year: float = Field(ge=1e-9, le=1e15)
    capacity_factor: float = Field(default=1, ge=1e-9, le=1)
    product_selling_price_usd_per_unit: float = Field(ge=0, le=1e12)
    tax_rate: float = Field(default=0.21, ge=0, le=1)
    discount_rate: float = Field(default=0.1, ge=0, le=10)
    operating_years: int = Field(default=20, ge=1, le=100)
    depreciation_years: int | None = Field(default=None, ge=1, le=100)

    @model_validator(mode="after")
    def opex_components(self):
        if (
            self.feedstock_opex_usd_per_year + self.utility_opex_usd_per_year
            > self.variable_opex_usd_per_year
        ):
            raise ValueError(
                "Feedstock and utility costs must be components of total variable OPEX"
            )
        return self


class FinancialInputs(FinancialAssumptions):
    total_capex_usd: float = Field(ge=1e-6, le=1e15)


class CashFlowYear(Model):
    year: int
    production_units: float
    revenue_usd: float
    fixed_opex_usd: float
    variable_opex_usd: float
    opex_usd: float
    depreciation_usd: float
    taxable_income_usd: float
    taxes_usd: float
    net_income_usd: float
    capital_expenditure_usd: float
    free_cash_flow_usd: float
    discounted_free_cash_flow_usd: float
    cumulative_free_cash_flow_usd: float
    cumulative_discounted_free_cash_flow_usd: float


class FinancialResult(Model):
    inputs: FinancialInputs
    cash_flows: list[CashFlowYear]
    npv_usd: float
    irr: float | None
    dcfror: float | None
    payback_years: float | None
    discounted_payback_years: float | None
    lcop_usd_per_unit: float
    assumptions: list[str]
    warnings: list[str]


def payback(cash_flows: list[float]) -> float | None:
    cumulative = cash_flows[0]
    for year, value in enumerate(cash_flows[1:], start=1):
        if cumulative < 0 <= cumulative + value:
            return year - 1 + (-cumulative / value)
        cumulative += value
    return None


def internal_rate_of_return(cash_flows: list[float]) -> float | None:
    """Unique IRR for this engine's single initial investment and nonnegative returns.

    Solve in log(1+r) space to handle negative rates and long lives stably.
    No fabricated rate for projects without a positive operating return.
    """
    operating = np.asarray(cash_flows[1:], dtype=float)
    if not np.any(operating > 0):
        return None
    if np.any(operating < 0):
        raise ValueError(
            "IRR requires conventional cash flows; multiple-sign changes unsupported"
        )
    periods = np.arange(1, len(cash_flows))[operating > 0]
    log_returns = np.log(operating[operating > 0]) - np.log(-cash_flows[0])
    lower = float(np.min(log_returns / periods)) - 1
    upper = float(np.max((log_returns + np.log(len(periods))) / periods)) + 1
    root = brentq(lambda y: float(logsumexp(log_returns - periods * y)), lower, upper)
    rate = expm1(root)
    return rate if rate > -1 else None


def calculate_dcf(inputs: FinancialInputs) -> FinancialResult:
    years = inputs.operating_years
    depreciation_years = inputs.depreciation_years or years
    production = inputs.plant_capacity_units_per_year * inputs.capacity_factor
    revenue = production * inputs.product_selling_price_usd_per_unit
    opex = inputs.fixed_opex_usd_per_year + inputs.variable_opex_usd_per_year
    rows = [
        CashFlowYear(
            year=0,
            production_units=0,
            revenue_usd=0,
            fixed_opex_usd=0,
            variable_opex_usd=0,
            opex_usd=0,
            depreciation_usd=0,
            taxable_income_usd=0,
            taxes_usd=0,
            net_income_usd=0,
            capital_expenditure_usd=inputs.total_capex_usd,
            free_cash_flow_usd=-inputs.total_capex_usd,
            discounted_free_cash_flow_usd=-inputs.total_capex_usd,
            cumulative_free_cash_flow_usd=-inputs.total_capex_usd,
            cumulative_discounted_free_cash_flow_usd=-inputs.total_capex_usd,
        )
    ]
    for year in range(1, years + 1):
        depreciation = (
            inputs.total_capex_usd / depreciation_years
            if year <= depreciation_years
            else 0
        )
        taxable_income = revenue - opex - depreciation
        taxes = max(0, taxable_income) * inputs.tax_rate
        net_income = taxable_income - taxes
        fcf = revenue - opex - taxes
        discounted = fcf / (1 + inputs.discount_rate) ** year
        rows.append(
            CashFlowYear(
                year=year,
                production_units=production,
                revenue_usd=revenue,
                fixed_opex_usd=inputs.fixed_opex_usd_per_year,
                variable_opex_usd=inputs.variable_opex_usd_per_year,
                opex_usd=opex,
                depreciation_usd=depreciation,
                taxable_income_usd=taxable_income,
                taxes_usd=taxes,
                net_income_usd=net_income,
                capital_expenditure_usd=0,
                free_cash_flow_usd=fcf,
                discounted_free_cash_flow_usd=discounted,
                cumulative_free_cash_flow_usd=rows[-1].cumulative_free_cash_flow_usd
                + fcf,
                cumulative_discounted_free_cash_flow_usd=rows[
                    -1
                ].cumulative_discounted_free_cash_flow_usd
                + discounted,
            )
        )
    flows = [row.free_cash_flow_usd for row in rows]
    discounted_flows = [row.discounted_free_cash_flow_usd for row in rows]
    irr = internal_rate_of_return(flows)
    # Pre-tax LCOP: discounted capital and operating costs / discounted production.
    annuity = fsum((1 + inputs.discount_rate) ** -year for year in range(1, years + 1))
    lcop = (inputs.total_capex_usd / annuity + opex) / production
    warnings = []
    if irr is None:
        warnings.append(
            "IRR/DCFROR undefined: no positive operating cash flow or rate indistinguishable from -100%"
        )
    return FinancialResult(
        inputs=inputs,
        cash_flows=rows,
        npv_usd=fsum(discounted_flows),
        irr=irr,
        dcfror=irr,
        payback_years=payback(flows),
        discounted_payback_years=payback(discounted_flows),
        lcop_usd_per_unit=lcop,
        assumptions=[
            "USD, constant-dollar unlevered project; rates as decimals",
            "Year-zero CAPEX, end-of-year cash flows, constant annual production and OPEX",
            "Annual OPEX inputs reflect the selected capacity factor; not scaled again",
            "Full CAPEX depreciated straight-line; default depreciation life equals operating life",
            "Taxes floored at zero; no loss carryforward, debt, working capital, salvage, escalation or credits",
            "LCOP is pre-tax discounted (CAPEX + OPEX) / discounted production",
            "Payback uses linear interpolation within the recovery year; null if unrecovered",
            "IRR and DCFROR are the same annual project return",
        ],
        warnings=warnings,
    )


class MonteCarloSettings(Model):
    iterations: int = Field(default=1000, ge=1, le=10000)
    variation_fraction: float = Field(default=0.2, ge=0, le=1)
    seed: int = Field(default=42, ge=0, le=2**32 - 1)


class MonteCarloRequest(Model):
    financial: FinancialInputs
    simulation: MonteCarloSettings = Field(default_factory=MonteCarloSettings)


class MonteCarloResult(Model):
    iterations: int
    seed: int
    variation_fraction: float
    p10_npv_usd: float
    p50_npv_usd: float
    p90_npv_usd: float
    mean_npv_usd: float
    probability_positive_npv: float
    min_npv_usd: float
    max_npv_usd: float
    distribution: str
    warnings: list[str]


def monte_carlo(
    inputs: FinancialInputs, settings: MonteCarloSettings | None = None
) -> MonteCarloResult:
    settings = settings or MonteCarloSettings()
    rng = np.random.default_rng(settings.seed)
    if settings.variation_fraction == 0:
        multipliers = np.ones((settings.iterations, 2))
    else:
        multipliers = uniform.rvs(
            loc=1 - settings.variation_fraction,
            scale=2 * settings.variation_fraction,
            size=(settings.iterations, 2),
            random_state=rng,
        )
    variable = (
        inputs.variable_opex_usd_per_year
        + inputs.feedstock_opex_usd_per_year * (multipliers[:, 0] - 1)
        + inputs.utility_opex_usd_per_year * (multipliers[:, 1] - 1)
    )
    # One independent draw per cost driver per scenario, held constant across project life.
    periods = np.arange(1, inputs.operating_years + 1)
    depreciation_years = inputs.depreciation_years or inputs.operating_years
    depreciation = np.where(
        periods <= depreciation_years, inputs.total_capex_usd / depreciation_years, 0
    )
    revenue = (
        inputs.plant_capacity_units_per_year
        * inputs.capacity_factor
        * inputs.product_selling_price_usd_per_unit
    )
    margin = revenue - inputs.fixed_opex_usd_per_year - variable[:, None]
    taxes = np.maximum(0, margin - depreciation) * inputs.tax_rate
    samples = -inputs.total_capex_usd + np.sum(
        (margin - taxes) / (1 + inputs.discount_rate) ** periods, axis=1
    )
    p10, p50, p90 = np.percentile(samples, [10, 50, 90])
    warnings = []
    if inputs.feedstock_opex_usd_per_year == inputs.utility_opex_usd_per_year == 0:
        warnings.append(
            "No feedstock or utility exposure supplied; NPV distribution is constant"
        )
    return MonteCarloResult(
        iterations=settings.iterations,
        seed=settings.seed,
        variation_fraction=settings.variation_fraction,
        p10_npv_usd=float(p10),
        p50_npv_usd=float(p50),
        p90_npv_usd=float(p90),
        mean_npv_usd=float(np.mean(samples)),
        probability_positive_npv=float(np.mean(samples > 0)),
        min_npv_usd=float(np.min(samples)),
        max_npv_usd=float(np.max(samples)),
        distribution="Independent uniform feedstock/utility price multipliers; fixed consumption; lifetime scenario draws; P10/P50/P90 are ascending NPV percentiles",
        warnings=warnings,
    )
