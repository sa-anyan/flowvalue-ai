import json
from types import SimpleNamespace as NS

import pytest
from fastapi.testclient import TestClient

from app.agent.copilot_research import (
    ResearchRequest,
    ResearchSettings,
    research_events,
)
from app.agent.universal_advisor import UniversalProcessAdvisor
from app.main import app, assessment, demo_assessment


def project(**changes):
    values = {
        "total_capex_usd": 1000,
        "fixed_opex_usd_per_year": 100,
        "variable_opex_usd_per_year": 400,
        "feedstock_opex_usd_per_year": 100,
        "utility_opex_usd_per_year": 250,
        "operating_years": 10,
        "discount_rate": 0,
        "plant_capacity_units_per_year": 100,
        "product_selling_price_usd_per_unit": 10,
        "tax_rate": 0,
    }
    return values | changes


def test_annualized_shares_no_double_counting():
    result = UniversalProcessAdvisor(project()).analyze()
    assert result.annualized_capital_cost == 100
    assert result.total_annualized_cost == 600
    assert result.lcop == 6
    assert sum(c.share_pct for c in result.cost_components) == pytest.approx(100)
    assert result.category_shares_pct["utilities"] == pytest.approx(250 / 600 * 100)
    assert result.category_shares_pct["variable_opex"] == pytest.approx(400 / 600 * 100)
    assert len(result.top_drivers) == 3
    assert result.top_drivers[0].parameter == "utility"
    assert result.probability_of_capex_overrun is None


def test_named_power_and_raw_material_thresholds():
    data = project(
        variable_opex_usd_per_year=800,
        feedstock_opex_usd_per_year=350,
        utility_opex_usd_per_year=400,
        advisor_context={
            "name": "Green hydrogen electrolysis",
            "utilities": [{"name": "Electricity", "annual_cost": 400}],
            "raw_materials": [{"name": "Specialty substrate", "annual_cost": 350}],
        },
    )
    result = UniversalProcessAdvisor(data).analyze()
    assert result.classification == "electrochemical"
    assert not any("split" in w for w in result.warnings)
    utility = next(r for r in result.recommendations if r.parameter == "utility")
    raw = next(r for r in result.recommendations if r.parameter == "feedstock")
    assert utility.suggested_change_pct == 40
    assert raw.suggested_change_pct == 30
    assert utility.scope == "all utilities"
    assert raw.npv_change_usd == pytest.approx(-350 * 0.3 * 10)


def test_arbitrary_equipment_and_zero_discount():
    data = {
        "equipment_bom": [
            {"name": "Fermentation package", "cost_usd": 500, "quantity": 2}
        ],
        "opex_breakdown": {
            "fixed": 100,
            "raw_materials": [{"name": "Methanol", "annual_cost": 300}],
            "utilities": [{"name": "Steam", "annual_cost": 100}],
        },
        "operating_years": 10,
        "discount_rate": 0,
        "context": {"name": "Protein from air fermentation"},
    }
    result = UniversalProcessAdvisor(data).analyze()
    assert result.classification == "biological"
    assert result.total_annualized_cost == 600
    assert result.lcop is None
    assert result.recommendations[0].npv_base_usd is None


def test_assessment_result_profile_matches_lcop():
    request = demo_assessment()
    result = assessment(request)
    profile = UniversalProcessAdvisor(
        {"bom": result.bom.model_dump(), "financial": result.financial.model_dump()}
    ).analyze()
    assert profile.lcop == pytest.approx(result.financial.lcop_usd_per_unit)
    capital = next(r for r in profile.recommendations if r.parameter == "capex")
    assert capital.npv_change_usd < 0


@pytest.mark.parametrize(
    "changes",
    [
        {"discount_rate": -1},
        {"fixed_opex_usd_per_year": float("inf")},
        {"variable_opex_usd_per_year": 100},
        {"operating_years": 0},
        {"capacity_factor": 2},
        {"advisor_context": {"utilities": [{"name": "Power", "annual_cost": 900}]}},
    ],
)
def test_invalid_profiles(changes):
    with pytest.raises((ValueError, TypeError)):
        UniversalProcessAdvisor(project(**changes)).analyze()


def test_stream_only_not_fabricated():
    with pytest.raises(ValueError, match="Missing total_capex"):
        UniversalProcessAdvisor({"streams": [{"mass_flow_kg_h": 200}]}).analyze()


def test_endpoints_and_capital_stress_export():
    client = TestClient(app)
    body = demo_assessment().model_dump()
    response = client.post(
        "/api/assessment/universal-suggestions", json=body | {"streams": []}
    )
    assert response.status_code == 200, response.text
    assert response.json()["recommendations"]
    base = assessment(demo_assessment())
    body["costing"]["settings"]["capital_cost_multiplier"] = 1.3
    stressed = client.post("/api/assessment", json=body)
    assert stressed.status_code == 200, stressed.text
    assert stressed.json()["bom"]["total_bare_module_cost_usd"] == pytest.approx(
        base.bom.total_bare_module_cost_usd * 1.3
    )
    from io import BytesIO

    from openpyxl import load_workbook

    workbook = load_workbook(
        BytesIO(client.post("/api/export/excel", json=body).content)
    )
    assert workbook["Inputs"]["C20"].value == 1.3
    assert "Inputs!$C$20" in workbook["Equipment BOM"]["R6"].value
    assert (
        client.post(
            "/api/assessment/universal-suggestions", json={"financial": None}
        ).status_code
        == 422
    )


