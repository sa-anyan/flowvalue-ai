"""Repeated property subheaders and batched source review; no template names required."""

import copy
import json
from io import BytesIO
from unittest.mock import patch

import openpyxl

from backend.ingestion.workbook_pipeline import parse_workbook
from backend.orchestration.workbook_review import review, review_contexts
from backend.tests.test_engineering_review import fixture, response


def workbook():
    book = openpyxl.Workbook()
    sheet = book.active
    sheet.title = "Engineering export"
    for start, offset in [(3, 0), (20, 2)]:
        sheet.cell(start, 2, "Stream Number")
        sheet.cell(start, 4, "hf taken at standard conditions")
        sheet.cell(start + 1, 2, "Description")
        sheet.cell(start + 3, 2, "Component")
        sheet.cell(start + 3, 4, "MW (kg/kmol)")
        sheet.cell(start + 3, 5, "hf (kJ/mol)")
        for col, identifier, text in [
            (
                6,
                1 + offset,
                "Water leaving Filter FT-101AB entering Mixing Tank MT-101",
            ),
            (11, 2 + offset, "Food entering Spray Dryer C-201"),
        ]:
            sheet.cell(start, col, identifier)
            sheet.cell(start + 1, col, text)
            for dc, heading in enumerate(
                ["Cp (kJ/kmol K)", "m (kg/hr)", "n (kmol/hr)", "mol %", "m3/h"]
            ):
                sheet.cell(start + 3, col + dc, heading)
            sheet.cell(start + 4, 2, "Water")
            sheet.cell(start + 4, 4, 18.015)
            sheet.cell(start + 4, 5, -285.5)
            sheet.cell(start + 4, col + 1, 180)
            sheet.cell(start + 4, col + 2, 10)
            sheet.cell(start + 4, col + 4, 0.18)
            sheet.cell(start + 5, col + 4, 0.18)
            sheet.cell(start + 4, col + 3, 1)
            sheet.cell(start + 4, col + 3).number_format = "0.0%"
            sheet.cell(start + 5, 2, "Total")
            sheet.cell(start + 5, col + 1, 180)
            sheet.cell(start + 5, col + 2, 10)
            sheet.cell(start + 8, 2, "Temperature (deg C)")
            sheet.cell(start + 8, col, 25)
            sheet.cell(start + 9, 2, "Pressure (Barg)")
            sheet.cell(start + 9, col, 2)
            sheet.cell(start + 10, 2, "Enhalpy (kJ/hr)")
            sheet.cell(start + 10, col, -3600)
    buffer = BytesIO()
    book.save(buffer)
    return buffer.getvalue()


def test_nested_headers_reference_columns_blank_rows_and_repeated_blocks():
    report = parse_workbook(workbook(), "any-name.xlsx")
    streams = [e for e in report.entities if e.kind == "material"]
    assert [e.identifier for e in streams] == ["1", "2", "3", "4"]
    for stream in streams:
        properties = {v.property: v for v in stream.values}
        assert properties["mass_flow"].normalized_value == 180
        assert properties["volume_flow"].normalized_value == 0.18
        assert properties["component_volume_flow"].normalized_value == 0.18
        assert properties["component_mass_flow"].normalized_value == 180
        assert properties["component_molar_flow"].normalized_value == 10
        assert properties["mole_fraction"].normalized_value == 1
        assert properties["temperature"].normalized_value == 25
        assert properties["pressure"].normalized_unit == "bar_gauge"
        assert properties["enthalpy_flow"].normalized_value == -1
        assert all(v.cell[0] not in {"D", "E"} for v in stream.values)
        assert properties["component_mass_flow"].header_cells
    units = {e.identifier: e for e in report.entities if e.kind == "equipment"}
    assert set(units) == {"FT-101AB", "MT-101", "C-201"}
    assert {e.values[0].normalized_value for e in units.values()} == {
        "Filter",
        "Mixing tank",
        "Spray dryer",
    }
    assert any(
        c.role == "source" and c.equipment_key == units["FT-101AB"].key
        for c in report.connections
    )


def test_review_batches_cover_all_source_cells_and_keep_small_contexts():
    parsed = fixture()
    for i in range(1, 2001):
        parsed["source_cells"].append(
            {"sheet": "Supporting", "cell": f"A{i}", "value": "context " * 35}
        )
    batches = review_contexts(parsed, "Test process", budget=20000)
    covered = {
        (sheet, cell[0])
        for batch in batches
        for sheet, cells in batch["worksheets"].items()
        for cell in cells
    }
    assert covered == {(c["sheet"], c["cell"]) for c in parsed["source_cells"]}
    assert len(batches) > 1
    assert all(len(json.dumps(b)) < 300000 for b in batches)


def test_review_keeps_successful_sections_after_failure():
    parsed = fixture()
    contexts = review_contexts(parsed, "process")

    class Provider:
        model = "fake-no-network"

        def generate(self, **kwargs):
            return response()

    class Cache:
        def __init__(self):
            self.calls = 0

        def cached(self, key, call):
            self.calls += 1
            if self.calls == 2:
                raise ValueError("Simulated section failure")
            return call(), False

    saved = copy.deepcopy(parsed)
    with patch(
        "backend.orchestration.workbook_review.review_contexts",
        return_value=contexts * 2,
    ):
        report, interpretation, _decisions, metadata = review(
            parsed, "process", Cache(), Provider()
        )
    assert metadata["status"] == "partial"
    assert len(report["entities"]) == 2
    assert metadata["batches"][0]["status"] == "reviewed"
    assert metadata["batches"][1]["status"] == "unreviewed"
    assert any("requires review" in note for note in interpretation["scope_notes"])
    assert parsed == saved


def test_review_manifest_exposes_existing_equipment_names_for_supporting_sheets():
    parsed = fixture()
    from backend.orchestration.workbook_review import apply_review
    effective, _ = apply_review(parsed, response())
    parsed['report'] = effective
    contexts = review_contexts(parsed, 'process')
    unit = next(e for e in contexts[0]['register_keys'] if e['kind'] == 'equipment')
    assert unit['name'] == 'Neutralisation vessel'
    assert unit['classification'] == 'Agitated neutralisation reactor'
