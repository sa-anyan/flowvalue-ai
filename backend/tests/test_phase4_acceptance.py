"""Phase 4 acceptance: the roadmap's own test list, end to end.

Roadmap Phase 4 testing: a wastewater integration fixture must distinguish a
treatment service fee, a capacity reservation, pipeline usage, environmental
certificates, technology licensing and avoided treatment costs. Then one
assumption at a time is changed and the expected effect checked, including
contract expiry and renewal, partial-year operation, zero production,
unsold product and conflicting billing units.

All numbers are synthetic test inputs, not market prices or contracts.
"""

import copy
from dataclasses import replace
from decimal import Decimal as D

import pytest

from backend.capex import calculate_capex
from backend.orchestration.operating_economics import calculate_operating_study
from backend.revenue import calculate_revenue
from backend.revenue.authority import double_count_reviews
from backend.revenue.contract_terms import coverage
from backend.revenue.models import AvoidedCost
from backend.tests.test_capex import inputs
from backend.tests.test_operating_economics import DESCRIPTION
from backend.tests.test_operating_economics import fixture as operating_fixture
from backend.tests.test_revenue import a
from backend.tests.test_revenue_mece import config_line, line, project


def _payment(category, identity, *, quantity, rate, unit="m3", rate_unit=None,
             fixed=0, period="per_unit", eligibility=""):
    base = line(category, identity)
    year = replace(
        base.years[0],
        quantity=a(quantity, unit),
        rate=a(rate, rate_unit or f"GBP/{unit}"),
        fixed_payment=a(fixed, "GBP/year"),
        minimum_quantity=a(0, unit),
    )
    return replace(base, quantity_unit=unit, rate_period=period, years=(year,),
                   eligibility_basis=eligibility or base.eligibility_basis)


def six_mechanisms():
    """Five payments plus one avoided cost, on one wastewater plant."""
    lines = (
        _payment("processing_services", "treatment", quantity=1000, rate="0.50"),
        _payment("capacity_availability", "capacity", quantity=2000, rate="0.15",
                 rate_unit="GBP/m3/year", period="annual"),
        _payment("infrastructure_usage", "pipeline", quantity=1000, rate="0.25"),
        _payment("environmental_attributes", "certificates", quantity=10, rate=20,
                 unit="certificate", eligibility="Synthetic ownership assumption"),
        _payment("other_contractual_income", "licence", quantity=0, rate=0, fixed=1000),
    )
    saving = AvoidedCost("avoided-treatment", "opex:offsite-treatment",
                         "Synthetic counterfactual: no off-site treatment", ((1, a(400, "GBP/year")),))
    return project(*lines, savings=(saving,))


def test_six_mechanisms_are_distinct_and_avoided_cost_is_not_revenue():
    result = calculate_revenue(six_mechanisms())
    assert not result.issues
    by_id = {r.payment_id: r.revenue for r in result.commercial}
    assert by_id == {
        "treatment": D("500.00"), "capacity": D("300.00"), "pipeline": D("250.00"),
        "certificates": D("200"), "licence": D("1000"),
    }
    assert len({r.payment_id for r in result.commercial}) == 5  # each payment once
    assert {r.category for r in result.commercial} == {
        "processing_services", "capacity_availability", "infrastructure_usage",
        "environmental_attributes", "other_contractual_income"}
    # The avoided cost is carried for OPEX, never added to revenue.
    assert result.annual[0].sales_revenue == D(2250)
    assert [s.id for s in result.avoided_costs] == ["avoided-treatment"]


def test_conflicting_billing_units_are_rejected():
    bad = _payment("processing_services", "treatment", quantity=1000, rate="0.50",
                   rate_unit="GBP/kg")
    result = calculate_revenue(project(bad))
    assert result.issues and not result.annual


def test_duplicate_payment_identity_is_rejected():
    first = _payment("processing_services", "fee", quantity=1, rate=1)
    second = _payment("infrastructure_usage", "fee", quantity=1, rate=1)
    assert "Duplicate" in str(calculate_revenue(project(first, second)).issues)


# --- integrated study: stream-linked volumes, contracted capacity, finance ---


def _study(ramp=None, *, capacity=True, term=None, calendar_start=2025):
    report, config, _ = operating_fixture()
    config["sales"] = []
    fin = config["financial"]
    fin["calendar_start_year"] = calendar_start  # construction 1 year: ops 2026, 2027, 2028
    if ramp is not None:
        fin["production_ramp"] = ramp
    life = fin["operating_years"]
    treatment = config_line(life)
    treatment.update(id="treatment", payment_id="treatment", name="Treatment fee")
    pipeline = config_line(life, "infrastructure_usage")
    pipeline.update(id="pipeline", payment_id="pipeline", name="Pipeline usage")
    for row in treatment["years"]:
        row["rate"] = 0.5
    for row in pipeline["years"]:
        row["rate"] = 0.25
    lines = [treatment, pipeline]
    if capacity:
        reservation = config_line(life, "capacity_availability")
        reservation.update(id="capacity", payment_id="capacity", name="Capacity reservation",
                           stream_key=None, property="contract_quantity", rate_period="annual")
        for row in reservation["years"]:
            row.update(quantity=2000, rate=0.15)
        lines.append(reservation)
    if term:
        treatment["contract_term"] = term
    config["commercial_lines"] = lines
    return report, config


