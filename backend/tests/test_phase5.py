"""Boundary, rights and end-to-end deterministic release regression checks."""

from datetime import date, timedelta
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook
from pydantic import ValidationError
from pypdf import PdfReader

from app.engine.indices import IndexRecord, index_catalog
from app.financial.dcf_model import ProductionIncentive
from app.main import app, demo_assessment
from app.policy.screening import PolicyEvidence, screen_policy

client = TestClient(app)


def evidence(**changes):
    return PolicyEvidence(
        **(
            {
                "profile": "us_45v",
                "jurisdiction": "US",
                "product": "hydrogen_kg",
                "construction_start": "2027-12-31",
                "placed_in_service": "2028-01-01",
                "emissions_kg_co2e_per_kg_h2": 4,
                "independent_verification": True,
                "owner_trade_sale_use": True,
                "no_conflicting_credit": True,
                "electricity_and_emissions_rules_reviewed": True,
                "wage_apprenticeship_reviewed": True,
                "monetization_reviewed": True,
                "reviewer": "Synthetic reviewer",
                "reviewed_on": date.today(),
                "source_urls": ["https://www.irs.gov/forms-pubs/about-form-7210"],
                "evidence_reference": "Synthetic regression case, not an eligibility claim",
            }
            | changes
        )
    )


def test_screen_unknown_and_45v_boundary_dates_emissions():
    assert screen_policy(PolicyEvidence(profile="us_45v"))["status"] == "needs_evidence"
    assert screen_policy(evidence())["can_enable"]
    for change in [
        {"construction_start": "2028-01-01"},
        {"placed_in_service": "2022-12-31"},
        {"emissions_kg_co2e_per_kg_h2": 4.00001},
        {"no_conflicting_credit": False},
        {"product": "other"},
        {"reviewed_on": date.today() + timedelta(days=1)},
        {"reviewed_on": date.today() - timedelta(days=91)},
        {"electricity_and_emissions_rules_reviewed": None},
    ]:
        assert not screen_policy(evidence(**change))["can_enable"]
    assert not screen_policy(evidence(), today=date(2027, 2, 1))["can_enable"]


def test_server_prevents_enabled_incomplete_or_overlong_screened_credit():
    kwargs = {
        "enabled": True,
        "eligibility_confirmed": True,
        "basis": "Synthetic basis",
    }
    with pytest.raises(ValidationError):
        ProductionIncentive(**kwargs, evidence=PolicyEvidence(profile="us_45v"))
    with pytest.raises(ValidationError):
        ProductionIncentive(**kwargs, evidence=evidence(), duration_years=11)
    with pytest.raises(ValidationError):
        ProductionIncentive(**kwargs, evidence=evidence(), start_year=3, duration_years=9)
    assert ProductionIncentive(**kwargs, evidence=evidence()).enabled
    assert ProductionIncentive(**kwargs).evidence is None  # legacy custom scenario
    with pytest.raises(ValidationError):
        PolicyEvidence(source_urls=["javascript:alert(1)"])


def test_index_rights_and_future_month_validation(monkeypatch):
    record = index_catalog()["records"][0]
    assert index_catalog()["license_holder"]["status"] == "not_connected"
    with pytest.raises(ValidationError):
        IndexRecord.model_validate(record | {"status": "verified"})
    with pytest.raises(ValidationError):
        IndexRecord.model_validate(record | {"period": f"{date.today().year}-12"})
    licensed = record | {
        "status": "verified",
        "publication_date": date.today().isoformat(),
        "license_reference": "Synthetic redistribution agreement",
        "distribution_rights": "redistribution_authorized",
        "rights_reviewed_on": date.today().isoformat(),
        "rights_expires_on": (date.today() + timedelta(days=10)).isoformat(),
    }
    assert IndexRecord.model_validate(licensed).status == "verified"

    class FakeFile:
        def joinpath(self, _):
            return self

        def read_text(self):
            import json

            return json.dumps(
                [
                    record,
                    licensed | {"distribution_rights": "internal_only"},
                    licensed | {"rights_expires_on": "2020-01-01"},
                ]
            )

    monkeypatch.setattr("app.engine.indices.files", lambda _: FakeFile())
    assert len(index_catalog()["records"]) == 1


def test_phase5_assessment_exports_preserve_evidence_and_live_formulas():
    payload = demo_assessment().model_dump(mode="json")
    payload["costing"]["settings"]["cepci_basis"] = (
        "Synthetic dated source and rights reference"
    )
    payload["financial"]["incentive"] = ProductionIncentive(
        enabled=True,
        eligibility_confirmed=True,
        basis="Synthetic case",
        evidence=evidence(),
        rate_usd_per_unit=0.2,
    ).model_dump(mode="json")
    r = client.post("/api/assessment", json=payload)
    assert r.status_code == 200
    assert r.json()["financial"]["cash_flows"][1]["credit_generated_usd"] > 0
    assert client.post(
        "/api/policy/screen", json=payload["financial"]["incentive"]["evidence"]
    ).json()["can_enable"]
    workbook = load_workbook(
        BytesIO(client.post("/api/export/excel", json=payload).content)
    )
    text = "\n".join(str(c.value) for row in workbook["Notes"] for c in row)
    assert (
        "Synthetic dated source" in text
        and "Synthetic reviewer" in text
        and "45v-screen-2026-10-27" in text
    )
    assert "NPV(" in workbook["Summary"]["C6"].value
    pdf = PdfReader(BytesIO(client.post("/api/export/pdf", json=payload).content))
    assert len(pdf.pages) == 2
    payload["financial"]["incentive"]["evidence"]["product"] = "other"
    for path in ("/api/assessment", "/api/export/excel", "/api/export/pdf"):
        assert client.post(path, json=payload).status_code == 422


def test_release_checks_generate_artifacts_without_provider_call():
    response = client.post(
        "/api/release/check", json=demo_assessment().model_dump(mode="json")
    )
    assert response.status_code == 200, response.text
    checks = {c["label"]: c for c in response.json()["checks"]}
    assert checks["Engineering references"]["status"] == "pass"
    assert checks["Excel and PDF generation"]["status"] == "pass"
    assert checks["Account save/reload"]["status"] == "manual"


def test_new_endpoints_require_auth(monkeypatch):
    monkeypatch.setenv("REQUIRE_AUTH", "true")
    assert client.post("/api/policy/screen", json={}).status_code == 401
    assert client.post("/api/release/check", json={}).status_code == 401
