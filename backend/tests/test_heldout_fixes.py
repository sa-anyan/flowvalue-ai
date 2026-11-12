"""Fixes from the held-out PEM run (findings 2 and 3), with synthetic data."""

import json
from io import BytesIO

import openpyxl
import pytest

from backend.equipment_resolution.register_completeness import check
from backend.ingestion.design_basis import extract
from backend.orchestration.ingest import parse
from backend.orchestration.store import Store


def _cells(rows, sheet="Basis"):
    from openpyxl.utils import get_column_letter

    out = []
    for r, row in enumerate(rows, 1):
        for c, value in enumerate(row, 1):
            if value is not None:
                out.append({"sheet": sheet, "cell": f"{get_column_letter(c)}{r}", "value": value, "formula": None})
    return out


def test_design_basis_table_with_gaps_units_and_notes():
    cells = _cells([
        ["Basis and parameters"],
        [],
        ["Parameter", "Value", "Unit", "Type", "Notes"],
        [],
        ["Specific electricity", 55.5, "kWh/kg", "Literature", "System basis"],
        ["Water recovery", 0.85, "fraction", "Assumed"],
        ["Comment row without a number", "n/a"],
        [],
        ["Coolant cp", 4.18, "kJ/(kg K)"],
        [], [], [],
        ["Unrelated", 1, "x"],
    ])
    items = extract(cells)
    assert [(i["parameter"], i["value"], i["unit"]) for i in items] == [
        ("Specific electricity", 55.5, "kWh/kg"), ("Water recovery", 0.85, "fraction"), ("Coolant cp", 4.18, "kJ/(kg K)")]
    assert items[0]["id"] == "Basis!B5" and items[0]["notes"] == {"type": "Literature", "notes": "System basis"}


def test_stream_tables_alone_give_no_design_basis():
    cells = _cells([["Stream ID", "Description", "Mass flow (kg/h)"], ["S-1", "Feed", 100]])
    assert extract(cells) == []


def _workbook():
    book = openpyxl.Workbook()
    balance = book.active
    balance.title = "Balance"
    balance.append(["Stream ID", "Description", "Mass flow (kg/h)", "Temperature (C)", "Pressure (bar)"])
    balance.append(["S-101", "Raw water to RO", 1000, 25, 1])
    balance.append(["S-102", "RO permeate to Storage Tank T-101", 850, 25, 1])
    basis = book.create_sheet("Basis")
    basis.append(["Parameter", "Value", "Unit"])
    basis.append(["Specific electricity", 55.5, "kWh/kg"])
    data = BytesIO()
    book.save(data)
    return data.getvalue()


def test_ai_receives_the_workbook_design_basis(tmp_path):
    from backend.orchestration.advisor import propose
    from backend.orchestration.service import empty_plan

    parsed = parse(_workbook(), "basis.xlsx")
    seen = []

    class Provider:
        model = "test-model"

        def generate(self, *, instructions, context, schema):
            seen.append(context)
            raise RuntimeError("stop after capturing the request")

    with pytest.raises(Exception):
        propose(parsed, "Water purification", empty_plan(), [], Store(tmp_path / "c.sqlite"), Provider(),
                requested_sections=("opex",))
    sent = json.dumps(seen[0], default=str)
    assert "Basis!B2" in sent and "55.5" in sent and "Specific electricity" in sent


def test_unit_named_in_streams_but_not_registered_is_flagged_and_can_be_resolved():
    report = parse(_workbook(), "ro.xlsx")["report"]
    result = check(report)
    assert result["status"] == "unconfirmed"
    assert [m["family"] for m in result["possibly_missing"]] == ["reverse_osmosis"]
    assert len(result["possibly_missing"][0]["evidence"]) >= 2  # both RO stream mentions
    # The tank is registered (T-101), so it is not flagged.
    assert "tank" not in {m["family"] for m in result["possibly_missing"]}
    # A recorded decision with a basis resolves the flag; without a basis it does not.
    assert check(report, plan={"register_review": {"reverse_osmosis": {"decision": "out_of_scope"}}})["possibly_missing"]
    resolved = check(report, plan={"register_review": {"reverse_osmosis": {
        "decision": "out_of_scope", "basis": "Supplied by the site utility"}}})
    assert resolved["status"] == "no_unregistered_units_named" and resolved["resolved"][0]["basis"]


def test_ro_acronym_needs_capitals_but_full_name_does_not():
    from backend.equipment_resolution.register_completeness import _families

    assert "reverse_osmosis" in _families("Raw water to RO")
    assert "reverse_osmosis" in _families("reverse osmosis permeate")
    assert "reverse_osmosis" not in _families("Product to a pro buyer")


def test_possibly_missing_unit_blocks_coverage_claim_in_basis_of_estimate(capex_study):  # noqa: F811
    from backend.blocks.execution import view
    from backend.dashboard_reporting.basis_of_estimate import build_basis_of_estimate, render_markdown

    store, key = capex_study
    state = view(store.get(key))
    coverage = state["results"]["stages"]["equipment"]["result"]["pricing_coverage"]
    coverage["register_completeness"] = {
        "status": "unconfirmed", "possibly_missing": [{
            "family": "reverse_osmosis", "label": "RO / reverse osmosis unit",
            "evidence": [{"stream": "1", "text": "Raw water to RO", "source": "Balance!B2"}]}]}
    boe = build_basis_of_estimate(state)
    assert boe["coverage"]["tiers"]["meets_coverage_target_without_assumptions"] is False
    assert any(i.startswith("Possibly missing equipment: RO") for i in boe["open_items"])
    assert "### Possibly missing equipment" in render_markdown(boe)


from backend.tests.test_basis_of_estimate import capex_study  # noqa: E402,F401  (fixture)
