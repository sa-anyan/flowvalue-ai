"""FV-G0-R01: explicit/inherited horizons, contract years and analytic oracles.

Synthetic inputs only. The small economic reference uses a supplied $100 capital
snapshot, not a costing function; its expected cash series is hand specified.
"""

import copy
import json
from decimal import Decimal as D, localcontext

import pytest

from backend.capex.models import CapexResult

from backend.orchestration.operating_economics import calculate_operating_study
from backend.orchestration.pipeline import run
from backend.orchestration.store import Store
from backend.scenarios_and_uncertainty.monte_carlo.engine import evaluate, simulate
from backend.scenarios_and_uncertainty.monte_carlo.models import Settings
from backend.scenarios_and_uncertainty.monte_carlo.scenarios import (
    prepare,
    resolve_horizon,
)
from backend.scenarios_and_uncertainty.monte_carlo.service import start
from backend.tests.test_monte_carlo import complete_state
from backend.tests.test_revenue_authority import approve


def outcome(state, settings):
    plan = prepare(state, settings)
    return plan, evaluate(state["parsed"]["report"], state["description"], plan, [])


@pytest.mark.parametrize("settings", [Settings(), Settings(operating_years=3)])
def test_three_authorised_years_default_or_explicit(settings):
    state = complete_state()
    original = copy.deepcopy(state)
    plan, result = outcome(state, settings)
    assert plan["operating_economics"]["financial"]["operating_years"] == 3
    assert result["status"] == "complete"
    assert [p["year"] for p in result["cash_flow"]] == [0, 1, 2, 3, 4]
    assert state == original


def test_explicit_twenty_does_not_invent_seventeen_contract_years():
    state = complete_state()
    plan, result = outcome(state, Settings(operating_years=20))
    assert plan["operating_economics"]["financial"]["operating_years"] == 20
    assert [
        y["year"] for y in plan["operating_economics"]["commercial_lines"][0]["years"]
    ] == [1, 2, 3]
    assert result["status"] == "partial"
    assert result["metrics"]["npv"] is None
    assert "missing operating years=" + str(list(range(4, 21))) in str(result["issues"])
    assert result["unpriced"] == []


def test_missing_year_stays_unresolved_not_zero():
    state = complete_state()
    state["plan"]["operating_economics"]["commercial_lines"][0]["years"].pop(1)
    state["revenue_approval"] = approve(
        state["plan"]["operating_economics"], state["parsed"]["report"]
    )["approval"]
    _, result = outcome(state, Settings())
    assert result["status"] == "partial"
    assert "missing operating years=[2]" in str(result["issues"])
    assert result["metrics"]["npv"] is None


@pytest.mark.parametrize("years", [[1, 2, 2], [1, 3, 2], [2027, 2028, 2029]])
def test_duplicate_unordered_and_calendar_rows_rejected(years):
    state = complete_state()
    for row, year in zip(
        state["plan"]["operating_economics"]["commercial_lines"][0]["years"], years
    ):
        row["year"] = year
    with pytest.raises(ValueError, match="Commercial"):
        prepare(state, Settings())


def test_explicit_shortening_is_by_year_and_disclosed_without_mutation():
    state = complete_state()
    original = copy.deepcopy(state)
    plan = prepare(state, Settings(operating_years=2))
    assert [
        r["year"] for r in plan["operating_economics"]["commercial_lines"][0]["years"]
    ] == [1, 2]
    assert plan["_monte_carlo_horizon"]["excluded_schedule_years"] == [
        {"kind": "commercial_lines", "id": "treatment", "years": [3]}
    ]
    assert state == original


def test_implicit_horizon_does_not_silently_drop_extra_contract_rows():
    state = complete_state()
    rows = state["plan"]["operating_economics"]["commercial_lines"][0]["years"]
    rows.append({**rows[-1], "year": 4})
    plan, result = outcome(state, Settings())
    assert len(plan["operating_economics"]["commercial_lines"][0]["years"]) == 4
    assert result["status"] == "partial"


