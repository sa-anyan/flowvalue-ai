import numpy as np
import pytest
from pydantic import ValidationError
from scipy.stats import uniform

from app.financial.dcf_model import (
    FinancialInputs,
    MonteCarloSettings,
    calculate_dcf,
    internal_rate_of_return,
    monte_carlo,
)


def inputs(**changes):
    values = {
        "total_capex_usd": 1000,
        "plant_capacity_units_per_year": 100,
        "product_selling_price_usd_per_unit": 6,
        "operating_years": 2,
        "tax_rate": 0,
        "discount_rate": 0.1,
    }
    return FinancialInputs.model_validate(values | changes)


def test_two_year_hand_calculated_case():
    result = calculate_dcf(inputs())
    assert [r.free_cash_flow_usd for r in result.cash_flows] == [-1000, 600, 600]
    assert result.npv_usd == pytest.approx(-1000 + 600 / 1.1 + 600 / 1.21)
    assert result.irr == pytest.approx(0.1306623862918075)
    assert result.dcfror == result.irr
    assert result.payback_years == pytest.approx(1 + 400 / 600)
    assert result.discounted_payback_years == pytest.approx(
        1 + (1000 - 600 / 1.1) / (600 / 1.21)
    )
    assert result.lcop_usd_per_unit == pytest.approx(1000 / (100 / 1.1 + 100 / 1.21))
    at_return = sum(
        r.free_cash_flow_usd / (1 + result.irr) ** r.year for r in result.cash_flows
    )
    assert at_return == pytest.approx(0, abs=1e-7)


def test_depreciation_taxes_and_no_loss_refund():
    result = calculate_dcf(
        inputs(tax_rate=0.25, fixed_opex_usd_per_year=100, depreciation_years=1)
    )
    first, second = result.cash_flows[1:]
    assert first.depreciation_usd == 1000
    assert first.taxable_income_usd == -500
    assert first.taxes_usd == 0
    assert first.free_cash_flow_usd == 500
    assert second.depreciation_usd == 0
    assert second.taxes_usd == 125
    assert second.net_income_usd == 375
    assert second.free_cash_flow_usd == 375


def test_zero_discount_lcop_and_capacity_factor():
    result = calculate_dcf(
        inputs(discount_rate=0, capacity_factor=0.5, fixed_opex_usd_per_year=100)
    )
    assert result.cash_flows[1].production_units == 50
    assert result.npv_usd == -600
    assert result.lcop_usd_per_unit == 12
    assert result.discounted_payback_years is None


def test_loss_making_and_negative_irr():
    loss = calculate_dcf(
        inputs(product_selling_price_usd_per_unit=0, fixed_opex_usd_per_year=100)
    )
    assert loss.irr is None
    assert loss.payback_years is None
    assert loss.discounted_payback_years is None
    assert loss.warnings
    negative = calculate_dcf(inputs(product_selling_price_usd_per_unit=4))
    assert -1 < negative.irr < 0
    assert negative.payback_years is None


def test_long_lived_negative_return_stability():
    result = calculate_dcf(
        inputs(operating_years=100, product_selling_price_usd_per_unit=0.001)
    )
    assert -1 < result.irr < 0
    assert internal_rate_of_return([-100, 100]) == pytest.approx(0, abs=1e-10)
    with pytest.raises(ValueError):
        internal_rate_of_return([-100, 200, -50])


def test_zero_variance_matches_dcf_with_depreciation_cutoff():
    case = inputs(
        variable_opex_usd_per_year=120,
        feedstock_opex_usd_per_year=60,
        utility_opex_usd_per_year=50,
        depreciation_years=1,
        tax_rate=0.25,
    )
    result = monte_carlo(case, MonteCarloSettings(variation_fraction=0))
    assert result.p10_npv_usd == pytest.approx(calculate_dcf(case).npv_usd)
    assert result.p10_npv_usd == result.p50_npv_usd == result.p90_npv_usd


