"""Each button runs one block, never its missing prerequisites or descendants."""

import copy
from pathlib import Path
from unittest.mock import patch

import pytest

from backend.blocks.execution import initialize, run_stage, view, MODE
from backend.orchestration.ingest import parse
from backend.orchestration.service import new_assessment, edit
from backend.orchestration.store import Store
from backend.revenue.authority import update
from backend.tests.test_stage_connections import workbook, plan_for, DESCRIPTION


@pytest.fixture
def study(tmp_path):
    content = workbook()
    report = parse(content, "independent.xlsx")["report"]
    store = Store(tmp_path / "stages.sqlite")
    state = new_assessment(
        store, content, "independent.xlsx", DESCRIPTION, "sells treated water"
    )
    state = initialize(state)
    state.update(running=False, plan=plan_for(report))
    state = store.put(state, state["revision"])
    return store, state["id"]


def test_equipment_without_data_does_not_run_data_or_ai(study):
    store, key = study
    with patch(
        "backend.blocks.engineering_data.runner.calculate",
        side_effect=AssertionError("No cascade"),
    ), patch(
        "backend.orchestration.provider.EngineeringProvider",
        side_effect=AssertionError("No paid call"),
    ):
        state = run_stage(store, key, "equipment", use_ai=True)
    assert state["stage_runs"]["equipment"]["status"] == "data_required"
    assert state["stage_runs"]["equipment"]["requires"] == ["engineering_data"]
    assert not state["stage_outputs"]
    assert "engineering_data" not in state["stage_runs"]


def test_data_runs_alone_and_reading_page_executes_nothing(study):
    store, key = study
    state = run_stage(store, key, "engineering_data")
    assert list(state["stage_outputs"]) == ["engineering_data"]
    assert state["parsed"]["report"]["entities"]
    with patch(
        "backend.blocks.execution.get_runner",
        side_effect=AssertionError("Read must not run"),
    ):
        opened = view(state)
    assert opened["stage_runs"]["engineering_data"]["status"] == "ready"
    assert not opened["results"]["stages"].get("equipment", {}).get("result")


def test_revenue_has_no_capex_or_opex_dependency(study):
    store, key = study
    state = run_stage(store, key, "engineering_data")
    update(store, key, state["revision"], approve=True)
    with patch(
        "backend.blocks.capex.runner.calculate", side_effect=AssertionError("No CAPEX")
    ), patch(
        "backend.blocks.opex.runner.calculate", side_effect=AssertionError("No OPEX")
    ):
        state = run_stage(store, key, "revenue")
    assert state["stage_runs"]["revenue"]["status"] == "ready", state["stage_runs"][
        "revenue"
    ]
    assert state["results"]["stages"]["revenue"]["result"]["annual"]
    assert set(state["stage_outputs"]) == {"engineering_data", "revenue"}


def test_revenue_uses_explicitly_selected_project_price_basis(study):
    store, key = study
    state = run_stage(store, key, "engineering_data")
    config = state["plan"]["operating_economics"]
    config["price_basis"]["price_period"] = "USD per kg; flat throughout operating life."
    state["plan"]["cost_translation"] = {"target_period": "2026-09"}
    state = store.put(state, state["revision"])
    state = update(store, key, state["revision"], approve=True)
    state = run_stage(store, key, "revenue")
    assert "Revenue needs a dated price basis" in state["results"]["stages"]["revenue"]["issues"][0]

    text = state["revenue_description"] + ". Use the project’s saved USD price basis."
    state = update(store, key, state["revision"], text=text, approve=True)
    state = run_stage(store, key, "revenue")
    stage = state["results"]["stages"]["revenue"]
    assert not stage["issues"]
    assert stage["result"]["basis"] == {"currency": "USD", "price_period": "2026-09"}
    assert "as requested" in stage["result"]["price_basis_notice"]
    assert state["plan"]["operating_economics"]["price_basis"] == config["price_basis"]