class FakeStream:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    def __aiter__(self):
        async def events():
            yield NS(
                type="response.output_text.delta", delta="Grid tariff evidence [1]."
            )
            annotation = NS(
                type="url_citation",
                url="https://www.eia.gov/electricity/",
                title="EIA",
                start_index=21,
                end_index=24,
            )
            response = NS(
                output=[
                    NS(type="web_search_call", status="completed"),
                    NS(type="message", content=[NS(annotations=[annotation])]),
                ]
            )
            yield NS(type="response.completed", response=response)

        return events()


class FakeClient:
    def __init__(self):
        self.responses = self
        self.request = None

    async def create(self, **kwargs):
        self.request = kwargs
        return FakeStream()


def test_streaming_research_citations_actions_and_data_minimization():
    import asyncio

    payload = project(
        secret="DO_NOT_SEND_THIS", streams=[{"private_data": "DO_NOT_SEND_THIS"}]
    )
    profile = UniversalProcessAdvisor(payload).analyze()
    request = ResearchRequest(project=payload)
    client = FakeClient()

    async def collect():
        return [
            event
            async for event in research_events(
                profile,
                request,
                ResearchSettings(openai_api_key="dummy-test-key"),
                client=client,
            )
        ]

    events = asyncio.run(collect())
    assert any("event: delta" in e for e in events)
    assert any("event: citation" in e and "www.eia.gov" in e for e in events)
    assert any(
        "event: complete" in e and "web_search_with_citations" in e for e in events
    )
    assert "DO_NOT_SEND_THIS" not in client.request["input"]
    assert client.request["tools"][0]["type"] == "web_search"
    assert client.request["tool_choice"] == "required"
    assert client.request["store"] is False
    assert "CAPEX overrun" in client.request["instructions"]
    assert json.loads(events[1].split("data: ")[1])[0]["parameter"] in {
        "capex",
        "feedstock",
        "utility",
        "fixed_opex",
    }


@pytest.mark.parametrize(
    "name,sector",
    [
        ("Water electrolysis hydrogen", "electrochemical"),
        ("Thermal pyrolysis", "thermal"),
        ("Protein fermentation", "biological"),
        ("PSA separation", "separation"),
        ("Chemical recycling", "circular"),
        ("Specialty chemicals", "specialty"),
    ],
)
def test_sector_classification(name, sector):
    assert (
        UniversalProcessAdvisor(project(advisor_context={"name": name}))
        .analyze()
        .classification
        == sector
    )


def test_missing_key_is_explicit(monkeypatch):
    from app import main

    monkeypatch.setattr(
        main, "ResearchSettings", lambda: ResearchSettings(openai_api_key="")
    )
    response = TestClient(app).post(
        "/api/copilot/research-sensitivities", json={"project": project()}
    )
    assert response.status_code == 503
    assert "OPENAI_API_KEY" in response.json()["detail"]


def test_interrupted_stream_and_safe_provider_failure():
    import asyncio

    class BrokenClient:
        def __init__(self):
            self.responses = self

        async def create(self, **kwargs):
            raise ValueError("PRIVATE_PROVIDER_ERROR_DO_NOT_LEAK")

    async def collect():
        return [
            event
            async for event in research_events(
                UniversalProcessAdvisor(project()).analyze(),
                ResearchRequest(project=project()),
                ResearchSettings(openai_api_key="dummy"),
                client=BrokenClient(),
            )
        ]

    events = asyncio.run(collect())
    assert "event: error" in events[-1]
    assert "PRIVATE_PROVIDER_ERROR" not in "".join(events)


def test_stream_summary_does_not_infer_energy_or_leak_raw_fields():
    profile = UniversalProcessAdvisor(
        project(
            streams=[
                {
                    "phase": "gas",
                    "mass_flow_kg_h": 123,
                    "private_field": "do-not-forward",
                }
            ]
        )
    ).analyze()
    assert profile.stream_summary["count"] == 1
    assert profile.stream_summary["phase_counts"] == {"gas": 1}
    assert "private_field" not in str(profile.model_dump())
    assert profile.financial_basis["product_selling_price_usd_per_unit"] == 10


def test_currency_and_missing_costs_are_not_silently_reinterpreted():
    with pytest.raises(ValueError, match="USD"):
        UniversalProcessAdvisor(project(currency="EUR")).analyze()
    data = project(fixed_opex_usd_per_year=None)
    assert any(
        "fixed_opex" in w for w in UniversalProcessAdvisor(data).analyze().warnings
    )
