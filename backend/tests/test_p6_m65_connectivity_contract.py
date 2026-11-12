"""P6 M6.5: no invented equipment connectivity from incomplete source evidence."""

from backend.ingestion.balance.models import BalanceReport, Entity, Evidence
from backend.ingestion.engineering_register import build_register


def _evidence(property_name, value, cell, identifier):
    return Evidence(id=identifier, workbook="synthetic.xlsx", sheet="Case A",
                    cell=cell, property=property_name, label=property_name,
                    original_value=value, normalized_value=value, status="verified")


def _report(*values):
    identity = _evidence("identifier", "S-01", "A2", "identity")
    stream = Entity(key="initial", kind="material", identifier="S-01",
                    table="T1", id_evidence=identity, values=list(values))
    return BalanceReport(filename="synthetic.xlsx", sha256="a" * 64,
                         sheets=[{"name": "Case A"}], entities=[stream])


def test_missing_endpoints_do_not_create_physical_equipment():
    report = _report(_evidence("mass_flow", 10, "B2", "flow"))
    build_register(report)
    assert not [entity for entity in report.entities if entity.kind == "equipment"]
    assert len(report.connections) == 2
    assert {edge.role for edge in report.connections} == {"source", "destination"}
    assert all(edge.equipment_key is None and edge.status == "unresolved"
               and edge.basis == "missing" for edge in report.connections)


def test_mention_is_not_verified_physical_connectivity():
    report = _report(_evidence("description", "Stream S-01 mentions P-101", "B2", "description"))
    build_register(report)
    mentions = [edge for edge in report.connections if edge.role == "mention"]
    assert len(mentions) == 1
    assert mentions[0].basis == "mention"
    assert mentions[0].status != "verified"
    assert "description" in mentions[0].evidence_ids
    assert any(edge.role == "source" and edge.equipment_key is None
               for edge in report.connections)
    assert any(edge.role == "destination" and edge.equipment_key is None
               for edge in report.connections)
