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


def test_stray_partial_component_row_does_not_hide_stream_flows():
    """Finding 9 root cause: a partial "Component" row above the real subheader
    left a whole stream block without flows, so the AI sometimes lost them."""
    book = openpyxl.Workbook()
    ws = book.active
    ws.title = "Material and Energy Balance"
    rows = {
        3: {2: "Stream Number", 6: "1", 11: "2"},
        4: {2: "Description", 6: "Feed to Unit U-1", 11: "Product from Unit U-1"},
        6: {2: "Component", 4: "MW (kg/kmol)"},  # stray partial header
        7: {2: "Component", 4: "MW (kg/kmol)", 7: "m (kg/h)", 8: "n (kmol/h)", 12: "m (kg/h)", 13: "n (kmol/h)"},
        8: {2: "Water", 4: 18.015, 7: 900, 8: 49.96, 12: 0, 13: 0},
        9: {2: "Hydrogen", 4: 2.016, 7: 0, 8: 0, 12: 100, 13: 49.6},
        18: {2: "Total", 7: 900, 8: 49.96, 12: 100, 13: 49.6},
    }
    for r, cols in rows.items():
        for c, value in cols.items():
            ws.cell(row=r, column=c, value=value)
    data = BytesIO()
    book.save(data)
    report = parse(data.getvalue(), "stray-header.xlsx")["report"]
    flows = {e["identifier"]: {(v["property"], v.get("component")): v["normalized_value"] for v in e["values"]}
             for e in report["entities"] if e["kind"] == "material"}
    assert flows["1"][("mass_flow", None)] == 900
    assert flows["2"][("component_mass_flow", "Hydrogen")] == 100


def test_unit_excluded_by_decision_is_shown_in_basis_of_estimate(capex_study):  # noqa: F811
    from backend.blocks.execution import view
    from backend.dashboard_reporting.basis_of_estimate import build_basis_of_estimate, render_markdown

    store, key = capex_study
    state = view(store.get(key))
    state["results"]["stages"]["equipment"]["result"]["pricing_coverage"]["register_completeness"] = {
        "status": "no_unregistered_units_named", "possibly_missing": [],
        "resolved": [{"family": "reverse_osmosis", "label": "RO / reverse osmosis unit",
                      "decision": "out_of_scope", "basis": "Site supplies purified water"}]}
    boe = build_basis_of_estimate(state)
    assert boe["exclusions_and_gaps"]["excluded_units"] == [
        {"label": "RO / reverse osmosis unit", "decision": "out_of_scope", "basis": "Site supplies purified water"}]
    assert not any("Possibly missing" in i for i in boe["open_items"])
    assert "Units excluded by decision: RO / reverse osmosis unit (out_of_scope: Site supplies purified water)" in render_markdown(boe)


def test_ro_models_with_implausible_coefficients_are_held():
    """Merged-code PEM run: an RO unit was priced at US$0.90 by a Seider RO model."""
    from backend.equipment_costing.indexes.openpytea.adapter import estimate_cost
    from backend.equipment_costing.indexes.openpytea.registry import catalogue

    for key in ("openpytea:osmosis_brackish_seider_2013", "openpytea:osmosis_seawater_seider_2013"):
        model = catalogue()[key]
        assert model["status"] == "disabled"
        assert any("FlowValue hold" in r for r in model["disabled_reasons"])
        with pytest.raises(ValueError, match="MODEL_DISABLED"):
            estimate_cost(key, 0.2, size_unit="US_MGD", allow_unverified=True)


def test_equipment_only_sheet_does_not_claim_the_workbook_has_no_streams():
    from backend.ingestion.balance.models import BalanceReport
    from backend.ingestion.workbook_pipeline import review_registers

    report = BalanceReport.model_validate(parse(_workbook(), "ro.xlsx")["report"])
    equipment = next(e for e in report.entities if e.kind == "equipment").model_copy(deep=True)
    equipment.key = "cover:RO"
    equipment.identifier = "RO"
    equipment.id_evidence = equipment.id_evidence.model_copy(update={"sheet": "Cover Page"})
    report.entities.append(equipment)
    report.issues = []
    review_registers(report)
    assert not [i for i in report.issues if i.code == "missing_material_streams"]


def test_register_decisions_carry_over_to_a_reupload_of_the_same_file(tmp_path):
    from backend.equipment_resolution.register_completeness import carry_over

    store = Store(tmp_path / "s.sqlite")
    first = store.create({"source_sha256": "abc", "plan": {"register_review": {
        "reverse_osmosis": {"decision": "out_of_scope", "basis": "Site supplies purified water"}}}}, b"")
    store.create({"source_sha256": "other", "plan": {"register_review": {
        "pump": {"decision": "not_equipment", "basis": "x"}}}}, b"")
    again = {"id": "new", "source_sha256": "abc", "plan": {}}
    assert carry_over(store, again) == 1
    decision = again["plan"]["register_review"]["reverse_osmosis"]
    assert decision["decision"] == "out_of_scope" and decision["basis"] == "Site supplies purified water"
    assert decision["carried_over_from"]["assessment"] == first["id"]
    assert again["assumptions"]["register_review"]["status"] == "carried_over"
    # The carried decision resolves the flag exactly as the original did.
    report = parse(_workbook(), "ro.xlsx")["report"]
    assert check(report, plan=again["plan"])["status"] == "no_unregistered_units_named"


def test_carry_over_needs_the_exact_same_file_and_never_overwrites(tmp_path):
    from backend.equipment_resolution.register_completeness import carry_over

    store = Store(tmp_path / "s.sqlite")
    store.create({"source_sha256": "abc", "plan": {"register_review": {
        "reverse_osmosis": {"decision": "out_of_scope", "basis": "x"}}}}, b"")
    edited = {"id": "new", "source_sha256": "abc-edited", "plan": {}}
    assert carry_over(store, edited) == 0 and "register_review" not in edited["plan"]
    own = {"id": "new2", "source_sha256": "abc", "plan": {"register_review": {
        "reverse_osmosis": {"decision": "included_in", "basis": "Part of the EL-101 package"}}}}
    assert carry_over(store, own) == 0
    assert own["plan"]["register_review"]["reverse_osmosis"]["decision"] == "included_in"


def test_upload_endpoint_carries_decisions_for_the_same_workbook(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    import backend.api.app as api

    store = Store(tmp_path / "api.sqlite")
    monkeypatch.setattr(api, "store", store)
    client = TestClient(api.app)
    content = _workbook()
    first = client.post("/api/assessments", files={"file": ("pem.xlsx", content)}, data={"description": "Test"})
    assert first.status_code == 202
    saved = store.get(first.json()["id"])
    saved["plan"]["register_review"] = {"reverse_osmosis": {"decision": "out_of_scope", "basis": "Founder decision"}}
    store.put(saved, saved["revision"])
    second = client.post("/api/assessments", files={"file": ("pem.xlsx", content)}, data={"description": "Test"})
    carried = store.get(second.json()["id"])["plan"]["register_review"]["reverse_osmosis"]
    assert carried["decision"] == "out_of_scope"
    assert carried["carried_over_from"]["assessment"] == first.json()["id"]
