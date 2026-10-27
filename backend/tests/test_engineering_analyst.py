"""Independent unit-investigation, review and research boundaries; no paid calls."""

import asyncio
from datetime import date
from io import BytesIO
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook
from pydantic import ValidationError

from app.agent.copilot_research import ResearchSettings
from app.agent.engineering_research import research_unit
from app.engineering.investigation import investigate
from app.engineering.models import EngineeringCase, UnitService
from app.engineering.review import filter_value, open_challenges
from app.main import AssessmentRequest, app, demo_assessment
from app.study.models import Evidence, Study, ledger_digest

client = TestClient(app)


def project():
    p = demo_assessment()
    existing = p.costing.equipment[0]
    p.study = Study(
        evidence=[
            Evidence(
                evidence_id="DESIGN",
                title="Independent synthetic design fixture",
                kind="design_input",
                reference="Software test, not an actual industrial validation",
                observed_on=date.today(),
                reviewer="Synthetic reviewer",
            )
        ],
        engineering_cases=[
            EngineeringCase(
                unit_id=existing.unit_id,
                unit_kind="heat_exchanger",
                proposed_equipment=existing.model_dump(exclude_none=True),
                evidence_ids=["DESIGN"],
                hypothesis="Check A = Q / (U times LMTD) against an independent 100 m2 result",
                service=UnitService(
                    duty_description="Synthetic sensible heating duty",
                    fluid_composition="Illustrative water service",
                    concentration_basis="Synthetic pure fluid assumption",
                    phase="liquid",
                    normal_temperature_c=25,
                    design_temperature_c=80,
                    design_pressure_barg=existing.design_pressure_barg,
                    food_contact=False,
                    corrosion_conditions="Actual water chemistry would need investigation; fixture only",
                    wetted_material="carbon_steel",
                    shell_material="carbon_steel",
                    material_rationale="Synthetic material decision to test the workflow; no industrial suitability claim",
                    compatibility_reviewed=True,
                    mechanical_scope_reviewed=True,
                ),
            )
        ],
    )
    return p


def body(p=None):
    p = p or project()
    return {
        "project": p.model_dump(mode="json"),
        "unit_id": p.study.engineering_cases[0].unit_id,
    }


def test_supported_sizing_has_independent_area_and_no_automatic_material_claim():
    p = project()
    r = investigate(p, p.study.engineering_cases[0].unit_id)
    assert r["can_apply_baseline"], r["blockers"]
    assert r["sizing"]["sizing"]["area_m2"] == pytest.approx(1000 * 1000 / (500 * 20))
    assert r["baseline_status"] == "not_reviewed"
    assert any(
        "Neither grade guarantees sterility" in o["role"] for o in r["material_options"]
    )
    assert len(r["sources"]) == 2


@pytest.mark.parametrize(
    "change,match",
    [
        ({"food_contact": None}, "food contact"),
        ({"design_pressure_barg": None}, "design pressure"),
        ({"fluid_composition": ""}, "fluid composition"),
        ({"compatibility_reviewed": False}, "compatibility"),
        ({"mechanical_scope_reviewed": False}, "mechanical"),
        ({"food_contact": True, "cleaning_regime": ""}, "cleaning"),
        ({"wetted_material": "ss316l", "shell_material": "carbon_steel"}, "Composite"),
        ({"design_pressure_barg": 10}, "differs"),
    ],
)
def test_missing_conditions_food_and_composite_materials_block_baseline(change, match):
    p = project()
    case = p.study.engineering_cases[0]
    case.service = UnitService.model_validate(case.service.model_dump() | change)
    r = investigate(p, case.unit_id)
    assert not r["can_apply_baseline"]
    assert any(match.lower() in b.lower() for b in r["blockers"])


def test_valve_and_composite_require_assembled_quote_and_evidence():
    p = project()
    c = p.study.engineering_cases[0]
    c.unit_kind = "valve"
    c.proposed_equipment = {}
    r = investigate(p, c.unit_id)
    assert r["sizing"] is None and not r["can_apply_baseline"]
    assert any("No validated valve" in q for q in r["questions"])
    c.service.wetted_material = "ss316l"
    c.service.shell_material = "carbon_steel"
    c.service.lining_or_cladding = "Synthetic clad assembly, not a real design"
    c.proposed_equipment = {
        "kind": "quoted",
        "purchased_cost_usd": 1000.0,
        "installed_cost_usd": 2000.0,
        "reference_cepci": 800.0,
        "source": "Synthetic assembled quote for workflow test",
    }
    assert any("quotation record" in b for b in investigate(p, c.unit_id)["blockers"])
    p.study.evidence[0].kind = "quotation"
    assert investigate(p, c.unit_id)["can_apply_baseline"]


def test_evidence_assumption_and_undated_records_do_not_establish_review():
    p = project()
    p.study.evidence[0].kind = "assumption"
    assert not investigate(p, p.study.engineering_cases[0].unit_id)[
        "can_apply_baseline"
    ]
    p.study.evidence[0].kind = "design_input"
    p.study.evidence[0].observed_on = None
    assert any(
        "observation date" in b
        for b in investigate(p, p.study.engineering_cases[0].unit_id)["blockers"]
    )
    with pytest.raises(ValidationError):
        Study(
            engineering_cases=[EngineeringCase(unit_id="X", evidence_ids=["missing"])]
        )
    with pytest.raises(ValidationError):
        UnitService(normal_temperature_c=100, design_temperature_c=50)
    with pytest.raises(ValidationError):
        EngineeringCase(unit_id="X", proposed_equipment={"duty_kw": float("nan")})


