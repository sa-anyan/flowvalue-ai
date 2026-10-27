"""Frozen reference checks and trusted single-product bridge contracts."""

from types import SimpleNamespace as NS

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.integrations import biosteam_runner as runner
from app.integrations.libraries import BioSTEAMSnapshot
from app.main import app
from app.validation import references


def test_frozen_reference_cases_pass():
    report = references.reference_report()
    assert report["passed"] is True
    assert report["passed_cases"] == report["total_cases"] == 7
    assert len({c["id"] for c in report["cases"]}) == 7
    assert any("not independent" in n for n in report["limitations"])


def test_reference_checks_report_regression(monkeypatch):
    original = references.calculate_dcf

    def wrong(inputs):
        result = original(inputs)
        return result.model_copy(update={"npv_usd": result.npv_usd + 100})

    monkeypatch.setattr(references, "calculate_dcf", wrong)
    report = references.reference_report()
    assert report["passed"] is False
    assert report["passed_cases"] == 5


def fake_system():
    unit = NS(ID="P101", purchase_cost=1000, installed_cost=3000)
    feed = NS(
        ID="feed",
        F_mass=100,
        T=298.15,
        P=101325,
        phase="l",
        phases=("l",),
        source=None,
        sink=unit,
    )
    product = NS(
        ID="product",
        F_mass=100,
        T=353.15,
        P=300000,
        price=2,
        phase="l",
        phases=("l",),
        source=unit,
        sink=None,
    )
    system = NS(
        ID="test",
        products=(product,),
        units=(unit,),
        streams=(feed, product),
        operating_hours=8000,
        material_cost=16000,
        utility_cost=4000,
    )
    return system, product


def test_bridge_annualization_streams_and_cost_scope(monkeypatch):
    monkeypatch.setattr(runner, "version", lambda name: "test-version")
    system, product = fake_system()
    snapshot = runner.export_system(
        system,
        product,
        fixed_opex_usd_per_year=5000,
        reference_cepci=800,
        provenance="Trusted test",
    )
    assert snapshot["production_units_per_year"] == 800000
    assert snapshot["variable_opex_usd_per_year"] == 20000
    assert snapshot["streams"][0]["destination_unit"] == "P101"
    assert snapshot["streams"][1]["temperature_c"] == 80
    response = TestClient(app).post("/api/integrations/biosteam/import", json=snapshot)
    assert response.status_code == 200, response.text
    project = response.json()
    assert project["financial"]["capacity_factor"] == 1
    assert project["financial"]["plant_capacity_units_per_year"] == 800000
    assert project["streams"] == snapshot["streams"]
    assert project["advisor_context"]["classification"] == "general"
    assessment = TestClient(app).post(
        "/api/assessment", json={k: v for k, v in project.items() if k != "streams"}
    )
    assert assessment.status_code == 200
    assert assessment.json()["bom"]["total_bare_module_cost_usd"] == 3000
    assert assessment.json()["financial"]["cash_flows"][1]["opex_usd"] == 25000


@pytest.mark.parametrize("change", ["coproduct", "utility_credit", "hours"])
def test_bridge_rejects_unsupported_financial_bases(monkeypatch, change):
    monkeypatch.setattr(runner, "version", lambda name: "test-version")
    system, product = fake_system()
    if change == "coproduct":
        system.products = (product, NS())
    if change == "utility_credit":
        system.utility_cost = -1
    if change == "hours":
        system.operating_hours = 9000
    with pytest.raises(ValueError):
        runner.export_system(
            system,
            product,
            fixed_opex_usd_per_year=5000,
            reference_cepci=800,
            provenance="test",
        )


def test_snapshot_rejects_duplicate_units_and_double_counted_opex(monkeypatch):
    monkeypatch.setattr(runner, "version", lambda name: "test-version")
    system, product = fake_system()
    snapshot = runner.export_system(
        system,
        product,
        fixed_opex_usd_per_year=5000,
        reference_cepci=800,
        provenance="test",
    )
    with pytest.raises(ValidationError):
        BioSTEAMSnapshot.model_validate(
            snapshot | {"equipment": snapshot["equipment"] * 2}
        )
    with pytest.raises(ValidationError):
        BioSTEAMSnapshot.model_validate(snapshot | {"variable_opex_usd_per_year": 1})


def test_runner_inputs_are_numeric_bounded_and_never_code():
    with pytest.raises(ValidationError):
        runner.WaterHeatingInputs.model_validate({"mass_flow_kg_h": -1})
    with pytest.raises(ValidationError):
        runner.WaterHeatingInputs.model_validate({"python": "print('untrusted')"})


def test_reference_endpoint_protected_in_cloud(monkeypatch):
    monkeypatch.setenv("REQUIRE_AUTH", "true")
    assert TestClient(app).get("/api/engineering/validation").status_code == 401


def test_actual_biosteam_example_transfers_into_independent_annuity_check():
    import json
    from pathlib import Path
    example=json.loads((Path(__file__).parents[1]/"examples/water-heating-biosteam.json").read_text())
    imported=TestClient(app).post("/api/integrations/biosteam/import",json=example)
    assert imported.status_code==200
    project=imported.json()
    evaluated=TestClient(app).post("/api/assessment",json={k:v for k,v in project.items() if k!="streams"})
    assert evaluated.status_code==200
    data=evaluated.json()
    capital=sum(u["installed_cost_usd"] for u in example["equipment"])
    opex=example["fixed_opex_usd_per_year"]+example["variable_opex_usd_per_year"]
    revenue=example["production_units_per_year"]*example["selling_price_usd_per_unit"]
    tax=max(0,revenue-opex-capital/20)*.21
    annuity=(1-1.1**-20)/.1
    assert data["bom"]["total_bare_module_cost_usd"]==pytest.approx(capital)
    assert data["financial"]["npv_usd"]==pytest.approx(-capital+(revenue-opex-tax)*annuity)
    assert data["financial"]["lcop_usd_per_unit"]==pytest.approx((capital+opex*annuity)/(example["production_units_per_year"]*annuity))
    assert len(project["streams"])==3
    assert all(s["mass_flow_kg_h"]==10000 for s in project["streams"])
    assert example["library_version"]=="2.54.0"
