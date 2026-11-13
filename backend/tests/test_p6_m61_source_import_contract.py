"""P6 M6.1: portable source-stream handoff contracts; no private workbooks."""

from backend.orchestration.pipeline import source_streams


def _stream(values, key="material:case-a", identifier="S-01"):
    return {"kind": "material", "key": key, "identifier": identifier, "values": values}


def _flow(value, *, status="verified", unit="kg/h", cell="C7"):
    return {"property": "mass_flow", "normalized_value": value,
            "normalized_unit": unit, "status": status, "workbook": "synthetic.xlsx",
            "sheet": "Balance", "cell": cell, "id": "evidence:" + cell}


def test_import_handoff_preserves_source_and_zero():
    report = {"entities": [_stream([_flow(0)])], "extracted_on": "2026-11-12"}
    rows = source_streams(report)
    assert len(rows) == 1
    assert rows[0]["flow"]["value"] == "0"
    assert rows[0]["flow"]["source"] == "synthetic.xlsx!Balance!C7"
    assert rows[0]["source_references"] == ["evidence:C7"]
    assert rows[0]["boundary"] == "unresolved"


def test_import_handoff_does_not_promote_missing_unsupported_or_conflicting_flow():
    cases = [[], [_flow(None)], [_flow(5, unit="t/h")],
             [_flow(5, status="unresolved")],
             [_flow(5, cell="C7"), _flow(6, cell="C8")]]
    for values in cases:
        assert source_streams({"entities": [_stream(values)]}) == []


def test_import_handoff_does_not_merge_different_stream_keys():
    report = {"entities": [_stream([_flow(5)], "material:a", "S-01"),
                           _stream([_flow(5, cell="D7")], "material:b", "S-01")]}
    rows = source_streams(report)
    assert [row["id"] for row in rows] == ["material:a", "material:b"]
