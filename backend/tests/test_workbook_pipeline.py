from hashlib import sha256
from io import BytesIO
from pathlib import Path

import openpyxl

from app.parsers.workbook_pipeline import parse_workbook


def data(rows):
    book = openpyxl.Workbook()
    for row in rows:
        book.active.append(row)
    output = BytesIO()
    book.save(output)
    raw = output.getvalue()
    folder = Path(__file__).resolve().parents[2] / "outputs/balance-parser-tests/pipeline-v2"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{sha256(raw).hexdigest()[:16]}.xlsx").write_bytes(raw)
    return raw


def test_explicit_routes_and_variable_width_components():
    report = parse_workbook(data([
        ['Stream Number', 1, None, 2],
        ['Description', 'Water from tank T-101 to pump P-201', None, 'Water to discharge'],
        ['Component', 'm3/h', 'kg/h', 'm3/h'],
        ['Water', 2, 2000, 2],
        ['Total', 2, 2000, 2],
    ]), 'variable.xlsm')
    streams = [e for e in report.entities if e.kind == 'material']
    assert len(streams) == 2
    assert any(v.property == 'component_mass_flow' and v.original_value == 2000 for v in streams[0].values)
    assert any(v.property == 'source' and v.normalized_value == 'T-101' for v in streams[0].values)
    assert any(v.property == 'destination' and v.normalized_value == 'P-201' for v in streams[0].values)
    assert {e.identifier for e in report.entities if e.kind == 'equipment'} == {'T-101', 'P-201'}
    assert report.tables


def test_vertical_rows_use_generic_adapter_with_explicit_endpoints():
    report = parse_workbook(data([
        ['Stream ID', 'Mass flow (kg/h)', 'Source', 'Destination'],
        ['FEED-A', 100, 'T-101', 'R-201'],
        ['OUT-B', 90, 'R-201', 'outside'],
    ]), 'vertical.xlsx')
    assert {'FEED-A', 'OUT-B'} <= {e.identifier for e in report.entities if e.kind == 'material'}
    assert {'T-101', 'R-201'} <= {e.identifier for e in report.entities if e.kind == 'equipment'}


def test_ambiguous_mentions_are_not_connected():
    report = parse_workbook(data([
        ['Stream Number', 1],
        ['Description', 'Water from tanks T-101 and T-102 to pump P-201'],
    ]), 'ambiguous.xlsm')
    stream = next(e for e in report.entities if e.kind == 'material')
    assert not any(v.property == 'source' for v in stream.values)
    assert any(v.property == 'destination' for v in stream.values)


def test_missing_volume_does_not_hide_component_mass():
    report = parse_workbook(data([
        ['Stream Number', 1, None, 2],
        ['Description', 'Water outlet', None, 'Biomass outlet'],
        ['Component', 'm3/h', 'kg/h', 'm3/h', 'kg/h'],
        ['Biomass', '-', 100, '-', 200],
        ['Total', 0, 0, 0, 0],
    ]), 'component.xlsm')
    streams = [e for e in report.entities if e.kind == 'material']
    assert any(v.component == 'Biomass' and v.original_value == 200 for v in streams[1].values)
    assert sum(i.code == 'component_total_mismatch' for i in report.issues) == 2