def test_monte_carlo_reproducible_and_independent_reference():
    case = inputs(
        variable_opex_usd_per_year=200,
        feedstock_opex_usd_per_year=100,
        utility_opex_usd_per_year=50,
        tax_rate=0.25,
        depreciation_years=1,
    )
    settings = MonteCarloSettings(seed=17)
    result = monte_carlo(case, settings)
    assert result == monte_carlo(case, settings)
    assert result.p10_npv_usd < result.p50_npv_usd < result.p90_npv_usd
    assert result != monte_carlo(case, MonteCarloSettings(seed=18))
    draws = uniform.rvs(
        loc=0.8, scale=0.4, size=(1000, 2), random_state=np.random.default_rng(17)
    )
    reference = []
    for feed, utility in draws:
        annual_opex = 50 + feed * 100 + utility * 50
        margin = 600 - annual_opex
        reference.append(-1000 + margin / 1.1 + (margin * 0.75) / 1.21)
    assert result.p10_npv_usd == pytest.approx(np.percentile(reference, 10))
    assert result.p50_npv_usd == pytest.approx(np.percentile(reference, 50))
    assert result.p90_npv_usd == pytest.approx(np.percentile(reference, 90))
    low_cost = calculate_dcf(
        case.model_copy(update={"variable_opex_usd_per_year": 170})
    ).npv_usd
    high_cost = calculate_dcf(
        case.model_copy(update={"variable_opex_usd_per_year": 230})
    ).npv_usd
    assert high_cost <= result.min_npv_usd <= result.max_npv_usd <= low_cost


def test_no_exposure_warns():
    result = monte_carlo(inputs())
    assert result.warnings
    assert result.p10_npv_usd == result.p90_npv_usd


@pytest.mark.parametrize(
    "changes",
    [
        {"total_capex_usd": 0},
        {"discount_rate": -1},
        {"tax_rate": 1.1},
        {"plant_capacity_units_per_year": 0},
        {"operating_years": 0},
        {"fixed_opex_usd_per_year": float("inf")},
        {"feedstock_opex_usd_per_year": 1},
    ],
)
def test_invalid_financial_inputs(changes):
    with pytest.raises(ValidationError):
        inputs(**changes)


def test_financial_api_and_assessment_capex():
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)
    direct = client.post("/api/financial/dcf", json=inputs().model_dump())
    assert direct.status_code == 200
    assert direct.json()["npv_usd"] == pytest.approx(calculate_dcf(inputs()).npv_usd)
    assumptions = inputs().model_dump(exclude={"total_capex_usd"})
    payload = {
        "costing": {
            "equipment": [
                {
                    "kind": "heat_exchanger",
                    "unit_id": "E1",
                    "duty_kw": 1000,
                    "overall_u_w_m2_k": 500,
                    "lmtd_k": 20,
                    "quantity": 2,
                }
            ]
        },
        "financial": assumptions,
        "simulation": {"iterations": 1000},
    }
    response = client.post("/api/assessment", json=payload)
    assert response.status_code == 200, response.text
    result = response.json()
    assert (
        result["financial"]["inputs"]["total_capex_usd"]
        == result["bom"]["total_bare_module_cost_usd"]
    )
    assert result["uncertainty"]["iterations"] == 1000
    assert (
        result["financial"]["cash_flows"][0]["free_cash_flow_usd"]
        == -result["bom"]["total_bare_module_cost_usd"]
    )
    payload["financial"]["total_capex_usd"] = 1
    assert client.post("/api/assessment", json=payload).status_code == 422
    mc = client.post(
        "/api/financial/monte-carlo", json={"financial": inputs().model_dump()}
    )
    assert mc.status_code == 200
    assert mc.json()["iterations"] == 1000
    assert (
        client.post(
            "/api/financial/monte-carlo",
            json={
                "financial": inputs().model_dump(),
                "simulation": {"iterations": 10001},
            },
        ).status_code
        == 422
    )


def test_tiny_positive_revenue_still_has_negative_irr():
    result = calculate_dcf(
        inputs(operating_years=1, product_selling_price_usd_per_unit=1e-100)
    )
    assert result.cash_flows[1].free_cash_flow_usd == pytest.approx(1e-98)
    # For rates closer to -1 than floating point can represent, report null rather than -100%.
    assert result.irr is None or result.irr > -1
