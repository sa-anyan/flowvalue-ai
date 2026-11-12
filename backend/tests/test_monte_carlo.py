"""Seeded distributions, scope honesty and canonical financial reconciliation."""

import copy
from decimal import Decimal
import io
import json
from pathlib import Path

import numpy as np
import pytest
from openpyxl import load_workbook

from backend.scenarios_and_uncertainty.monte_carlo.discovery import discover
from backend.scenarios_and_uncertainty.monte_carlo.engine import evaluate, simulate
from backend.scenarios_and_uncertainty.monte_carlo.exports import export
from backend.scenarios_and_uncertainty.monte_carlo.models import (
    Alias,
    Correlation,
    Parameter,
    Settings,
)
from backend.scenarios_and_uncertainty.monte_carlo.sampling import sample, validate
from backend.scenarios_and_uncertainty.monte_carlo.scenarios import apply, prepare
from backend.tests.test_isolated_stages import study
from backend.tests.test_operating_economics import DESCRIPTION
from backend.tests.test_revenue_authority import BOX, approve, ready


def complete_state():
    report, config, _ = ready()
    config["price_basis"]["price_period"] = "1987"
    plan = {
        "equipment": [
            {
                "equipment_key": "pump",
                "quantity": 1,
                "manual_price": {
                    "amount": 10_000,
                    "currency": "USD",
                    "price_period": "1987",
                    "source": "Synthetic manual purchase price",
                    "notes": "Explicit per-unit purchase cost for testing",
                    "cost_scope": "purchased_equipment",
                    "approved": True,
                },
                "rationale": "Synthetic asset with an approved purchase price",
            }
        ],
        "capex": {
            "model_id": "garrett",
            "process_type": "mixed",
            "delivery_basis": "delivered",
            "factor_selection": "minimum",
        },
        "operating_economics": config,
        "cost_translation": {"enabled": False},
    }
    return {
        "id": "synthetic",
        "revision": 0,
        "plan": plan,
        "description": DESCRIPTION + "\n" + BOX,
        "revenue_description": BOX,
        "revenue_approval": approve(config, report)["approval"],
        "parsed": {"report": report},
        "results": None,
    }


def parameter(distribution="triangular"):
    return Parameter(
        id="p",
        label="Test size",
        enabled=True,
        targets=[["equipment", 0, "size"]],
        unit="1000 US_gpm_psi",
        minimum=0.5,
        mode=1,
        maximum=2,
        stddev=0.2,
        source="Independent synthetic test",
        rationale="Test valid physical bounds",
        distribution=distribution,
        hard_min=0,
        strictly_positive=True,
    )


def test_distributions_reproduce_and_respect_limits():
    p = parameter()
    original = Settings(parameters=[p])
    for kind in ("triangular", "uniform", "normal", "lognormal", "discrete"):
        actual = p.model_copy(
            update={
                "distribution": kind,
                "choices": [0.5, 1, 2],
                "probabilities": [0.2, 0.6, 0.2],
            }
        )
        settings = Settings(parameters=[actual])
        _, a = sample(settings, original)
        _, b = sample(settings, original)
        np.testing.assert_array_equal(a, b)
        assert np.min(a.astype(float)) >= 0.5 and np.max(a.astype(float)) <= 2


def test_method_ranges_and_approved_commercial_draws():
    state = complete_state()
    report = state["parsed"]["report"]
    state["plan"]["capex"]["selected_factors"] = {"piping": .30}
    before = copy.deepcopy(state)
    settings = Settings.model_validate(discover(state)["settings"])
    by_id = {p.id: p for p in settings.parameters}
    piping = by_id["capex.selected_factors.piping"]
    assert (piping.minimum, piping.mode, piping.maximum) == (.15, .30, .70)
    assert any(p.minimum is not None and p.maximum is not None for p in settings.parameters
               if "garrett_factors" in p.targets[0])
    rate = next(p for p in settings.parameters if "commercial_lines" in p.targets[0]
                and p.targets[0][-1] == "rate")
    assert len(rate.targets) == settings.operating_years
    assert not rate.enabled and rate.minimum is None
    plan = prepare(state, settings)
    assert plan["_monte_carlo_revenue_approved"]
    low = evaluate(report, state["description"], plan, [])
    equipment_price = by_id["equipment.0.manual_price.amount"]
    apply(plan, [equipment_price], [12_000])
    assert evaluate(report, state["description"], plan, [])["metrics"]["capex"] > low["metrics"]["capex"]
    apply(plan, [rate], [rate.mode * 2])
    high = evaluate(report, state["description"], plan, [])
    assert high["metrics"]["revenue"] > low["metrics"]["revenue"] > 0
    assert state == before
    state.pop("revenue_approval")
    unapproved = evaluate(report, state["description"], prepare(state, settings), [])
    assert unapproved["metrics"]["revenue"] is None


