"""M6.4 synthetic-only preview contract; no API or approval side effects."""

from copy import deepcopy

from backend.ingestion.mapping_preview import preview


def _evidence(id, value, normalized, status="verified"):
    return {
        "id": id, "workbook": "synthetic.xlsx", "sheet": "A", "cell": id,
        "property": "mass_flow", "original_value": value, "original_unit": "t/h",
        "normalized_value": normalized, "normalized_unit": "kg/h",
        "status": status,
    }


def _entity(key, evidence, tag="S-01"):
    return {
        "key": key, "kind": "material", "identifier": tag, "case": "A",
        "id_evidence": _evidence("id-" + key, tag, tag),
        "values": [evidence],
    }


def test_preview_preserves_source_zero_and_is_pure():
    report = {
        "sha256": "a" * 64, "parser_version": "test",
        "entities": [_entity("s1", _evidence("B2", 0, 0))],
    }
    original = deepcopy(report)
    result = preview(report)
    assert report == original
    row = next(r for r in result["observations"] if r["evidence_id"] == "B2")
    assert row["source"]["value"] == 0
    assert row["proposed"]["value"] == 0
    assert not row["needs_review"]
    assert result["source_sha256"] == "a" * 64


def test_missing_and_unresolved_are_not_coerced_to_zero():
    report = {"entities": [_entity("s1", _evidence("B2", None, None, "unresolved"))]}
    row = next(r for r in preview(report)["observations"] if r["evidence_id"] == "B2")
    assert row["source"]["value"] is None
    assert row["proposed"]["value"] is None
    assert row["needs_review"]


def test_conflicts_and_duplicate_display_tags_remain_visible():
    report = {
        "entities": [
            _entity("s1", _evidence("B2", 1, 1000)),
            _entity("s2", _evidence("C2", 2, 2000)),
        ],
        "issues": [{"code": "conflicting_source", "evidence_ids": ["B2", "C2"]}],
    }
    result = preview(report)
    assert len(result["observations"]) == 4
    assert result["repeated_display_tags"] == [
        {"kind": "material", "identifier": "S-01", "case": "A", "count": 2}
    ]
    assert result["issues"][0]["code"] == "conflicting_source"


def test_text_mentions_and_explicit_links_are_never_auto_verified():
    report = {
        "entities": [],
        "connections": [
            {"stream_key": "s1", "equipment_key": "p1", "role": "mention",
             "basis": "mention", "status": "inferred", "evidence_ids": ["B2"]},
            {"stream_key": "s2", "equipment_key": "p2", "role": "destination",
             "basis": "explicit_field", "status": "verified", "evidence_ids": ["C2"]},
        ],
    }
    result = preview(report)
    assert all(not row["verified_physical_link"] for row in result["connections"])
    assert result["connections"][1]["status"] == "verified"
    assert result["connections"][0]["evidence_ids"] == ["B2"]
