from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

import openpyxl
import pytest

from app.parsers.inputs.xlsm_adapter import parse_xlsm


def workbook(rows):
    book = openpyxl.Workbook()
    for row in rows:
        book.active.append(row)
    output = BytesIO()
    book.save(output)
    return output.getvalue()


def test_xlsm_equipment_and_source():
    report = parse_xlsm(workbook([['Stream Number', 1, 2], ['Description', 'Feed from pump P-101', 'Feed to reactor R-201']]), 'sample.xlsm')
    assert [e.identifier for e in report.entities if e.kind == "equipment"] == ['P-101', 'R-201']
    assert report.entities[0].id_evidence.cell == 'B2'
    assert report.entities[0].status == 'inferred'
    assert report.checks == []


def test_xlsm_ignores_macro_payload_and_formula():
    raw = workbook([['Stream 1: Feed from pump P-101'], ['=1+1']])
    output = BytesIO()
    with ZipFile(BytesIO(raw)) as source, ZipFile(output, 'w', ZIP_DEFLATED) as target:
        for item in source.infolist():
            target.writestr(item, source.read(item.filename))
        target.writestr('xl/vbaProject.bin', b'not executed')
    assert len([e for e in parse_xlsm(output.getvalue(), 'sample.xlsm').entities if e.kind == 'equipment']) == 1


def test_xlsm_malformed():
    with pytest.raises(ValueError):
        parse_xlsm(b'bad', 'bad.xlsm')


def test_untagged_and_new_streams_are_retained():
    rows = [['Stream Number', 13, 14, 15],
            ['Description', 'Treated water to mains', 'Biomass to digestion', 'Additional recycle stream'],
            ['Component', 'm3/h', 'm3/h', 'm3/h'],
            ['Temperature (C)', 30, 31, 32]]
    report = parse_xlsm(workbook(rows), 'additional.xlsm')
    streams = [e for e in report.entities if e.kind == 'material']
    assert [e.identifier for e in streams] == ['13', '14', '15']
    assert not any(e.kind == 'equipment' for e in report.entities)
    assert streams[1].id_evidence.cell == 'C2'


def test_identical_descriptions_in_separate_blocks_keep_sources():
    report = parse_xlsm(workbook([
        ['Stream Number', 1], ['Description', 'Recycle water outlet'], [],
        ['Stream Number', 1], ['Description', 'Recycle water outlet'],
    ]), 'blocks.xlsm')
    assert [e.id_evidence.cell for e in report.entities] == ['B2', 'B5']