def test_correlations_and_constraints_cannot_be_bypassed():
    p = parameter()
    q = p.model_copy(update={"id": "q", "targets": [["equipment", 1, "size"]]})
    r = p.model_copy(update={"id": "r", "targets": [["equipment", 2, "size"]]})
    base = Settings(parameters=[p, q, r])
    with pytest.raises(ValueError, match="positive semidefinite"):
        validate(
            Settings(
                parameters=[p, q, r],
                correlations=[
                    Correlation(a="p", b="q", rho=0.9, rationale="Test"),
                    Correlation(a="q", b="r", rho=0.9, rationale="Test"),
                    Correlation(a="p", b="r", rho=-0.9, rationale="Test"),
                ],
            ),
            base,
        )
    with pytest.raises(ValueError, match="physical"):
        validate(
            Settings(
                parameters=[p.model_copy(update={"minimum": -1, "hard_min": -100})]
            ),
            base,
        )
    with pytest.raises(ValueError, match="unit"):
        validate(Settings(parameters=[p.model_copy(update={"unit": "kg"})]), base)
    settings = Settings(
        parameters=[p, q],
        correlations=[
            Correlation(
                a="p", b="q", rho=0.8, rationale="Shared physical design driver"
            )
        ],
    )
    _, draw = sample(settings, base)
    assert np.corrcoef(draw.astype(float).T)[0, 1] > 0.7


def test_alias_cycles_rejected_and_baseline_preserved():
    state = complete_state()
    state["plan"]["equipment"].append({"equipment_key": "other", "curve_id": None})
    state["parsed"]["report"]["entities"].append(
        {"key": "other", "identifier": "Other", "kind": "equipment", "values": []}
    )
    before = copy.deepcopy(state)
    with pytest.raises(ValueError, match="Cyclic"):
        prepare(
            state,
            Settings(
                aliases=[
                    Alias(equipment_key="pump", target_key="other", rationale="Test"),
                    Alias(equipment_key="other", target_key="pump", rationale="Test"),
                ]
            ),
        )
    plan = prepare(
        state,
        Settings(
            aliases=[
                Alias(
                    equipment_key="other",
                    target_key="pump",
                    rationale="Confirmed duplicate",
                )
            ]
        ),
    )
    assert plan["equipment"][1]["scope_decision"] == "alias"
    assert state == before


def test_canonical_financials_and_reproducible_simulation():
    from backend.orchestration.pipeline import run

    state = complete_state()
    original = copy.deepcopy(state)
    settings = Settings.model_validate(discover(state)["settings"])
    settings.parameters = []
    a = simulate(state, settings)
    b = simulate(state, settings)
    assert a == b
    assert len(a["runs"]) == 1000
    assert a["summary"]["complete_runs"] == 1000
    plan = prepare(state, settings)
    canonical = run(
        state["parsed"]["report"], state["description"], plan, calculate_ranges=False
    )
    npv = dict(canonical["stages"]["financial"]["result"]["metrics"])["project_npv"][
        "value"
    ]
    assert a["runs"][0]["metrics"]["npv"] == float(npv)
    assert state == original
    assert a["summary"]["metrics"]["npv"]["p10"] == float(npv)
    data, mime = export(a, "xlsx")
    book = load_workbook(io.BytesIO(data), read_only=True)
    assert {
        "Results",
        "Parameters",
        "Cash flows",
        "Exact values",
        "Unresolved scope",
        "Audit JSON",
    } <= set(book.sheetnames)
    exact_rows = book["Exact values"].values
    assert next(exact_rows) == ("run", "chunk", "json")
    run_index, chunk_index, payload = next(exact_rows)
    assert (run_index, chunk_index) == (0, 0)
    assert json.loads(payload) == a["runs"][0]["exact_values"]
    assert mime.endswith("sheet")
    csv, _ = export(a, "csv")
    assert b"npv" in csv and b"complete" in csv


