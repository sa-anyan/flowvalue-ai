"""Independent arithmetic and workflow tests; no inspiration workbook inputs."""

from datetime import date, timedelta
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook
from pydantic import ValidationError
from pypdf import PdfReader

from app.main import AssessmentRequest, SavedProject, app, demo_assessment
from app.study.models import (
    CostItem,
    DesignBasis,
    Evidence,
    Study,
    ledger_digest,
    review_study,
)

client = TestClient(app)


def item(id="LAB", **changes):
    return CostItem(
        **(
            {
                "item_id": id,
                "description": "Independent synthetic cost",
                "cost_type": "fixed_opex",
                "status": "included",
                "quantity": 2,
                "rate_usd": 100,
                "allocation_fraction": 0.5,
                "basis": "Synthetic arithmetic test",
            }
            | changes
        )
    )


def study(**changes):
    payload = {"cost_items": [item()]} | changes
    rows = list(payload["cost_items"])
    for kind in ("fixed_opex", "feedstock", "utilities", "other_variable"):
        if not any(i.cost_type == kind for i in rows):
            rows.append(
                item(
                    f"NA-{kind}",
                    cost_type=kind,
                    status="not_applicable",
                    quantity=None,
                    rate_usd=None,
                    basis="Explicitly outside this synthetic arithmetic fixture",
                )
            )
    payload["cost_items"] = rows
    return Study(**payload)


def test_annual_ledger_arithmetic_and_components_are_disjoint():
    s = study(
        cost_items=[
            item(),
            item(
                "FEED",
                cost_type="feedstock",
                quantity=10,
                rate_usd=3,
                allocation_fraction=1,
            ),
            item(
                "POWER",
                cost_type="utilities",
                quantity=5,
                rate_usd=2,
                allocation_fraction=1,
            ),
            item(
                "OTHER",
                cost_type="other_variable",
                quantity=4,
                rate_usd=5,
                allocation_fraction=1,
            ),
            item(
                "CAP",
                cost_type="capex",
                quantity=2,
                rate_usd=500,
                allocation_fraction=1,
            ),
        ]
    )
    r = review_study(s)
    assert r["totals_usd"] == {
        "fixed_opex": 100,
        "feedstock": 30,
        "utilities": 10,
        "other_variable": 20,
        "capex": 1000,
    }
    assert r["can_apply_opex"]
    assert any("planning-only" in w for w in r["warnings"])
    p = demo_assessment().model_dump(mode="json") | {"study": s.model_dump(mode="json")}
    applied = client.post(
        "/api/study/apply-opex",
        json={"project": p, "reviewer": "Synthetic reviewer", "confirm_replace": True},
    )
    assert applied.status_code == 200, applied.text
    out = applied.json()
    assert out["financial"]["variable_opex_usd_per_year"] == 60
    assert out["financial"]["fixed_opex_usd_per_year"] == 100
    assert out["advisor_context"]["raw_materials"] == []
    old = client.post("/api/assessment", json=p).json()
    new = client.post("/api/assessment", json=out).json()
    assert (
        old["bom"]["total_bare_module_cost_usd"]
        == new["bom"]["total_bare_module_cost_usd"]
    )
    assert new["financial"]["cash_flows"][1]["opex_usd"] == 160
    assert review_study(Study.model_validate(out["study"]))["application_current"]
    assert (
        client.post(
            "/api/study/apply-opex",
            json={
                "project": out,
                "reviewer": "Synthetic reviewer",
                "confirm_replace": True,
            },
        ).json()["financial"]
        == out["financial"]
    )  # replacement, not addition


@pytest.mark.parametrize(
    "change",
    [
        {"quantity": None},
        {"rate_usd": None},
        {"basis": ""},
        {"status": "missing"},
        {"status": "unsupported"},
        {"cost_arrangement": "charged_elsewhere"},
    ],
)
def test_unresolved_or_duplicate_costs_block_application(change):
    s = study(cost_items=[item(**change)])
    assert not review_study(s)["can_apply_opex"]
    p = demo_assessment().model_dump(mode="json") | {"study": s.model_dump(mode="json")}
    assert (
        client.post(
            "/api/study/apply-opex",
            json={"project": p, "reviewer": "R", "confirm_replace": True},
        ).status_code
        == 422
    )


