"""Financial JSON is executable input, not commentary, with blank-only writes."""

import copy
from unittest.mock import patch

import pytest

from backend.blocks.financial.proposal import FIELDS, merge, prepare, validate_policy
from backend.blocks.models import Context, DataRequired
from backend.blocks.execution import run_stage
from backend.tests.test_isolated_stages import study


def policy():
    return {"depreciation_years": 10, "discount_rate": .1, "tax_rate": .25,
            "salvage_fraction": 0, "working_capital_recovery_fraction": 1, "closure_allowance": 0,
            "rationale": "Synthetic preliminary scenario, not jurisdictional tax advice",
            "field_rationales": {key: "Synthetic planning assumption" for key in FIELDS}}


class Provider:
    model = "synthetic"
    def __init__(self, value=None):
        self.calls = 0
        self.value = policy() if value is None else value
    def generate(self, **request):
        self.calls += 1
        return copy.deepcopy(self.value)


@pytest.mark.parametrize("key,value", [("tax_rate", 25), ("discount_rate", True), ("discount_rate", float('nan')),
                                        ("depreciation_years", 2.5), ("closure_allowance", -1)])
def test_invalid_json_is_rejected(key, value):
    p = policy()
    p[key] = value
    with pytest.raises(ValueError):
        validate_policy(p)


def test_merge_preserves_user_values_zeroes_schedule_and_other_costs():
    original = {"financial": {"tax_rate": 0, "discount_rate": .07, "operating_years": 18,
                              "production_ramp": [.2, .4], "rationale": "User basis"},
                "materials": [{"unit_price": 5}], "price_basis": {"currency": "GBP", "price_period": "2026"}}
    before = copy.deepcopy(original)
    config, applied = merge(original, policy(), "synthetic")
    assert config["financial"]["tax_rate"] == 0 and config["financial"]["discount_rate"] == .07
    assert config["financial"]["production_ramp"] == [.2, .4]
    assert config["financial"]["rationale"] == "User basis"
    assert config["financial"]["price_basis"] == original["price_basis"]
    assert "tax_rate" not in applied and original == before
    assert config["financial_input_provenance"]["depreciation_years"]["origin"] == "ai"


def test_complete_saved_inputs_never_call_ai_again():
    provider = Provider()
    ctx = Context({"plan": {"operating_economics": {"financial": policy()}}}, {}, {}, None, provider=provider, use_ai=True)
    _, changed = prepare(ctx)
    assert not changed and provider.calls == 0


def test_ai_disabled_and_invalid_response_leave_saved_values_alone():
    state = {"plan": {"operating_economics": {"financial": {"tax_rate": .2}}}}
    provider = Provider({"summary": "Commentary is not a policy"})
    assert prepare(Context(state, {}, {}, None, provider=provider))[1] is False
    before = copy.deepcopy(state)
    with pytest.raises(DataRequired, match="Retry Financial"):
        prepare(Context(state, {}, {}, None, provider=provider, use_ai=True))
    assert state == before


def test_financial_proposal_runs_canonical_engine_and_preserves_upstream(study):
    store, key = study
    from backend.revenue.authority import update

    run_stage(store, key, "engineering_data")
    state = store.get(key)
    update(store, key, state["revision"], approve=True)
    for stage in ("equipment", "capex", "revenue", "opex"):
        run_stage(store, key, stage)
    state = store.get(key)
    config = state["plan"]["operating_economics"]
    for field in (*FIELDS, "rationale"):
        config["financial"].pop(field, None)
    state = store.put(state, state["revision"])
    upstream = copy.deepcopy(state["stage_outputs"])
    provider = Provider()
    result = run_stage(store, key, "financial", use_ai=True, provider=provider)
    assert result["stage_runs"]["financial"]["status"] == "ready", result["stage_runs"]["financial"]
    assert result["results"]["stages"]["financial"]["result"]["ledger"]
    assert result["plan"]["operating_economics"]["financial"]["discount_rate"] == .1
    assert all(result["stage_outputs"][stage] == payload for stage, payload in upstream.items())
    run_stage(store, key, "financial", use_ai=True, provider=provider)
    assert provider.calls == 1