def _run(report, config):
    return calculate_operating_study(report, DESCRIPTION, config, calculate_capex(inputs=inputs()))


def _by_payment(result):
    out = {}
    for r in result["revenue"].commercial:
        out.setdefault(r.payment_id, {})[r.year] = r.revenue
    return out


def test_more_treated_volume_moves_volume_payments_not_capacity_and_finance_reconciles():
    base = _run(*_study([0.6, 0.8, 1]))
    more = _run(*_study([0.9, 0.8, 1]))
    b, m = _by_payment(base), _by_payment(more)
    assert m["treatment"][1] == b["treatment"][1] * D("1.5")
    assert m["pipeline"][1] == b["pipeline"][1] * D("1.5")
    assert m["capacity"][1] == b["capacity"][1] == D("300.00")
    assert m["treatment"][2] == b["treatment"][2]  # other years unchanged
    construction = 1
    for result in (base, more):
        assert not result["financial"].issues
        for annual in result["revenue"].annual:
            assert result["financial"].ledger[annual.year + construction].revenue == annual.sales_revenue


def test_partial_year_and_zero_production():
    partial = _by_payment(_run(*_study([0.5, 0.8, 1])))
    full = _by_payment(_run(*_study([1, 0.8, 1])))
    assert partial["treatment"][1] * 2 == full["treatment"][1]
    assert partial["capacity"][1] == full["capacity"][1]  # contracted, not volume-linked
    zero = _run(*_study([0, 0.8, 1]))
    z = _by_payment(zero)
    assert z["treatment"][1] == 0 and z["pipeline"][1] == 0  # zero, not unresolved
    assert z["capacity"][1] == D("300.00")
    assert not zero["financial"].issues


def test_contract_expiry_2027_blocks_unsupported_2028_payment():
    term = {"start_year": 2026, "end_year": 2027, "basis": "Synthetic heads of terms"}
    report, config = _study(term=term)
    with pytest.raises(ValueError, match="pays in 2028"):
        _run(report, config)
    # Expiry honoured: 2028 set to no payment.
    report, config = _study(term=term)
    config["commercial_lines"][0]["years"][2]["rate"] = 0
    result = _by_payment(_run(report, config))
    assert result["treatment"][3] == 0 and result["treatment"][2] > 0


def test_renewal_2028_needs_an_explicit_basis_and_is_labelled():
    term = {"start_year": 2026, "end_year": 2027, "basis": "Synthetic heads of terms",
            "renewals": [{"start_year": 2028, "end_year": None, "status": "assumed", "basis": ""}]}
    report, config = _study(term=term)
    with pytest.raises(ValueError, match="needs a basis"):
        _run(report, config)
    term["renewals"][0]["basis"] = "Renewal on the same terms is a planning assumption"
    report, config = _study(term=copy.deepcopy(term))
    result = _run(report, config)
    assert _by_payment(result)["treatment"][3] > 0
    years = coverage(config["commercial_lines"][0], config)
    assert years[3] == {"calendar_year": 2028, "basis": "renewal_assumed"}
    assert years[1]["basis"] == "contract"


def test_contract_term_validation():
    report, config = _study(term={"start_year": 2026, "end_year": 2025, "basis": "x"})
    with pytest.raises(ValueError, match="ends before it starts"):
        _run(report, config)
    report, config = _study(term={"end_year": 2027})
    with pytest.raises(ValueError, match="needs a basis"):
        _run(report, config)


def test_payments_sharing_a_stream_need_a_double_count_review():
    _, config = _study()
    problems = double_count_reviews(config)
    assert len(problems) == 1 and "Treatment fee, Pipeline usage bill the same stream" in problems[0]
    for item in config["commercial_lines"][:2]:
        item["shared_stream_review"] = {"basis": "Treatment service and pipeline access are separate contracts"}
    assert double_count_reviews(config) == []


def test_avoided_cost_beside_revenue_needs_an_overlap_review():
    _, config = _study(capacity=False)
    for item in config["commercial_lines"]:
        item["shared_stream_review"] = {"basis": "Separate contracts"}
    config["avoided_costs"] = [{"id": "avoided-treatment", "target_opex_id": "feed:acid",
                                "rationale": "Synthetic", "already_applied": False, "years": []}]
    assert any("Avoided cost avoided-treatment" in p for p in double_count_reviews(config))
    config["avoided_costs"][0]["revenue_overlap_review"] = {
        "basis": "The saving is the plant's own avoided cost; no customer is billed for it"}
    assert double_count_reviews(config) == []