def test_unpriced_equipment_never_counts_as_success():
    state = complete_state()
    state["parsed"]["report"]["entities"].append(
        {
            "key": "missing",
            "kind": "equipment",
            "identifier": "Unresolved",
            "values": [],
        }
    )
    result = simulate(state, Settings(), progress=lambda done, total: False)
    assert result["summary"]["complete_runs"] == 0
    assert result["summary"]["probability_negative_npv"] is None
    assert result["runs"][0]["coverage"]["fraction"] == 0.5
    assert result["runs"][0]["unpriced"][0]["tag"] == "Unresolved"


CHARLIE_TAGS = [
    "T-104",
    "T-101",
    "R-101",
    "T-105",
    "HE-101",
    "HE-102",
    "S-201",
    "FT-201",
    "PD-201AB",
    "PD-201",
    "C-201",
    "T-301",
    "R-201",
]


@pytest.mark.parametrize("tag", CHARLIE_TAGS)
def test_all_thirteen_charlie_exceptions_are_explicit(tag):
    state = complete_state()
    state["results"] = {
        "stages": {
            "equipment": {
                "result": {
                    "equipment": [
                        {
                            "equipment_tag": tag,
                            "equipment_cost": None,
                            "parsed_source": {"equipment_key": tag},
                            "decision": {
                                "candidate_curve_ids": [],
                                "rationale": "Missing supported model/input; never zero",
                            },
                        }
                    ]
                }
            }
        }
    }
    gap = discover(state)["exceptions"][0]
    assert gap["tag"] == tag and gap["reason"]
    assert gap["status"] == "unsupported_model"


def test_actual_charlie_register_when_available():
    path = Path("outputs/charlie-founder-workflow/after.json")
    if not path.exists():
        pytest.skip("Private Charlie snapshot not distributed")
    state = json.loads(path.read_text())
    data = discover(state)
    assert {e["tag"] for e in data["exceptions"]} == set(CHARLIE_TAGS)
    assert len(data["exceptions"]) == 13
    settings = Settings.model_validate(data["settings"])
    result = simulate(state, settings, progress=lambda done, total: False)
    assert result["summary"]["complete_runs"] == 0
    assert len(result["runs"][0]["unpriced"]) == 13


def test_boolean_quantity_and_unknown_target_are_rejected():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        Parameter.model_validate({**parameter().model_dump(), "minimum": True})
    p = parameter()
    bad = p.model_copy(update={"targets": [["equipment", 999, "size"]]})
    with pytest.raises(ValueError, match="target"):
        validate(Settings(parameters=[bad]), Settings(parameters=[p]))


def test_failed_iterations_do_not_enter_probability_denominators():
    from unittest.mock import patch

    state = complete_state()
    with patch(
        "backend.scenarios_and_uncertainty.monte_carlo.engine.evaluate",
        side_effect=ValueError("Invalid capacity"),
    ):
        result = simulate(state, Settings(), progress=lambda done, total: False)
    assert result["summary"]["failed_runs"] == 1
    assert result["summary"]["complete_runs"] == 0
    assert result["summary"]["probability_negative_npv"] is None


def test_confirmed_alias_is_not_charged_twice():
    state = complete_state()
    report = state["parsed"]["report"]
    report["entities"].append(
        {"key": "alias", "identifier": "Pump alias", "kind": "equipment", "values": []}
    )
    state["plan"]["equipment"].append({"equipment_key": "alias", "curve_id": None})
    settings = Settings(
        aliases=[
            Alias(
                equipment_key="alias",
                target_key="pump",
                rationale="Confirmed duplicate",
            )
        ]
    )
    plan = prepare(state, settings)
    result = evaluate(report, state["description"], plan, ["alias"])
    assert_exact_stage_parity(report, state["description"], plan, result)
    assert result["coverage"]["total"] == 1
    assert result["coverage"]["confirmed_aliases"] == 1
    assert sum(row["price_coverage"] == "priced" for row in result["equipment_records"]) == 1


