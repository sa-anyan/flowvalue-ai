import asyncio
import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from test_equipment_catalog import report

from app.agent.copilot_research import ResearchSettings
from app.agent.equipment_interpretation import (
    InterpretationDraft,
    InterpretationRequest,
    interpret_equipment,
    interpretation_input,
)
from app.main import app


def request():
    return InterpretationRequest(
        report=report("Bioreactor R-001", "R-001"), equipment_key="unit"
    )


def draft(**changes):
    return InterpretationDraft.model_validate(
        {
            "interpreted_identity": "Bioreactor; possible agitated vessel basis",
            "observations": [{"evidence_id": "e2"}],
            "candidates": [
                {
                    "catalog_id": "garrett-a1-258",
                    "rationale": "Agitated vessel is a hypothesis, not a complete biological process assembly.",
                    "differences": ["Investigate aeration, hygiene and heat removal."],
                    "missing_inputs": ["Working volume and service requirements."],
                }
            ],
            "engineering_hypotheses": [
                "A complete assembly may need a vendor quotation."
            ],
            "clarification_questions": ["Is agitation required?"],
            "uncertainty_drivers": [
                "Cost method scope and unsupported sterile-service additions."
            ],
            **changes,
        }
    )


class Provider:
    def __init__(self, output=None, status="completed"):
        self.responses = self
        self.output = output if output is not None else draft()
        self.status = status
        self.calls = []

    async def parse(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(status=self.status, output_parsed=self.output)


def run(body=None, provider=None):
    return asyncio.run(
        interpret_equipment(
            body or request(),
            ResearchSettings(openai_api_key=SecretStr("test-secret")),
            provider or Provider(),
        )
    )


def test_grounded_provisional_basis_and_modifications_without_mutation():
    body = request()
    before = body.report.model_dump_json()
    provider = Provider()
    result = run(body, provider)
    assert result["status"] == "draft_requires_review"
    assert result["costing_ready"] is False
    assert result["candidate_sources"][0]["name"] == "Agitated tanks"
    assert len(result["candidate_sources"][0]["source_refs"]) == 2
    assert result["observation_sources"][0]["cell"] == "B2"
    assert body.report.model_dump_json() == before
    call = provider.calls[0]
    assert len(provider.calls) == 1
    assert call["store"] is False
    assert "tools" not in call
    assert call["max_output_tokens"] == 2600
    assert "test-secret" not in json.dumps(json.loads(call["input"]))


@pytest.mark.parametrize(
    "change",
    [
        {"observations": [{"evidence_id": "invented"}]},
        {"observations": [{"evidence_id": "not-provided"}]},
        {"observations": []},
        {"engineering_hypotheses": ["Use a 20% cost allowance."]},
    ],
)
def test_reject_untraced_evidence_and_invented_numeric_estimates(change):
    with pytest.raises(ValueError):
        run(provider=Provider(draft(**change)))


def test_unknown_catalog_and_duplicate_candidates_rejected():
    value = draft()
    value.candidates[0].catalog_id = "fabricated-method"
    with pytest.raises(ValueError):
        run(provider=Provider(value))
    value = draft()
    value.candidates.append(value.candidates[0])
    with pytest.raises(ValueError):
        run(provider=Provider(value))


def test_refusal_truncation_and_wrong_unit_fail_closed():
    with pytest.raises(ValueError):
        run(provider=Provider(status="incomplete"))
    body = request()
    body.equipment_key = "not-in-report"
    p = Provider()
    with pytest.raises(ValueError):
        run(body, p)
    assert not p.calls


def test_input_fingerprint_changes_and_other_units_not_sent():
    body = request()
    _, a, _ = interpretation_input(body)
    body.process_description = "Food process user assertion."
    payload, b, _ = interpretation_input(body)
    assert a != b
    assert payload["user_process_description"] == body.process_description
    other = body.report.entities[0].model_copy(deep=True)
    other.key, other.identifier = "other-unit", "SENSITIVE-OTHER"
    other.id_evidence.sheet = "Unrelated scope"
    body.report.entities.append(other)
    payload, _, _ = interpretation_input(body)
    assert "SENSITIVE-OTHER" not in json.dumps(payload)


def test_api_disabled_auth_and_body_limits(monkeypatch):
    monkeypatch.setenv("AI_ENABLED", "false")
    monkeypatch.setenv("REQUIRE_AUTH", "false")
    client = TestClient(app)
    assert (
        client.post("/api/equipment/interpret", json=request().model_dump()).status_code
        == 503
    )
    assert (
        client.post(
            "/api/equipment/interpret", content=b"x" * (3 * 1024 * 1024 + 1)
        ).status_code
        == 413
    )
    monkeypatch.setenv("REQUIRE_AUTH", "true")
    assert (
        client.post("/api/equipment/interpret", json=request().model_dump()).status_code
        == 401
    )


def test_team8_ph_stage_receives_process_context_without_inventing_edges():
    from pathlib import Path

    from app.parsers.workbook_pipeline import parse_workbook

    path = Path(__file__).parent / "fixtures/parser_v3/team8-reference.xlsm"
    parsed = parse_workbook(path.read_bytes(), path.name)
    unit = next(
        e for e in parsed.entities if e.kind == "equipment" and e.identifier == "P-001"
    )
    body = InterpretationRequest(report=parsed, equipment_key=unit.key)
    before = parsed.model_dump_json()
    payload, digest, evidence = interpretation_input(body)
    text = json.dumps(payload)
    assert "Sulfuric Acid" in text
    assert "pH Adjusted Wastewater to Bioreactor" in text
    assert any(e.component for e in evidence.values())
    assert all(e.sheet == "Mass and Energy Balance" for e in evidence.values())
    context = payload["process_context"]
    original_keys = {c.key for c in parsed.connections}
    assert all(c["key"] in original_keys for c in context["relationships"])
    assert any(
        c["role"] == "destination" and c["status"] == "inferred"
        for c in context["relationships"]
    )
    assert not any(
        c["equipment_key"] != unit.key
        and c["stream_key"] not in context["linked_stream_keys"]
        for c in context["relationships"]
    )
    assert parsed.model_dump_json() == before
    # A same-scope downstream description edit invalidates the interpretation.
    stream = next(
        e
        for e in parsed.entities
        if e.kind == "material"
        and any("pH Adjusted" in str(v.original_value) for v in e.values)
    )
    next(
        v for v in stream.values if v.property == "description"
    ).original_value = "Changed process duty"
    assert interpretation_input(body)[1] != digest


def test_shared_tag_other_case_and_scope_are_excluded():
    body = request()
    other = body.report.entities[0].model_copy(deep=True)
    other.key = "other-case"
    other.case = "different operating case"
    other.values[0].original_value = "SECRET OTHER CASE"
    body.report.entities.append(other)
    payload, _, _ = interpretation_input(body)
    assert "SECRET OTHER CASE" not in json.dumps(payload)


def test_equivalent_cell_evidence_is_accepted_but_neighbor_only_proposal_is_not():
    from app.agent.equipment_interpretation import validate_draft

    body = request()
    stream = body.report.entities[0].model_copy(deep=True)
    stream.kind, stream.key, stream.identifier = "material", "stream", "1"
    stream.values[0].id = "same-cell-stream-description"
    body.report.entities.append(stream)
    payload, _, evidence = interpretation_input(body)
    alias_ref = next(
        ref
        for ref, value in evidence.items()
        if value.id == "same-cell-stream-description"
    )
    value = draft(observations=[{"evidence_id": alias_ref}])
    validate_draft(value, payload, evidence)
    # Same wording on a genuinely different cell is context, not selected-unit evidence.
    stream.values[0].cell = "Z99"
    stream.id_evidence.cell = "Z98"
    payload, _, evidence = interpretation_input(body)
    with pytest.raises(ValueError, match="selected equipment"):
        validate_draft(value, payload, evidence)