def test_opex_preparation_fills_missing_fields_without_overwriting_locked_revenue(study):
    import json
    from backend.blocks.preparation import prepare_stage

    store, key = study
    state = run_stage(store, key, "engineering_data")
    config = state["plan"]["operating_economics"]
    proposal = copy.deepcopy(config)
    proposal["price_basis"]["price_period"] = "2026-09"
    proposal["sales"][0]["unit_price"] = 999
    proposal["materials"] = []
    expected_energy = config.pop("energy")
    state["locked"] = ["operating_economics"]
    state = store.put(state, state["revision"])
    state = update(store, key, state["revision"], approve=True)

    response = {"sections": [{"section": "operating_economics", "value_json": json.dumps(proposal)}]}
    with patch("backend.orchestration.advisor.propose", return_value=(response, {})) as propose:
        prepared = prepare_stage(store, key, "opex", provider=object())
    saved = prepared["plan"]["operating_economics"]
    assert "operating_economics" not in propose.call_args.args[3]
    assert saved["sales"] == config["sales"]
    assert saved["materials"] == config["materials"]
    assert saved["price_basis"] == config["price_basis"]
    assert saved["energy"] == [{**item, "price_basis": proposal["price_basis"]} for item in expected_energy]
    assert prepared["revenue_approval"] == state["revenue_approval"]


def test_manual_stage_order_and_finance_only_consumes_saved_inputs(study):
    store, key = study
    state = run_stage(store, key, "engineering_data")
    update(store, key, state["revision"], approve=True)
    state = run_stage(store, key, "equipment")
    assert set(state["stage_outputs"]) == {"engineering_data", "equipment"}
    state = run_stage(store, key, "capex")
    equipment = copy.deepcopy(state["results"]["stages"]["equipment"])
    state = run_stage(store, key, "opex")
    assert state["stage_runs"]["opex"]["status"] == "ready"
    assert state["stage_runs"]["opex"]["complete"] is False
    assert (
        state["results"]["stages"]["opex"]["result"]["known_cash_opex_subtotal"]
        is not None
    )
    assert "revenue" not in state["stage_runs"]
    state = run_stage(store, key, "revenue")
    assert state["stage_runs"]["opex"]["status"] == "stale"
    state = run_stage(store, key, "opex")
    assert state["stage_runs"]["opex"]["status"] == "ready", state["stage_runs"]["opex"]
    upstream = copy.deepcopy(state["stage_outputs"])
    with patch(
        "backend.blocks.equipment.runner.calculate",
        side_effect=AssertionError("No upstream run"),
    ), patch(
        "backend.blocks.revenue.runner.calculate",
        side_effect=AssertionError("No upstream run"),
    ), patch(
        "backend.blocks.opex.runner.calculate",
        side_effect=AssertionError("No upstream run"),
    ):
        state = run_stage(store, key, "financial")
    assert state["stage_runs"]["financial"]["status"] == "ready", state["stage_runs"][
        "financial"
    ]
    assert len(state["results"]["stages"]["financial"]["result"]["ledger"]) == 22
    assert state["results"]["stages"]["equipment"] == equipment
    assert all(state["stage_outputs"][k] == v for k, v in upstream.items())


def test_equipment_edit_marks_dependents_stale_but_does_not_run_them(study):
    store, key = study
    for stage in ("engineering_data", "equipment", "capex"):
        state = run_stage(store, key, stage)
    rows = copy.deepcopy(state["plan"]["equipment"])
    rows[0]["sizing"]["parameters"]["residence_time_h"]["value"] = 48
    changed = edit(
        store, key, state["revision"], "equipment", rows, "Independent input edit"
    )
    assert changed["stage_runs"]["equipment"]["status"] == "stale"
    assert changed["stage_runs"]["capex"]["status"] == "stale"
    with patch(
        "backend.blocks.equipment.runner.calculate",
        side_effect=AssertionError("No automatic rerun"),
    ):
        blocked = run_stage(store, key, "capex")
    assert blocked["stage_runs"]["capex"]["status"] == "data_required"
    assert blocked["stage_runs"]["capex"]["requires"] == ["equipment"]
    assert blocked["stage_runs"]["engineering_data"]["status"] == "ready"