def test_engineering_proposals_are_separate_and_require_enablement():
    from backend.scenarios_and_uncertainty.monte_carlo.advisor import recommend

    class Cache:
        def cached(self, key, call):
            return call(), False

    class Provider:
        def generate(self, **kwargs):
            return {
                "proposals": [
                    {
                        "id": p["id"],
                        "status": "unresolved",
                        "minimum": None,
                        "mode": p["mode"],
                        "maximum": None,
                        "stddev": None,
                        "distribution": "triangular",
                        "source": "No external research",
                        "rationale": "Insufficient physical evidence",
                        "confidence": "Uncalibrated",
                    }
                    for p in kwargs["context"]["parameters"]
                ]
            }

    state = complete_state()
    before = copy.deepcopy(state)
    proposals, audit = recommend(state, Cache(), Provider())
    assert state == before
    assert proposals == [] and audit


def test_api_freezes_baseline_and_rejects_stale_and_wrong_parent(study):
    import threading
    from unittest.mock import patch

    from fastapi.testclient import TestClient

    import backend.api.app as api
    from backend.blocks.execution import fresh, run_stage
    from backend.blocks.stage_workflow import approve as approve_engineering, queue as queue_stages, run
    from backend.revenue.authority import update

    store, key = study
    endpoint = f"/api/assessments/{key}/monte-carlo/run"

    class Queue:
        def submit(self, call):
            self.call = call

    queue = Queue()
    with (
        patch.object(api, "store", store),
        patch.object(api, "lock", threading.Lock()),
        patch.object(api, "executor", queue),
        TestClient(api.app, base_url="http://localhost") as client,
    ):
        response = client.post(endpoint, json=Settings().model_dump())
        assert response.status_code == 422
        assert "run financial first" in response.json()["detail"]

        state = run_stage(store, key, "engineering_data")
        state = approve_engineering(store, key, state["revision"])
        update(store, key, state["revision"], approve=True)
        queue_stages(store, key)
        state = run(store, key)
        assert fresh(state, "financial"), state["stage_runs"]

        before = copy.deepcopy(state)
        settings = Settings.model_validate(discover(state)["settings"])
        settings.baseline_revision = state["revision"] - 1
        response = client.post(endpoint, json=settings.model_dump())
        assert response.status_code == 422
        assert "rediscover parameters" in response.json()["detail"]
        settings.baseline_revision = state["revision"]
        response = client.post(endpoint, json=settings.model_dump())
        assert response.status_code == 202, response.text
        job = response.json()
        assert job["status"] == "queued"
        assert store.get(job["snapshot_id"])["assessment"] == before
        assert (
            client.get(
                f"/api/assessments/not-the-parent/monte-carlo/jobs/{job['id']}"
            ).status_code
            == 404
        )
        assert store.get(state["id"]) == before


def test_user_locked_parameters_do_not_auto_enable():
    state = complete_state()
    state["locked"] = ["equipment"]
    state["plan"]["equipment"][0]["sizing"] = {
        "method": "vessel_hold_up",
        "parameters": {
            "residence_time_h": {
                "value": 1,
                "unit": "h",
                "low": 0.5,
                "high": 2,
                "rationale": "Synthetic range",
                "source": "Synthetic",
            }
        },
    }
    data = discover(state)
    assert all(
        not p["enabled"]
        for p in data["settings"]["parameters"]
        if p["targets"][0][0] == "equipment"
    )


def test_marginal_moments_are_consistent_with_definitions():
    p = parameter("uniform")
    settings = Settings(parameters=[p], iterations=10000)
    _, draw = sample(settings, settings)
    assert abs(float(np.mean(draw.astype(float))) - 1.25) < 0.03
    settings.parameters[0].distribution = "triangular"
    _, draw = sample(settings, settings)
    assert abs(float(np.mean(draw.astype(float))) - (0.5 + 1 + 2) / 3) < 0.03


