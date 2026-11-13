"""M2.1 schema compatibility across three workbook layouts."""

from decimal import Decimal
from hashlib import sha256

import pytest

from backend.ingestion.balance.models import BalanceReport
from backend.orchestration.ingest import parse
from backend.tests.test_sizing_cross_file import FIXTURES


@pytest.mark.parametrize("layout", ["rows", "columns", "rows_units"])
def test_layouts_share_canonical_stream_and_source_contract(layout):
    path = FIXTURES / f"{layout}.xlsx"
    content = path.read_bytes()
    report = BalanceReport.model_validate(parse(content, path.name)["report"])
    assert report.sha256 == sha256(content).hexdigest()
    assert len({entity.key for entity in report.entities}) == len(report.entities)
    stream = next(e for e in report.entities if e.kind == "material" and e.identifier == "P-IN")
    flow = next(v for v in stream.values if v.property == "volume_flow")
    assert flow.observation_id and flow.sheet and flow.cell
    assert Decimal(str(flow.normalized_value)) == Decimal("3.6")
    assert flow.normalized_unit == "m3/h"
    assert path.read_bytes() == content
