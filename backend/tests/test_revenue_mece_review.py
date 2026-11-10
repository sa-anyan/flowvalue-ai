"""Review popup uses canonical income models and source-backed price proposals."""

import copy
from decimal import Decimal
from unittest.mock import Mock
import pytest
from backend.tests.test_isolated_stages import study
from backend.blocks.execution import run_stage
from backend.revenue.rate_workspace import RateLine, RateStudyRequest, save_rates
from backend.revenue.price_review import propose_review, validate_review

CASES = [
    (
        "capacity_availability",
        "reservation",
        {
            "quantity": 100,
            "rate": 2,
            "unit": "m3",
            "period": "monthly",
            "availability": 0.9,
        },
        2160,
    ),
    (
        "infrastructure_usage",
        "usage",
        {"quantity": 1000, "rate": 5, "unit": "pallet-day"},
        5000,
    ),
    (
        "environmental_attributes",
        "credits",
        {
            "quantity": 200,
            "rate": 45,
            "eligibility": "Explicit scenario eligibility",
            "ownership": "Project owns the attributes",
        },
        9000,
    ),
    ("other_contractual_income", "fixed", {"fixed": 50000}, 50000),
    (
        "processing_services",
        "processed_quantity",
        {"quantity": 100, "rate": 200, "unit": "tonne"},
        20000,
    ),
]


@pytest.mark.parametrize("method,subtype,inputs,expected", CASES)
def test_all_nonproduct_mece_forms_reach_existing_python_ledger(
    study, method, subtype, inputs, expected
):
    store, key = study
    run_stage(store, key, "engineering_data")
    state = store.get(key)
    values = {
        "name": "Explicit test income",
        "description": "Independent synthetic commercial terms",
        **inputs,
    }
    line = RateLine(
        id="income",
        name=values["name"],
        kind="service",
        category=method,
        method_form={"method": method, "subtype": subtype, "inputs": values},
    )
    request = RateStudyRequest(
        revision=state["revision"],
        lines=[line],
        remove=[r["id"] for r in state["plan"]["operating_economics"]["sales"]],
        days_per_year=314,
        hours_per_day=24,
        approve=True,
    )
    save_rates(store, key, request)
    state = run_stage(store, key, "revenue")
    result = state["results"]["stages"]["revenue"]["result"]
    assert result and not result["issues"]
    assert Decimal(result["annual"][0]["sales_revenue"]) == Decimal(expected)
    assert (
        store.get(key)["plan"]["operating_economics"]["commercial_lines"][0][
            "method_form"
        ]["method"]
        == method
    )


def test_product_coproduct_ranges_and_timeline_share_one_schedule(study):
    store, key = study
    run_stage(store, key, "engineering_data")
    state = store.get(key)
    base = dict(kind="product", rate=2, rate_unit="kg/h", price=5, price_unit="kg")
    request = RateStudyRequest(
        revision=state["revision"],
        lines=[
            RateLine(id="main", name="Main", **base),
            RateLine(
                id="co",
                name="Co-product",
                role="byproduct",
                price_review={
                    "minimum": 3,
                    "maximum": 7,
                    "origin": "user",
                    "rationale": "Explicit test interval",
                },
                **base,
            ),
        ],
        remove=[r["id"] for r in state["plan"]["operating_economics"]["sales"]],
        days_per_year=100,
        hours_per_day=10,
        operating_years=1,
        approve=True,
    )
    save_rates(store, key, request)
    state = run_stage(store, key, "revenue")
    result = state["results"]["stages"]["revenue"]["result"]
    assert len(result["annual"]) == 1
    assert Decimal(result["annual"][0]["sales_revenue"]) == 20000
    saved = store.get(key)
    assert (
        saved["analysis_schedule"]["analysis_years"]
        - saved["analysis_schedule"]["construction_years"]
        == 1
    )
    co = next(
        r for r in saved["plan"]["operating_economics"]["sales"] if r["id"] == "co"
    )
    assert co["role"] == "byproduct" and co["price_review"]["minimum"] == 3


def research_state():
    return {
        "plan": {
            "operating_economics": {
                "price_basis": {"currency": "USD", "price_period": "2026"},
                "sales": [{"id": "sale", "name": "Product", "quantity_unit": "kg"}],
            }
        }
    }