def test_preflight_uses_reviewed_central_assumptions(monkeypatch):
    from backend.scenarios_and_uncertainty.monte_carlo import service

    state = complete_state()
    settings = Settings.model_validate(discover(state)["settings"])
    report = state["parsed"]["report"]
    baseline = evaluate(report, state["description"], prepare(state, settings), [])
    sale = next(p for p in settings.parameters if p.id == "operating_economics.sales.0.unit_price")
    sale.enabled = True
    sale.minimum = 0.8
    sale.mode = 1.1
    sale.maximum = 1.2
    sale.rationale = "Synthetic explicit central-case price"
    central = {}

    def record_evaluation(*args):
        central.update(evaluate(*args))
        return central

    monkeypatch.setattr(service, "evaluate", record_evaluation)
    check = service.preflight(state, settings)
    assert check["status"] == "complete"
    assert central["metrics"]["revenue"] > baseline["metrics"]["revenue"] > 0
    assert state["plan"]["operating_economics"]["sales"][0]["unit_price"] == 1


def test_zero_weight_discrete_alternative_is_never_selected():
    p = parameter("discrete")
    p.choices = [0.5, 1, 2]
    p.probabilities = [0, 1, 0]
    settings = Settings(parameters=[p])
    _, draw = sample(settings, settings)
    assert np.all(draw.astype(float) == 1)


def test_input_fingerprint_includes_source_values():
    state = complete_state()
    settings = Settings()
    first = simulate(state, settings, progress=lambda *args: False)
    state["parsed"]["report"]["entities"][0]["values"][0]["normalized_value"] = 101
    second = simulate(state, settings, progress=lambda *args: False)
    assert first["input_hash"] != second["input_hash"]


def test_confirmed_same_tag_scenario_keeps_both_prices():
    state = complete_state()
    report = state["parsed"]["report"]
    original = next(row for row in report["entities"] if row["key"] == "pump")
    original["identifier"] = "T-104"
    report["entities"].append({**copy.deepcopy(original), "key": "pump-two"})
    first = state["plan"]["equipment"][0]
    second = copy.deepcopy(first)
    second.update(
        equipment_key="pump-two",
        scope_confirmation={
            "status": "user_confirmed_distinct",
            "rationale": "Reviewed separate costed item",
        },
    )
    second["manual_price"]["amount"] = 5_000
    state["plan"]["equipment"].append(second)
    result = evaluate(report, state["description"], state["plan"], [])
    assert_exact_stage_parity(report, state["description"], state["plan"], result)
    records = result["equipment_records"]
    assert [(r["record_key"], r["display_tag"], r["cost"]) for r in records] == [
        ("pump", "T-104", 10_000), ("pump-two", "T-104", 5_000)
    ]
    assert sum(r["cost"] for r in records) == 15_000
    from backend.scenarios_and_uncertainty.monte_carlo.engine import summarize

    summary = summarize([{"index": 0, **result}], [], Settings())
    assert summary["equipment"]["pump"]["p50"] == 10_000
    assert summary["equipment"]["pump-two"]["p50"] == 5_000
    assert summary["equipment"]["pump-two"]["display_tag"] == "T-104"

def test_legacy_tag_keyed_scenario_export_leaves_snapshot_unchanged():
    payload = json.dumps({
        "runs": [{
            "index": 0,
            "status": "complete",
            "equipment_costs": {"T-104": 5000},
            "equipment_installation_costs": {"T-104": 250},
            "equipment_models": {"T-104": "legacy-model"},
        }],
        "settings": Settings().model_dump(mode="json"),
        "summary": {"metrics": {}},
        "audit": {"exceptions": []},
    })
    result = json.loads(payload)
    workbook, _ = export(result, "xlsx")
    book = load_workbook(io.BytesIO(workbook), read_only=True)
    headers, values = list(book["Equipment costs"].values)
    row = dict(zip(headers, values))
    assert row["display_tag"] == "T-104"
    assert row["record_key"] is None
    assert row["cost"] == 5000
    assert row["installation_cost"] == 250
    assert row["model_id"] == "legacy-model"
    assert json.dumps(result) == payload

