"""M3.6: Basis of Estimate generated from the saved study only."""

import copy
from decimal import Decimal
from unittest.mock import patch

import pytest

from backend.blocks.execution import run_stage, view
from backend.dashboard_reporting.basis_of_estimate import (
    build_basis_of_estimate,
    render_html,
    render_markdown,
)
from backend.orchestration.service import edit
from backend.tests.test_estimate_class import _study


@pytest.fixture
def capex_study(tmp_path):
    store, key = _study(tmp_path)
    for stage in ("engineering_data", "equipment", "capex"):
        state = run_stage(store, key, stage)
    return store, key


def test_not_available_before_capex(tmp_path):
    store, key = _study(tmp_path)
    boe = build_basis_of_estimate(view(store.get(key)))
    assert boe["status"] == "not_available"
    assert "Run CAPEX first" in render_markdown(boe)


def test_report_comes_from_saved_capex_result(capex_study):
    store, key = capex_study
    state = view(store.get(key))
    capex = state["results"]["stages"]["capex"]["result"]
    with patch("backend.blocks.capex.runner.calculate", side_effect=AssertionError("no rerun")):
        boe = build_basis_of_estimate(state)
    assert boe["status"] == "current"
    assert boe["totals"]["total_capex"] == capex["total_capex"]
    assert boe["checks"]["reconciliation"]["status"] == "reconciled"
    assert boe["estimate_class"] == capex["estimate_class"]
    assert boe["identification"]["capex_run"]["output_hash"] == state["stage_runs"]["capex"]["output_hash"]
    tags = [r["tag"] for r in boe["scope"]["priced_equipment"]]
    assert tags == [l["equipment_tag"] for l in state["results"]["stages"]["equipment"]["result"]["equipment"] if l["amount"] is not None]
    assert any("Garrett" in s["reference"] for s in boe["sources"])
    assert any("18R-97" in s["reference"] for s in boe["sources"])
    assert "No source for capital category: owners_costs" in boe["open_items"]
    assert any("reviewer has not confirmed" in i for i in boe["open_items"])
    assert any("not yet verified" in i for i in boe["open_items"])


def test_unpriced_items_are_listed_with_reason_and_never_valued(capex_study):
    store, key = capex_study
    state = view(store.get(key))
    capex = state["results"]["stages"]["capex"]["result"]
    capex["unpriced_equipment"] = ["HX-9"]
    state["results"]["stages"]["equipment"]["result"]["pricing_coverage"] = {
        "review_queue": [{"equipment_tag": "HX-9", "reason": "Duty not confirmed", "issues": ["MODEL_OUT_OF_RANGE"]}]}
    boe = build_basis_of_estimate(state)
    item = boe["scope"]["unpriced_equipment"][0]
    assert item["tag"] == "HX-9" and item["reason"] == "Duty not confirmed"
    assert "not zero" in item["value"]
    assert "Unpriced equipment: HX-9" in boe["open_items"]
    assert "**HX-9**" in render_markdown(boe)


def test_breakdown_mismatch_is_reported(capex_study):
    store, key = capex_study
    state = view(store.get(key))
    capex = state["results"]["stages"]["capex"]["result"]
    counted = next(b for b in capex["breakdown"] if b["counted"] and b["amount"])
    counted["amount"] = str(Decimal(counted["amount"]) + 1)
    boe = build_basis_of_estimate(state)
    assert boe["checks"]["reconciliation"]["status"] == "mismatch"
    assert "Capital breakdown does not reconcile to total CAPEX" in boe["open_items"]


def test_edit_after_capex_marks_report_stale(capex_study):
    store, key = capex_study
    state = store.get(key)
    edit(store, key, state["revision"], "estimate_class",
         {"design_maturity": {"capacity_and_products": "complete"}}, "Declare capacity")
    boe = build_basis_of_estimate(view(store.get(key)))
    assert boe["status"] == "stale"
    assert boe["open_items"][0].startswith("CAPEX inputs changed")
    assert boe["user_assumptions"]["estimate_class"]["rationale"] == "Declare capacity"
    assert "**Stale:**" in render_markdown(boe)


def test_markdown_and_html_render_every_section(capex_study):
    store, key = capex_study
    boe = build_basis_of_estimate(view(store.get(key)))
    md = render_markdown(boe)
    for n, title in enumerate(("Price basis", "Estimate class", "Capital summary", "Scope: priced equipment",
                               "Capital breakdown and method", "Exclusions and gaps", "Checks",
                               "User assumptions", "Sources", "Open items"), 1):
        assert f"## {n}. {title}" in md
    hostile = copy.deepcopy(boe)
    hostile["identification"]["source_file"] = "<script>x</script>"
    assert "<script>" not in render_html(hostile)


def test_api_formats(tmp_path, capex_study):
    from fastapi.testclient import TestClient
    from backend.api import app as api

    store, key = capex_study
    with patch.object(api, "store", store):
        client = TestClient(api.app)
        url = f"/api/assessments/{key}/basis-of-estimate"
        assert client.get(url).json()["checks"]["reconciliation"]["status"] == "reconciled"
        md = client.get(url, params={"format": "markdown"})
        assert md.headers["content-type"].startswith("text/markdown") and "# Basis of Estimate" in md.text
        assert client.get(url, params={"format": "html"}).text.startswith("<!doctype html>")
        assert client.get(url, params={"format": "pdf"}).status_code == 422