def test_baseline_roundtrip_and_staleness_on_service_sizing_and_evidence():
    p = project()
    request = body(p) | {
        "reviewer": "Synthetic engineer",
        "basis": "Independent arithmetic and workflow fixture; excludes actual industrial validation",
        "confirm": True,
    }
    response = client.post("/api/engineering/apply-baseline", json=request)
    assert response.status_code == 200, response.text
    out = AssessmentRequest.model_validate(response.json())
    uid = out.study.engineering_cases[0].unit_id
    assert investigate(out, uid)["baseline_status"] == "current_user_review"
    roundtrip = AssessmentRequest.model_validate_json(out.model_dump_json())
    assert investigate(roundtrip, uid)["baseline_status"] == "current_user_review"
    roundtrip.study.engineering_cases[
        0
    ].service.cleaning_regime = "New cleaning conditions"
    assert investigate(roundtrip, uid)["baseline_status"] == "stale_review"
    next(e for e in out.costing.equipment if e.unit_id == uid).quantity = 2
    assert investigate(out, uid)["baseline_status"] == "stale_review"
    assert len(out.study.engineering_cases[0].baseline_history) == 1
    excel = client.post("/api/export/excel", json=out.model_dump(mode="json"))
    w = load_workbook(BytesIO(excel.content))
    notes = "\n".join(str(c.value) for row in w["Notes"] for c in row)
    assert "stale_review" in notes
    assert "NPV(" in w["Summary"]["C6"].value


def test_baseline_requires_confirmation_and_blocks_incomplete_unit():
    b = body() | {"reviewer": "R", "basis": "B", "confirm": False}
    assert client.post("/api/engineering/apply-baseline", json=b).status_code == 422
    b["confirm"] = True
    b["project"]["study"]["engineering_cases"][0]["service"][
        "compatibility_reviewed"
    ] = False
    assert client.post("/api/engineering/apply-baseline", json=b).status_code == 422


def test_engineering_inputs_invalidate_opex_snapshot_but_legacy_empty_case_does_not():
    s = Study()
    before = ledger_digest(s)
    assert ledger_digest(Study.model_validate_json(s.model_dump_json())) == before
    s.engineering_cases = [EngineeringCase(unit_id="R1")]
    assert ledger_digest(s) != before


def test_review_resolution_and_filter_escaping():
    events = [
        {"id": "a", "action": "challenge", "parent_id": None},
        {"id": "b", "action": "challenge", "parent_id": None},
        {"id": "c", "action": "resolve", "parent_id": "a"},
    ]
    assert [e["id"] for e in open_challenges(events)] == ["b"]
    encoded = filter_value('R&action=eq.resolve,"X')
    from urllib.parse import parse_qs

    assert "&" not in encoded
    assert parse_qs("unit_id=eq." + encoded) == {
        "unit_id": ['eq.R&action=eq.resolve,"X']
    }
    assert filter_value("E1") == "E1"


def test_unit_research_is_bounded_cited_and_never_changes_project():
    p = project()
    before = p.model_dump_json()
    report = investigate(p, p.study.engineering_cases[0].unit_id)
    captured = {}

    class FakeResponses:
        async def create(self, **kw):
            captured.update(kw)
            return SimpleNamespace(
                status="completed",
                output_text="Synthetic sourced draft",
                output=[
                    SimpleNamespace(type="web_search_call", status="completed"),
                    SimpleNamespace(
                        type="message",
                        content=[
                            SimpleNamespace(
                                annotations=[
                                    SimpleNamespace(
                                        type="url_citation",
                                        url="https://www.outokumpu.com/en/products/corrosion-tables",
                                        title="Manufacturer",
                                        start_index=0,
                                        end_index=10,
                                    )
                                ]
                            )
                        ],
                    ),
                ],
            )

    result = asyncio.run(
        research_unit(
            report,
            {
                "description": "Fixture",
                "OPENAI_API_KEY": "MUST_NOT_FORWARD",
                "source_context": "MUST_NOT_FORWARD",
            },
            ResearchSettings(),
            client=SimpleNamespace(responses=FakeResponses()),
        )
    )
    assert result["evidence_status"] == "sourced_draft"
    assert (
        captured["store"] is False
        and captured["max_tool_calls"] == 2
        and captured["max_output_tokens"] == 2500
    )
    assert "MUST_NOT_FORWARD" not in captured["input"]
    assert "outokumpu.com" in captured["tools"][0]["filters"]["allowed_domains"]
    assert p.model_dump_json() == before


def test_incomplete_or_uncited_research_cannot_be_called_sourced():
    p = project()
    report = investigate(p, p.study.engineering_cases[0].unit_id)

    class FakeResponses:
        async def create(self, **kw):
            return SimpleNamespace(
                status="incomplete", output_text="partial", output=[]
            )

    r = asyncio.run(
        research_unit(
            report,
            {},
            ResearchSettings(),
            client=SimpleNamespace(responses=FakeResponses()),
        )
    )
    assert r["evidence_status"] == "insufficient_evidence" and not r["complete"]


def test_new_engineering_endpoints_protected(monkeypatch):
    monkeypatch.setenv("REQUIRE_AUTH", "true")
    for route in ("investigate", "research", "apply-baseline"):
        assert client.post(f"/api/engineering/{route}", json={}).status_code == 401
    assert client.get("/api/engineering/reviews/identity").status_code == 401