def test_split_projection_keeps_priced_and_unpriced_records():
    state = complete_state()
    report = state["parsed"]["report"]
    parent = state["plan"]["equipment"][0]
    parent["scope_confirmation"] = {
        "status": "user_confirmed",
        "rationale": "Reviewed split",
    }
    parent["physical_assets"] = [
        {
            "asset_id": "priced",
            "equipment_tag": "T-104",
            "quantity": 1,
            "manual_price": parent["manual_price"],
        },
        {
            "asset_id": "unpriced",
            "equipment_tag": "T-104",
            "quantity": 1,
            "scope_confirmation": {
                "status": "user_confirmed_distinct",
                "rationale": "Reviewed separately costed item",
            },
        },
    ]
    result = evaluate(report, state["description"], state["plan"], [])
    assert_exact_stage_parity(report, state["description"], state["plan"], result)
    records = result["equipment_records"]
    assert [(r["record_key"], r["price_coverage"], r["cost"]) for r in records] == [
        ("pump::priced", "priced", 10_000), ("pump::unpriced", "unpriced", None)
    ]
    assert [r["physical_asset_id"] for r in records] == ["pump::priced", "pump::unpriced"]
    assert records[0]["model_id"] == "manual:user-price"


def test_ab_projection_preserves_quantity_extended_price():
    state = complete_state()
    report = state["parsed"]["report"]
    equipment = next(row for row in report["entities"] if row["key"] == "pump")
    equipment["identifier"] = "PD-201AB"
    state["plan"]["equipment"][0]["quantity"] = 2
    result = evaluate(report, state["description"], state["plan"], [])
    record, = result["equipment_records"]
    assert record["display_tag"] == "PD-201AB"
    assert record["equipment_count"] == 2
    assert record["cost"] == 20_000

@pytest.mark.parametrize("case", ["alias", "AB"])
def test_deterministic_decimal_parity(case):
    from backend.orchestration.pipeline import run

    state = complete_state()
    report = state["parsed"]["report"]
    aliases = []
    if case == "alias":
        report["entities"].append(
            {"key": "alias", "identifier": "Pump alias", "kind": "equipment", "values": []}
        )
        state["plan"]["equipment"].append({"equipment_key": "alias"})
        aliases = [Alias(equipment_key="alias", target_key="pump", rationale="Reviewed alias")]
    else:
        next(row for row in report["entities"] if row["key"] == "pump")["identifier"] = "P-101AB"
        state["plan"]["equipment"][0]["quantity"] = 2
    plan = prepare(state, Settings(aliases=aliases))
    stage = run(report, state["description"], plan, calculate_ranges=False)["stages"]
    scenario = evaluate(report, state["description"], plan, [a.equipment_key for a in aliases])
    assert_exact_stage_parity(report, state["description"], plan, scenario)
    metrics = dict(stage["financial"]["result"]["metrics"])
    values = scenario.get("exact_values", {}).get("metrics", scenario["metrics"])
    for key, metric in {"npv": "project_npv", "payback": "project_discounted_payback"}.items():
        expected = metrics[metric]["value"]
        actual = values[key]
        assert (None if actual is None else Decimal(str(actual))) == (
            None if expected is None else Decimal(expected)
        ), (case, key, expected, actual)