def test_zero_exclusions_and_not_applicable_differ_from_missing():
    zero = review_study(study(cost_items=[item(quantity=0)]))
    assert zero["can_apply_opex"] and zero["rows"][0]["amount_usd"] == 0
    for status in ("excluded", "not_applicable"):
        r = review_study(
            study(cost_items=[item(status=status, quantity=None, rate_usd=None)])
        )
        assert r["can_apply_opex"] and not r["rows"][0]["counted"]
    assert not review_study(Study())["can_apply_opex"]


def test_links_duplicates_dates_and_nonfinite_values_rejected():
    with pytest.raises(ValidationError):
        study(cost_items=[item(), item()])
    with pytest.raises(ValidationError):
        study(cost_items=[item(evidence_ids=["unknown"])])
    e = Evidence(evidence_id="EV", title="Synthetic source")
    with pytest.raises(ValidationError):
        study(evidence=[e, e])
    with pytest.raises(ValidationError):
        Evidence(
            evidence_id="E",
            title="Future",
            observed_on=date.today() + timedelta(days=1),
        )
    with pytest.raises(ValidationError):
        Evidence(evidence_id="E", title="Unsafe", source_url="javascript:alert(1)")
    with pytest.raises(ValidationError):
        item(rate_usd=float("nan"))
    with pytest.raises(ValidationError):
        item(allocation_fraction=1.1)


def test_design_context_questions_and_digest_change_on_evidence_or_context():
    s = study(design_basis=DesignBasis(description="Food fermentation"))
    r = review_study(s)
    assert any("hygiene" in q for q in r["questions"])
    digest = ledger_digest(s)
    s.design_basis.requirements = "Synthetic documented cleaning requirements"
    assert ledger_digest(s) != digest
    digest = ledger_digest(s)
    s.evidence.append(Evidence(evidence_id="E", title="New source"))
    assert ledger_digest(s) != digest


def test_stale_application_and_scope_survive_project_and_exports():
    p = demo_assessment().model_dump(mode="json") | {
        "study": study().model_dump(mode="json")
    }
    out = client.post(
        "/api/study/apply-opex",
        json={"project": p, "reviewer": "Synthetic reviewer", "confirm_replace": True},
    ).json()
    out["study"]["cost_items"][0]["rate_usd"] = 300
    assert not review_study(Study.model_validate(out["study"]))["application_current"]
    assert out["financial"]["fixed_opex_usd_per_year"] == 100
    saved = SavedProject(
        name="Synthetic", project=AssessmentRequest.model_validate(out)
    )
    restored = AssessmentRequest.model_validate(saved.project.model_dump(mode="json"))
    assert restored.study.cost_items[0].rate_usd == 300
    assessed = client.post("/api/assessment", json=out).json()
    assert any("STALE" in w for w in assessed["financial"]["warnings"])
    excel = client.post("/api/export/excel", json=out)
    w = load_workbook(BytesIO(excel.content))
    notes = "\n".join(str(c.value) for row in w["Notes"] for c in row)
    assert "STALE" in notes and "Synthetic reviewer" in notes
    assert "NPV(" in w["Summary"]["C6"].value
    pdf = client.post("/api/export/pdf", json=out)
    assert len(PdfReader(BytesIO(pdf.content)).pages) == 2


def test_apply_requires_explicit_replacement_and_named_reviewer():
    p = demo_assessment().model_dump(mode="json") | {
        "study": study().model_dump(mode="json")
    }
    for change in ({"confirm_replace": False}, {"reviewer": " "}):
        assert (
            client.post(
                "/api/study/apply-opex",
                json={"project": p, "reviewer": "R", "confirm_replace": True} | change,
            ).status_code
            == 422
        )


def test_new_study_endpoints_protected(monkeypatch):
    monkeypatch.setenv("REQUIRE_AUTH", "true")
    for path in ("/api/study/review", "/api/study/apply-opex"):
        assert client.post(path, json={}).status_code == 401


def test_assessment_returns_normalized_study_for_json_imports():
    p = demo_assessment().model_dump(mode="json") | {
        "study": {"design_basis": {"description": "Synthetic source"}}
    }
    r = client.post("/api/assessment", json=p)
    assert r.status_code == 200
    assert r.json()["study"]["schema_version"] == "flowvalue-study-v1"
    assert r.json()["study"]["evidence"] == []


def test_absent_opex_classes_cannot_be_silently_replaced_with_zero():
    review = review_study(Study(cost_items=[item()]))
    assert not review["can_apply_opex"]
    assert any(
        "feedstock" in b and "absence is not zero" in b
        for b in review["opex_application_blockers"]
    )
