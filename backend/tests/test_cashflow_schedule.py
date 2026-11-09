"""Cashflow calendar uses canonical revenue and finance, without provider calls."""

from decimal import Decimal
from unittest.mock import patch
import pytest
from backend.blocks.cashflow.schedule import (
    make_policy,
    apply_policy,
    validate,
    save,
    factor,
)
from backend.blocks.cashflow.view import snapshot
from backend.blocks.execution import run_stage
from backend.tests.test_isolated_stages import study
from backend.revenue.authority import fingerprint


def test_calendar_bounds_and_unknown_sources():
    policy = make_policy(6, 2)
    assert policy["production_ramp"] == [0.2, 0.4, 0.6, 0.8]
    for years, construction in [(2, 2), (61, 2), (20, 11), (True, 0)]:
        with pytest.raises(ValueError):
            make_policy(years, construction)
    for bad in [-0.1, 1.1, "NaN", "Infinity"]:
        with pytest.raises(ValueError):
            validate({**policy, "production_ramp": [bad, 0.5, 1, 1]})
    with pytest.raises(ValueError):
        validate({**policy, "revenue_factors": {"3": {"product:invented": 0.5}}})


def test_factors_are_annual_and_approval_bound():
    config = {"sales": [{"id": "water"}]}
    policy = make_policy(6, 2)
    policy["revenue_factors"] = {"3": {"product:water": 0.5}}
    revised = apply_policy(config, policy)
    assert factor(revised, "product", "water", 1) == Decimal(".5")
    assert factor(revised, "product", "water", 2) == 1
    assert factor(revised, "commercial", "service", 1) == 1
    original = fingerprint(revised, "water", {})
    revised["cashflow_schedule"]["revenue_factors"]["3"]["product:water"] = 0.8
    assert fingerprint(revised, "water", {}) != original
    assert "financial" not in config


def test_canonical_ledger_and_year_edit(study):
    store, key = study
    run_stage(store, key, "engineering_data")
    state = store.get(key)
    policy = make_policy(6, 2)
    saved = save(store, key, state["revision"], policy, approve_revenue=True)
    with patch(
        "backend.orchestration.provider.EngineeringProvider",
        side_effect=AssertionError("No LLM"),
    ):
        for stage in ["equipment", "capex", "revenue", "opex", "financial"]:
            state = run_stage(store, key, stage, use_ai=False)
    result = snapshot(store.get(key))
    assert result["has_financial_ledger"], state["stage_runs"]["financial"]
    assert len(result["rows"]) == 7
    assert [str(r["revenue"]) for r in result["rows"][1:3]] == ["0", "0"]
    before = Decimal(result["rows"][3]["revenue"])
    source = result["streams"][0]["id"]
    policy["revenue_factors"] = {"3": {source: 0.5}}
    save(store, key, store.get(key)["revision"], policy, approve_revenue=True)
    run_stage(store, key, "revenue", use_ai=False)
    edited = snapshot(store.get(key))
    assert Decimal(edited["rows"][3]["stream_revenue"][source]) == before / 2
    assert edited["financial_stale"]
    save(store, key, store.get(key)["revision"], policy)
    assert not store.get(key).get("revenue_approval")


def test_commercial_source_factor_and_horizon_extension():
    from backend.tests.test_revenue_mece import config_line
    from backend.tests.test_operating_economics import fixture, DESCRIPTION
    from backend.tests.test_capex import inputs
    from backend.capex import calculate_capex
    from backend.orchestration.operating_economics import calculate_operating_study

    report, config, _ = fixture()
    config["sales"] = []
    config["commercial_lines"] = [config_line(config["financial"]["operating_years"])]
    base = calculate_operating_study(
        report, DESCRIPTION, config, calculate_capex(inputs=inputs())
    )
    build = config["financial"]["construction_years"]
    life = config["financial"]["operating_years"]
    policy = make_policy(
        life + build, build, {"production_ramp": config["financial"]["production_ramp"]}
    )
    identity = config["commercial_lines"][0]["id"]
    policy["revenue_factors"] = {str(build + 1): {"commercial:" + identity: 0.5}}
    revised = apply_policy(config, policy)
    changed = calculate_operating_study(
        report, DESCRIPTION, revised, calculate_capex(inputs=inputs())
    )
    assert (
        changed["revenue"].annual[0].sales_revenue
        == base["revenue"].annual[0].sales_revenue / 2
    )
    assert (
        changed["revenue"].annual[1].sales_revenue
        == base["revenue"].annual[1].sales_revenue
    )
    assert (
        revised["commercial_lines"][0]["years"]
        == config["commercial_lines"][0]["years"]
    )
    longer = apply_policy(config, make_policy(life + build + 1, build))
    assert len(longer["commercial_lines"][0]["years"]) == life + 1
    assert "provisional" in longer["commercial_lines"][0]["schedule_extension_basis"]


def test_default_plateau_and_preservation():
    policy = make_policy(20, 2)
    assert policy["production_ramp"][:4] == [0.2, 0.4, 0.6, 0.8]
    assert all(v == 0.8 for v in policy["production_ramp"][3:])
    assert "not published Garrett" in policy["rationale"]
    assert (
        make_policy(20, 2, {"production_ramp": [0.3, 0.7]})["production_ramp"]
        == [0.3] + [0.7] * 17
    )


def test_browser_number_serialization_does_not_invalidate_approval(study):
    from backend.revenue.authority import update
    from backend.orchestration.service import edit
    import json

    store, key = study
    run_stage(store, key, "engineering_data")
    policy = make_policy(6, 2, {"production_ramp": [1]})
    save(store, key, store.get(key)["revision"], policy, approve_revenue=True)
    state = store.get(key)
    # JSON.stringify turns 1.0 into 1; this must not make Python reject approval.
    config = json.loads(
        json.dumps(state["plan"]["operating_economics"]).replace("1.0", "1")
    )
    edited = edit(
        store,
        key,
        state["revision"],
        "operating_economics",
        config,
        "User review",
        manual_revenue=True,
    )
    update(store, key, edited["revision"], approve=True)
    result = run_stage(store, key, "revenue", use_ai=False)
    assert result["stage_runs"]["revenue"]["status"] == "ready", result["stage_runs"][
        "revenue"
    ]
