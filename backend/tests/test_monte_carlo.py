"""Seeded distributions, scope honesty and canonical financial reconciliation."""

import copy
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
from backend.scenarios_and_uncertainty.monte_carlo.scenarios import prepare
from backend.tests.test_operating_economics import DESCRIPTION, fixture


def complete_state():
    report, config, _ = fixture()
    plan = {
        "equipment": [
            {
                "equipment_key": "pump",
                "curve_id": "G296-122",
                "size": 1,
                "size_unit": "1000 US_gpm_psi",
                "quantity": 1,
                "costing_options": {
                    "allow_unverified": True,
                    "unit_context": {"target_gallon_basis": "US"},
                },
                "rationale": "Synthetic supplied pump size for integration testing, not an industrial reference",
            }
        ],
        "capex": {
            "model_id": "garrett",
            "process_type": "mixed",
            "delivery_basis": "delivered",
            "factor_selection": "minimum",
        },
        "operating_economics": config,
    }
    return {
        "id": "synthetic",
        "revision": 0,
        "plan": plan,
        "description": DESCRIPTION,
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
    settings = Settings(parameters=[])
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
        "Unresolved scope",
        "Audit JSON",
    } <= set(book.sheetnames)
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
    assert result["coverage"]["total"] == 1
    assert result["coverage"]["confirmed_aliases"] == 1
    assert len(result["equipment_costs"]) == 1


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


def test_api_freezes_baseline_and_rejects_stale_and_wrong_parent(tmp_path):
    import threading
    from unittest.mock import patch

    from fastapi.testclient import TestClient

    import backend.api.app as api
    from backend.orchestration.store import Store

    store = Store(tmp_path / "mc.db")
    state = store.create({**complete_state(), "running": False}, b"fixture")
    before = copy.deepcopy(store.get(state["id"]))
    settings = Settings.model_validate(discover(state)["settings"])

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
        settings.baseline_revision = 99
        response = client.post(
            f"/api/assessments/{state['id']}/monte-carlo/run",
            json=settings.model_dump(),
        )
        assert response.status_code == 422
        settings.baseline_revision = state["revision"]
        response = client.post(
            f"/api/assessments/{state['id']}/monte-carlo/run",
            json=settings.model_dump(),
        )
        assert response.status_code == 202, response.text
        job = response.json()
        assert job["status"] == "queued"
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


def test_preflight_uses_reviewed_central_assumptions():
    from backend.scenarios_and_uncertainty.monte_carlo.service import preflight

    state = complete_state()
    settings = Settings.model_validate(discover(state)["settings"])
    sale = next(
        p
        for p in settings.parameters
        if p.targets[0][:2] == ["operating_economics", "sales"]
    )
    sale.enabled = True
    sale.minimum = 0.8
    sale.mode = 1.1
    sale.maximum = 1.2
    sale.rationale = "Synthetic explicit central-case price"
    check = preflight(state, settings)
    assert check["status"] == "complete"
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
