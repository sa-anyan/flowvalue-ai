"""M6.5 synthetic connectivity: no invented physical piping."""

from backend.ingestion.connection_proposals import proposed_links


def report(connections):
    return {
        "entities": [
            {"key": "s", "kind": "material"},
            {"key": "p1", "kind": "equipment"},
            {"key": "p2", "kind": "equipment"},
            {"key": "p3", "kind": "equipment"},
        ],
        "connections": connections,
    }


def edge(role, key, status="inferred", basis="explicit_field", evidence="B2"):
    return {
        "stream_key": "s", "equipment_key": key, "role": role,
        "status": status, "basis": basis, "evidence_ids": [evidence],
    }


def test_unique_source_and_destination_are_unverified_proposals():
    result = proposed_links(report([edge("source", "p1"), edge("destination", "p2")]))
    assert len(result) == 1
    assert result[0]["status"] == "proposed_unverified"
    assert result[0]["physical_connection_verified"] is False
    assert result[0]["evidence_ids"] == ["B2"]


def test_mentions_do_not_create_directed_links():
    assert proposed_links(report([edge("mention", "p1"), edge("destination", "p2")])) == []


def test_conflicting_candidates_do_not_create_pipes():
    edges = [edge("source", "p1"), edge("source", "p3"),
             edge("destination", "p2")]
    assert proposed_links(report(edges)) == []


def test_unresolved_alternative_blocks_unique_looking_pair():
    edges = [edge("source", "p1"), edge("source", "p3", "unresolved"),
             edge("destination", "p2")]
    assert proposed_links(report(edges)) == []


def test_missing_endpoint_and_self_link_are_not_drawn():
    assert proposed_links(report([edge("source", "p1")])) == []
    assert proposed_links(report([edge("source", "p1"), edge("destination", "p1")])) == []


def test_ambiguous_equipment_identity_is_not_substituted_by_display_tag():
    assert proposed_links(report([edge("source", "P-1"), edge("destination", "p2")])) == []