def reference_study(zero_middle=False):
    """Input definition: capital100, WC10; revenue200/year; admin10%; no tax."""
    state = complete_state()
    cfg = state["plan"]["operating_economics"]
    cfg["sales"] = []
    cfg["commercial_intent"]["mechanisms"] = [
        m for m in cfg["commercial_intent"]["mechanisms"] if m["id"] == "fee"
    ]
    state["description"] = state["revenue_description"] = (
        "We charge wastewater treatment fees."
    )
    fee = cfg["commercial_lines"][0]
    fee.update(stream_key=None, property="contract_quantity")
    for row in fee["years"]:
        row.update(quantity=100, rate=0 if zero_middle and row["year"] == 2 else 2)
    cfg.update(materials=[], energy=[], labour=[])
    cfg["additional_expenses"] = [
        dict(
            id=key,
            category=key,
            annual_allowance=0,
            behavior="fixed",
            rationale="Explicit synthetic zero applicability",
            uncertainty="Synthetic reference",
        )
        for key in ("raw_materials", "utilities", "operating_labor")
    ]
    for key in cfg["garrett_factors"]:
        cfg["garrett_factors"][key].update(
            fraction=0.1 if key == "administration" else 0,
            override=True,
            override_reason="Explicit synthetic reference, not an industrial Garrett selection",
        )
    cfg["financial"].update(
        construction_years=0,
        construction_spend_fractions=[1],
        production_ramp=[1, 1, 1],
        tax_rate=0,
    )
    state["revenue_approval"] = approve(
        cfg, state["parsed"]["report"], state["revenue_description"]
    )["approval"]
    # A supplied upstream snapshot is an input, not a generated expected value.
    capital = CapexResult(
        model_id="garrett",
        process_type="mixed",
        status="provisional",
        purchased_equipment=D(100),
        direct_costs=D(100),
        indirect_costs=D(0),
        plant_cost=D(100),
        fixed_capital=D(100),
        startup_expenses=D(0),
        working_capital=D(10),
        total_capex=D(110),
        currency="USD",
        period="1987",
        index_series="SOURCE_PRICE_BASIS",
        index_value=D(1),
        lines=(),
        issues=(),
        assumptions=("Supplied synthetic capital input, not a costing benchmark",),
        evidence={"source": "Independent synthetic numerical input"},
    )
    return state, capital


@pytest.mark.parametrize("zero_middle", [False, True])
def test_independent_three_year_revenue_opex_and_finance(zero_middle):
    state, capital = reference_study(zero_middle)
    cfg = prepare(state, Settings())["operating_economics"]
    result = calculate_operating_study(
        state["parsed"]["report"], state["description"], cfg, capital
    )
    revenues = [D(200), D(0) if zero_middle else D(200), D(200)]
    assert [r.sales_revenue for r in result["revenue"].annual] == revenues
    assert [r.annual_cash_opex for r in result["opex"].values()] == [
        r / 10 for r in revenues
    ]
    expected_cash = [D(-110), D(180), D(0) if zero_middle else D(180), D(190)]
    assert [r.fcff for r in result["financial"].ledger] == expected_cash
    with localcontext() as c:
        c.prec = 40
        expected_npv = sum(v / D("1.1") ** year for year, v in enumerate(expected_cash))
        actual_npv = dict(result["financial"].metrics)["project_npv"].value
        assert abs(actual_npv - expected_npv) < D("1e-30")
    assert result["financial"].status == "calculated_preliminary"


def test_monte_carlo_and_deterministic_horizons_and_npv_reconcile():
    state = complete_state()
    result = simulate(state, Settings(parameters=[]))
    deterministic = run(
        state["parsed"]["report"],
        state["description"],
        prepare(state, Settings()),
        calculate_ranges=False,
    )
    ledger = deterministic["stages"]["financial"]["result"]["ledger"]
    # Independent discounted-sum aggregation, not a second call to production NPV.
    expected_npv = sum(
        D(row["fcff"]) / D("1.1") ** row["period"]["year"] for row in ledger
    )
    assert result["summary"]["complete_runs"] == 1000
    assert (
        result["audit"]["operating_years"] == result["settings"]["operating_years"] == 3
    )
    assert result["audit"]["horizon_resolution"]["selection"] == "project"
    assert result["runs"][0]["metrics"]["npv"] == pytest.approx(
        float(expected_npv), rel=1e-12
    )
    assert len(result["runs"][0]["cash_flow"]) == len(ledger) == 5


def test_job_freezes_inherited_horizon_and_reopen_preserves_original(tmp_path):
    store = Store(tmp_path / "synthetic.sqlite3")
    original = store.create(complete_state(), b"synthetic")
    version = store.version(original["id"], "Original three-year reference")
    job = start(store, original["id"], Settings())
    restored = Settings.model_validate_json(json.dumps(job["settings"]))
    assert restored.operating_years == 3
    assert "operating_years" in restored.model_fields_set
    assert job["horizon_resolution"]["selection"] == "project"
    assert store.get(original["id"]) == original
    reopened = store.load(version)
    assert reopened["plan"] == original["plan"]
    assert (
        prepare(reopened, Settings())["operating_economics"]["financial"][
            "operating_years"
        ]
        == 3
    )


def test_legacy_serialized_twenty_remains_explicit():
    settings = Settings.model_validate({"operating_years": 20})
    assert resolve_horizon(complete_state(), settings)["selection"] == "explicit"
    _, result = outcome(complete_state(), settings)
    assert result["status"] == "partial"


@pytest.mark.parametrize("invalid", [True, 0, 51, "3"])
def test_ambiguous_or_invalid_inherited_horizon_not_guessed(invalid):
    state = complete_state()
    state["plan"]["operating_economics"]["financial"]["operating_years"] = invalid
    with pytest.raises(ValueError, match="unambiguous"):
        prepare(state, Settings())


def test_changed_schedule_still_requires_fresh_revenue_authority():
    state = complete_state()
    state["plan"]["operating_economics"]["commercial_lines"][0]["years"].pop(1)
    _, result = outcome(state, Settings())
    assert result["status"] == "partial"
    assert "Review and approve" in str(result["issues"])
    assert result["metrics"]["npv"] is None
