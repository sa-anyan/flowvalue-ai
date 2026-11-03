"""Large compressed workbooks pass; file-size and expansion guards remain active."""
from io import BytesIO
from zipfile import ZIP_STORED, ZipFile

import openpyxl
import pytest

from backend.ingestion.balance.workbook import read_book
from backend.ingestion.limits import MAX_WORKBOOK_BYTES
from backend.orchestration.ingest import parse


def large_workbook():
    book = openpyxl.Workbook()
    sheet = book.active
    sheet.append(['Stream ID', 'Mass flow (kg/h)', 'Temperature (C)', 'Pressure (bar)'])
    sheet.append(['S-101', 100, 25, 1])
    buffer = BytesIO()
    book.save(buffer)
    # Non-compressible report payload: exercise compressed upload size without
    # manufacturing millions of cells or relaxing XML expansion safeguards.
    with ZipFile(buffer, 'a', compression=ZIP_STORED) as archive:
        archive.writestr('xl/media/report.bin', b'x' * (8 * 1024 * 1024))
    return buffer.getvalue()


def test_eight_mib_workbook_is_parsed_in_isolated_worker():
    content = large_workbook()
    assert 8 * 1024 * 1024 < len(content) < MAX_WORKBOOK_BYTES
    result = parse(content, 'large-engineering-report.xlsx')
    assert result['report']['entities']


def test_workbook_over_twenty_mib_is_rejected_before_decoding():
    for reader in (read_book, parse):
        with pytest.raises(ValueError, match='20 MiB'):
            reader(b'x' * (MAX_WORKBOOK_BYTES + 1), 'oversize.xlsx')
