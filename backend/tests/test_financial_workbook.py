"""M4.6: the financial workbook is written from the saved study and reconciles."""

import copy
import socket
import tempfile
from decimal import Decimal as D
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import openpyxl
import pytest

from backend.dashboard_reporting.financial_workbook import build_financial_workbook, reconcile
from backend.orchestration.ingest import parse
from backend.orchestration.service import _execute_connected_reference as execute
from backend.orchestration.service import new_assessment
from backend.orchestration.store import Store
from backend.revenue.authority import update
from backend.tests.test_stage_connections import DESCRIPTION, plan_for, workbook


@pytest.fixture(scope="module")
def study():
    data = workbook()
    with tempfile.TemporaryDirectory() as folder, patch.object(
        socket.socket, "connect", side_effect=AssertionError("No network")
    ):
        store = Store(Path(folder) / "t.db")
        state = new_assessment(store, data, "synthetic.xlsx", DESCRIPTION, "sells treated water")
        parsed = parse(data, state["filename"])
        state.update(parsed=parsed, plan=plan_for(parsed["report"]), running=False)
        state = store.put(state, state["revision"])
        state = update(store, state["id"], state["revision"], approve=True)
        yield execute(store, state["id"], use_ai=False)


def test_workbook_reconciles_and_reads_back(study):
    content, summary = build_financial_workbook(study)
    assert summary["reconciled"] and not summary["readback_mismatches"]
    assert summary["checks"] > 3 and summary["numbers_written"] > 100
    book = openpyxl.load_workbook(BytesIO(content), data_only=True)
    assert book.sheetnames == ["Summary", "Cash flow", "Revenue", "OPEX", "OPEX lines", "Reconciliation", "Assumptions", "Sources"]
    results = [row[7].value for row in book["Reconciliation"].iter_rows(min_row=2) if row[0].value and row[7].value]
    assert results and set(results) == {"pass"}


def test_workbook_numbers_equal_saved_ledger(study):
    content, _ = build_financial_workbook(study)
    sheet = openpyxl.load_workbook(BytesIO(content), data_only=True)["Cash flow"]
    ledger = sorted(study["results"]["stages"]["financial"]["result"]["ledger"], key=lambda l: l["period"]["year"])
    revenue_row = next(r for r in sheet.iter_rows(min_row=4) if r[0].value == "Revenue")
    for cell, period in zip(revenue_row[1:], ledger):
        assert D(str(cell.value)) == pytest.approx(D(period["revenue"]), rel=D("1e-12"))
    metrics = dict(study["results"]["stages"]["financial"]["result"]["metrics"])
    summary = openpyxl.load_workbook(BytesIO(content), data_only=True)["Summary"]
    npv = next(r[1].value for r in summary.iter_rows() if r[0].value == "project_npv")
    assert D(str(npv)) == pytest.approx(D(metrics["project_npv"]["value"]), rel=D("1e-12"))


def test_tampered_ledger_fails_reconciliation(study):
    state = copy.deepcopy(study)
    ledger = state["results"]["stages"]["financial"]["result"]["ledger"]
    operating = next(l for l in ledger if D(l["revenue"]) > 0)
    operating["revenue"] = str(D(operating["revenue"]) + 1)
    failed = [c for c in reconcile(state) if not c["passed"]]
    assert [c["check"] for c in failed] == ["Ledger revenue = revenue stage"]
    _, summary = build_financial_workbook(state)
    assert summary["reconciled"] is False


def test_no_financial_result_no_workbook(study):
    state = copy.deepcopy(study)
    state["results"]["stages"]["financial"]["result"] = {}
    with pytest.raises(ValueError, match="Run the financial stage first"):
        build_financial_workbook(state)


def test_opex_lines_sheet_shows_payment_owner_and_escalation(study):
    content, _ = build_financial_workbook(study)
    sheet = openpyxl.load_workbook(BytesIO(content), data_only=True)["OPEX lines"]
    rows = [[c.value for c in r] for r in sheet.iter_rows(min_row=3) if r[0].value]
    feed = next(r for r in rows if str(r[0]).startswith("feed:"))
    assert feed[8] == "project" and feed[9].startswith("Study price basis")