def test_itemized_opex_can_run_without_capex_or_revenue(study):
    from backend.opex.indexes.garrett.model import CATEGORIES

    store, key = study
    state = run_stage(store, key, "engineering_data")
    config = copy.deepcopy(state["plan"]["operating_economics"])
    config["additional_expenses"] = [
        {
            "id": c.id,
            "name": c.id,
            "category": c.id,
            "annual_allowance": 1,
            "behavior": "fixed",
            "rationale": "Explicit standalone test allowance",
            "uncertainty": "Synthetic test",
        }
        for c in CATEGORIES
        if c.base
    ]
    state["plan"]["operating_economics"] = config
    store.put(state, state["revision"])
    with patch(
        "backend.blocks.capex.runner.calculate", side_effect=AssertionError("No CAPEX")
    ), patch(
        "backend.blocks.revenue.runner.calculate",
        side_effect=AssertionError("No revenue"),
    ):
        state = run_stage(store, key, "opex")
    assert state["stage_runs"]["opex"]["status"] == "ready", state["stage_runs"]["opex"]
    assert (
        state["results"]["stages"]["opex"]["result"]["first_year_cash_opex"] is not None
    )
    assert set(state["stage_outputs"]) == {"engineering_data", "opex"}


def test_currency_and_price_views_never_run_any_stage(study):
    from backend.orchestration.current_prices import current_price_view
    from backend.currency_conversion.assessment import currency_view

    store, key = study
    state = run_stage(store, key, "engineering_data")
    with patch(
        "backend.orchestration.current_prices.run",
        side_effect=AssertionError("No full chain"),
    ), patch(
        "backend.financial_modelling.calculate_financials",
        side_effect=AssertionError("No hidden finance"),
    ):
        opened = currency_view(current_price_view(state), "GBP")
    assert opened["stage_runs"]["engineering_data"]["status"] == "ready"
    assert "financial" not in opened["stage_runs"]


def test_api_upload_is_idle_and_old_full_run_endpoint_is_disabled(tmp_path):
    from fastapi.testclient import TestClient
    from backend.api import app as api

    store = Store(tmp_path / "api.db")
    with patch.object(api, "store", store), patch.object(
        api.executor, "submit", side_effect=AssertionError("No auto queue")
    ):
        client = TestClient(api.app)
        response = client.post(
            "/api/assessments",
            files={
                "file": (
                    "test.xlsx",
                    workbook(),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
            data={
                "use_ai": "true",
                "description": DESCRIPTION,
                "revenue_description": "sells treated water",
            },
        )
        assert response.status_code == 202, response.text
        key = response.json()["id"]
        state = store.get(key)
        assert state["execution_mode"] == MODE
        assert not state["running"] and not state["stage_runs"]
        assert "parsed" not in state
        with patch.object(
            api, "run_engineering_workflow", return_value={"id": key}
        ) as common:
            assert (
                client.post(
                    f"/api/assessments/{key}/run", json={"use_ai": True}
                ).status_code
                == 202
            )
            assert common.call_args.args[0] == key
            assert common.call_args.args[1].use_ai is True
        assert client.get(f"/api/assessments/{key}").status_code == 200
        assert not store.get(key)["stage_runs"]

@pytest.mark.parametrize("with_capital", [False, True])
def test_revenue_ai_ignores_large_equipment_outputs(study, with_capital):
    from backend.blocks.models import Context
    from backend.blocks.shared import operating_proposal

    store, key = study
    state = run_stage(store, key, "engineering_data")
    state["results"]["stages"]["equipment"] = {"result": {"register": "x" * 500000}}
    if with_capital:
        state["results"]["stages"]["capex"] = {
            "result": {"currency": "USD", "period": "early 1987"}
        }

    class ReachedProvider(Exception):
        pass

    class Probe:
        model = "test-revenue-context"

        def generate(self, *, instructions, context, schema):
            assert "equipment" not in context["calculated_stage_summary"]
            assert any(row["kind"] == "material" for row in context["report"]["entities"])
            assert ("materials" in schema["properties"]) == with_capital
            raise ReachedProvider

    source = state["stage_outputs"]["engineering_data"]
    ctx = Context(state, source["report"], {"engineering_data": source}, store, None, Probe(), True)
    with pytest.raises(ReachedProvider):
        operating_proposal(ctx, "revenue")