def assert_exact_stage_parity(report, description, plan, scenario):
    from backend.orchestration.pipeline import run

    stages = run(report, description, plan, calculate_ranges=False)["stages"]
    results = {key: value["result"] or {} for key, value in stages.items()}
    exact = json.loads(json.dumps(scenario, allow_nan=False))["exact_values"]

    def check(actual, expected):
        if expected is None:
            assert actual is None
        else:
            assert isinstance(actual, str)
            assert Decimal(actual) == Decimal(str(expected))

    for key, status in exact["stage_status"].items():
        assert status == results[key].get("status")
    financial = dict(results["financial"].get("metrics") or [])
    for key, name in (
        ("npv", "project_npv"),
        ("irr", "project_irr"),
        ("payback", "project_discounted_payback"),
    ):
        check(exact["metrics"][key], financial.get(name, {}).get("value"))
        assert scenario["metric_status"].get(name) == financial.get(name, {}).get("status")
    for key, amount in exact["capex_subtotals"].items():
        check(amount, results["capex"].get(key))
    for key, amount in exact["equipment_totals"].items():
        check(amount, results["equipment"].get(key))
    check(exact["metrics"]["opex"], results["opex"].get("first_year_cash_opex"))
    assert set(exact["annual_opex"]) == set(results["opex"].get("years", {}))
    for year, amounts in exact["annual_opex"].items():
        canonical = results["opex"]["years"][year]
        for key, value in amounts.items():
            if key == "status":
                assert value == canonical.get(key)
            else:
                check(value, canonical.get(key))
    annual = {str(row["year"]): row for row in results["revenue"].get("annual", [])}
    assert set(exact["annual_revenue"]) == set(annual)
    for year, amounts in exact["annual_revenue"].items():
        for key, value in amounts.items():
            check(value, annual[year].get(key))
    if not results["revenue"].get("issues"):
        check(exact["metrics"]["revenue"], annual.get("1", {}).get("sales_revenue"))
    equipment = {
        row["parsed_source"]["equipment_key"]: row for row in results["equipment"]["equipment"]
    }
    assert set(equipment) == {row["record_key"] for row in scenario["equipment_records"]}
    for record, amounts in zip(scenario["equipment_records"], exact["equipment"], strict=True):
        key = record["record_key"]
        row = equipment[key]
        assert amounts["record_key"] == key
        assert record["quantity"] == row["quantity"]
        assert record["cost_scope"] == row["cost_scope"]
        cost = row["equipment_cost"] if row["equipment_cost"] is not None else row["amount"]
        included = record["price_coverage"] == "priced"
        check(amounts["cost"], cost if included else None)
        check(amounts["installation_cost"], row["installation_cost"] if included else None)
    assert scenario["coverage"]["priced"] == sum(
        row["price_coverage"] == "priced" for row in scenario["equipment_records"]
    )


def test_exact_values_preserve_zero_and_distinguish_nonfinite_fields():
    from backend.scenarios_and_uncertainty.monte_carlo.exact_values import project_exact_values

    payload = project_exact_values(
        {"zero": "0.00", "missing": None, "invalid": "NaN", "overflow": "Infinity"},
        [], {}, {}, {}, {}, {},
    )
    assert payload["metrics"] == {
        "zero": "0.00", "missing": None, "invalid": None, "overflow": None,
    }
    assert payload["invalid_numeric_fields"] == ["metrics.invalid", "metrics.overflow"]

def test_ab_full_duty_sizing_and_exact_scenario_acceptance():
    from backend.orchestration.pipeline import run
    from backend.tests.test_sizing_cross_file import load, sizing, stream

    state = complete_state()
    report = state["parsed"]["report"]
    next(row for row in report["entities"] if row["key"] == "pump")["identifier"] = "P-101AB"
    source = load("rows.xlsx")
    report["entities"].append(stream(source, "P-IN"))
    item = state["plan"]["equipment"][0]
    item["sizing"] = sizing(source, "pump_duty")
    item["quantity"] = 2
    plan = prepare(state, Settings())
    scenario = evaluate(report, state["description"], plan, [])
    assert_exact_stage_parity(report, state["description"], plan, scenario)
    record, = scenario["equipment_records"]
    assert (record["display_tag"], record["equipment_count"]) == ("P-101AB", 2)
    assert Decimal(scenario["exact_values"]["equipment"][0]["cost"]) == Decimal(20_000)

    pair = run(report, state["description"], plan, calculate_ranges=False)
    single_plan = copy.deepcopy(plan)
    single_plan["equipment"][0]["quantity"] = 1
    single = run(report, state["description"], single_plan, calculate_ranges=False)
    pair_sizing = pair["stages"]["equipment"]["result"]["equipment"][0]["parsed_source"]["sizing"]
    single_sizing = single["stages"]["equipment"]["result"]["equipment"][0]["parsed_source"]["sizing"]
    assert pair_sizing == single_sizing
    assert pair_sizing["method"] == "pump_duty"
    assert Decimal(str(pair_sizing["calculation"]["hydraulic_power_kw"])) == Decimal("0.1")
