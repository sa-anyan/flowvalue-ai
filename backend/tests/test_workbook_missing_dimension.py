"""Held-out run finding P2-01: a valid .xlsx without the optional <dimension>
record was rejected as malformed (read-only openpyxl reports no size)."""

import re
import zipfile
from io import BytesIO

import openpyxl
import pytest

from backend.ingestion.balance.workbook import read_book


def _without_dimension(rows):
    book = openpyxl.Workbook()
    sheet = book.active
    sheet.title = "Balance"
    for row in rows:
        sheet.append(row)
    raw = BytesIO()
    book.save(raw)
    source = zipfile.ZipFile(BytesIO(raw.getvalue()))
    out = BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as target:
        for item in source.infolist():
            data = source.read(item.filename)
            if item.filename.startswith("xl/worksheets/sheet"):
                data = re.sub(rb"<dimension[^>]*/>", b"", data)
            target.writestr(item, data)
    return out.getvalue()


def test_workbook_without_dimension_record_is_read():
    content = _without_dimension([["Stream ID", "Mass flow (kg/h)"], ["S-1", 100], ["S-2", 80]])
    sheets, _ = read_book(content, "no-dimension.xlsx")
    sheet = sheets[0]
    assert (sheet.rows, sheet.cols) == (3, 2)
    assert sheet.cells[2, 2].value == 100


def test_size_limits_still_apply_without_dimension(monkeypatch):
    import backend.ingestion.balance.workbook as module

    monkeypatch.setattr(module, "MAX_ROWS", 2)
    content = _without_dimension([["a"], ["b"], ["c"], ["d"]])
    with pytest.raises(ValueError, match="exceeds"):
        read_book(content, "too-long.xlsx")
