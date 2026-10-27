"""AI setup and scenario isolation checks; no live provider calls or credentials."""

import asyncio
import json

import httpx
import pytest
from fastapi.testclient import TestClient
from openai import APIStatusError

from app import main
from app.agent import availability
from app.agent.copilot_research import ResearchSettings

client = TestClient(main.app)


@pytest.mark.parametrize(
    "key,enabled,state,can_generate",
    [
        ("", True, "not_configured", False),
        ("secret-never-return", False, "disabled", False),
        ("secret-never-return", True, "configured", True),
    ],
)
def test_status_exposes_capability_without_secrets(
    monkeypatch, key, enabled, state, can_generate
):
    monkeypatch.setattr(
        main,
        "ResearchSettings",
        lambda: ResearchSettings(openai_api_key=key, ai_enabled=enabled),
    )
    r = client.get("/api/copilot/status")
    assert r.status_code == 200
    assert r.json()["state"] == state
    assert r.json()["can_generate"] is can_generate
    assert r.json()["connection_verified"] is False
    assert "secret-never-return" not in r.text


def test_disable_switch_blocks_every_provider_operation(monkeypatch):
    monkeypatch.setattr(
        main,
        "ResearchSettings",
        lambda: ResearchSettings(openai_api_key="dummy", ai_enabled=False),
    )
    payload = main.demo_assessment().model_dump(mode="json")
    for path, body in [
        ("check", None),
        ("executive-memo", payload),
        ("research-sensitivities", {"project": payload}),
    ]:
        r = client.post("/api/copilot/" + path, json=body)
        assert r.status_code == 503
        assert "disabled" in r.json()["detail"]


class ModelClient:
    def __init__(self, error=None):
        self.models = self
        self.error = error
        self.model = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def retrieve(self, model):
        self.model = model
        if self.error:
            raise self.error
        return {"id": model}


def test_connection_check_verifies_access_without_generation(monkeypatch):
    fake = ModelClient()
    monkeypatch.setattr(availability, "AsyncOpenAI", lambda **kwargs: fake)
    result = asyncio.run(
        availability.check_connection(
            ResearchSettings(openai_api_key="secret-never-return")
        )
    )
    assert fake.model == "gpt-5.4-mini"
    assert result["connection_verified"] is True
    assert "billing quota" in result["message"]
    assert "secret-never-return" not in json.dumps(result)


@pytest.mark.parametrize("status", [401, 403, 404, 429, 500])
def test_connection_errors_do_not_leak_provider_payload(monkeypatch, status):
    response = httpx.Response(
        status, request=httpx.Request("GET", "https://api.openai.com/v1/models/test")
    )
    fake = ModelClient(
        APIStatusError(
            "PRIVATE_PROVIDER_DETAIL",
            response=response,
            body={"secret": "PRIVATE_PROVIDER_DETAIL"},
        )
    )
    monkeypatch.setattr(availability, "AsyncOpenAI", lambda **kwargs: fake)
    monkeypatch.setattr(
        main, "ResearchSettings", lambda: ResearchSettings(openai_api_key="dummy")
    )
    r = client.post("/api/copilot/check")
    assert r.status_code == 503
    assert "PRIVATE_PROVIDER_DETAIL" not in r.text


def test_memo_uses_recomputed_scenario_and_includes_provenance(monkeypatch):
    captured = {}

    async def memo(context, settings):
        captured.update(context)
        return "# Screening memo\nReview engineering scope."

    monkeypatch.setattr(main, "draft_memo", memo)
    monkeypatch.setattr(
        main,
        "ResearchSettings",
        lambda: ResearchSettings(openai_api_key="secret-never-return"),
    )
    project = main.demo_assessment()
    project.costing.settings.capital_cost_multiplier = 1.3
    project.engineering_notes = ["INCOMPLETE EQUIPMENT SCOPE: R-101 excluded."]
    expected = main.assessment(project)
    r = client.post("/api/copilot/executive-memo", json=project.model_dump(mode="json"))
    assert r.status_code == 200
    assert captured["financial"]["npv_usd"] == expected.financial.npv_usd
    assert (
        captured["bom"]["total_bare_module_cost_usd"]
        == expected.bom.total_bare_module_cost_usd
    )
    assert project.engineering_notes[0] in captured["financial"]["warnings"]
    assert captured["is_demo"] is True
    assert captured["economic_summary"]["total_annual_opex_usd"] == 500000
    assert "never added again" in captured["economic_summary"]["cost_accounting_basis"]
    assert r.json()["generated_at"]
    assert r.json()["evidence_basis"] == "computed_scenario_only"
    assert "secret-never-return" not in r.text


def test_cloud_auth_protects_configuration_and_diagnostic(monkeypatch):
    monkeypatch.setenv("REQUIRE_AUTH", "true")
    assert client.get("/api/copilot/status").status_code == 401
    assert client.post("/api/copilot/check").status_code == 401


@pytest.mark.parametrize(
    "state,text,accepted",
    [
        ("completed", "Computed memo", True),
        ("incomplete", "Partial draft", False),
        ("completed", "", False),
    ],
)
def test_memo_rejects_incomplete_provider_output(monkeypatch, state, text, accepted):
    from types import SimpleNamespace

    from app.agent import executive_memo

    captured = {}

    class MemoClient(ModelClient):
        def __init__(self):
            self.responses = self

        async def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(status=state, output_text=text)

    monkeypatch.setattr(executive_memo, "AsyncOpenAI", lambda **kwargs: MemoClient())
    run = executive_memo.draft_memo(
        {"npv_usd": 123}, ResearchSettings(openai_api_key="dummy")
    )
    if accepted:
        assert asyncio.run(run) == text
    else:
        with pytest.raises(ValueError):
            asyncio.run(run)
    assert captured["store"] is False
    assert json.loads(captured["input"])["npv_usd"] == 123