def evidence():
    return {
        "retrieved_at": "2026-11-10",
        "sources": [{"url": "https://example.org/a"}, {"url": "https://example.org/b"}],
        "candidates": [
            {
                "name": "Bulk grade A",
                "price": 13,
                "currency": "USD",
                "quantity_unit": "kg",
                "price_period": "2026",
                "source_date": "2026-10-01",
                "source_url": "https://example.org/a",
            },
            {
                "name": "Comparable grade B",
                "price": 34,
                "currency": "USD",
                "quantity_unit": "kg",
                "price_period": "2026",
                "source_date": "2026-10-02",
                "source_url": "https://example.org/b",
            },
        ],
    }


def test_research_chooses_only_returned_prices_and_python_bounds():
    state = research_state()
    before = copy.deepcopy(state)
    provider = Mock()
    provider.generate.return_value = {
        "candidate": 1,
        "rationale": "Grade B matches the product specification better; bulk terms remain provisional.",
    }
    proposal = propose_review(state, "sale", evidence(), provider)["price_review"]
    assert (proposal["minimum"], proposal["selected"], proposal["maximum"]) == (
        13,
        34,
        34,
    )
    assert state == before
    assert proposal["status"] == "proposed_not_applied"
    provider.generate.return_value = {"candidate": 9, "rationale": "Invented option"}
    with pytest.raises(ValueError, match="returned observation"):
        propose_review(state, "sale", evidence(), provider)


def test_missing_or_incompatible_evidence_never_gets_a_fake_range():
    draft = evidence()
    draft["candidates"][0]["currency"] = "GBP"
    draft["candidates"][1]["source_date"] = "unknown"
    provider = Mock()
    assert (
        propose_review(research_state(), "sale", draft, provider)["price_review"]
        is None
    )
    provider.generate.assert_not_called()
    with pytest.raises(ValueError, match="Minimum"):
        validate_review(
            {"minimum": 34, "maximum": 13, "rationale": "Bad"},
            24,
            "kg",
            {"currency": "USD", "price_period": "2026"},
        )


def test_research_opt_in_saves_only_a_review_proposal(study):
    from fastapi.testclient import TestClient
    from unittest.mock import patch
    from backend.api import app as api

    store, key = study
    run_stage(store, key, "engineering_data")
    state = store.get(key)
    target = state["plan"]["operating_economics"]["sales"][0]
    data = evidence()
    for row in data["candidates"]:
        row["quantity_unit"] = target["quantity_unit"]
    data.update(kind="market", target_id=target["id"])
    provider = Mock()
    provider.generate.return_value = {
        "candidate": 0,
        "rationale": "Synthetic matching grade and scale; not a supplier quotation",
    }
    with patch.object(api, "store", store), patch.object(
        api.executor, "submit", side_effect=lambda work: work()
    ), patch(
        "backend.orchestration.deep_research.research_draft", return_value=data
    ) as researcher, patch(
        "backend.orchestration.provider.EngineeringProvider", return_value=provider
    ):
        client = TestClient(api.app)
        endpoint = f"/api/assessments/{key}/research"
        body = {
            "revision": state["revision"],
            "kind": "market",
            "target_id": target["id"],
            "recommend_price": True,
        }
        assert client.post(endpoint, json={**body, "consent": False}).status_code == 422
        researcher.assert_not_called()
        response = client.post(endpoint, json={**body, "consent": True})
        assert response.status_code == 202, response.text
    saved = store.get(key)
    assert saved["plan"] == state["plan"]
    assert saved["research_drafts"][-1]["price_review"]["selected"] == 13
    assert saved["research_job"]["plan_changed"] is False


def test_price_research_draft_does_not_require_inventing_a_physical_rate(study):
    store, key = study
    run_stage(store, key, "engineering_data")
    state = store.get(key)
    request = RateStudyRequest(
        revision=state["revision"],
        lines=[
            RateLine(
                id="unresolved-sale", name="Explicit proposed product", kind="product"
            )
        ],
        days_per_year=314,
        hours_per_day=24,
    )
    save_rates(store, key, request)
    saved = store.get(key)
    row = next(
        r
        for r in saved["plan"]["operating_economics"]["sales"]
        if r["id"] == "unresolved-sale"
    )
    assert (
        row["unit_price"] is None
        and row["stream_key"] is None
        and "manual_rate" not in row
    )
    request.revision = saved["revision"]
    request.approve = True
    with pytest.raises(ValueError, match="rate and time unit"):
        save_rates(store, key, request)
    assert store.get(key)["revision"] == saved["revision"]
