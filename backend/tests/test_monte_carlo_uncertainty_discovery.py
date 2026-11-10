"""Registered uncertain inputs route through canonical costing without baseline edits."""

import copy
from backend.tests.test_monte_carlo import complete_state
from backend.scenarios_and_uncertainty.monte_carlo.discovery import discover
from backend.scenarios_and_uncertainty.monte_carlo.models import Settings
from backend.scenarios_and_uncertainty.monte_carlo.scenarios import prepare, apply
from backend.scenarios_and_uncertainty.monte_carlo.engine import evaluate


def test_default_capital_factors_have_published_ranges_and_recalculate():
    state = complete_state()
    before = copy.deepcopy(state)
    registered = discover(state)
    settings = Settings.model_validate(registered["settings"])
    piping = next(
        p for p in settings.parameters if p.id == "capex.selected_factors.piping"
    )
    assert (piping.minimum, piping.mode, piping.maximum) == (0.15, 0.15, 0.7)
    assert not piping.enabled
    piping.enabled = True
    plan = prepare(state, settings)
    assert plan["capex"]["selected_factors"]["piping"] == 0.15
    low = copy.deepcopy(plan)
    high = copy.deepcopy(plan)
    apply(low, [piping], [0.15])
    apply(high, [piping], [0.7])
    report = state["parsed"]["report"]
    a = evaluate(report, state["description"], low, set())
    b = evaluate(report, state["description"], high, set())
    assert b["metrics"]["capex"] > a["metrics"]["capex"]
    assert b["metrics"]["npv"] < a["metrics"]["npv"]
    assert state == before
    assert not any(
        p.id == "capex.selected_factors.equipment_installation"
        for p in settings.parameters
    )


def test_ai_ranges_are_preserved_without_inventing_bounds_for_other_guesses():
    state = complete_state()
    financial = state["plan"]["operating_economics"]["financial"]
    financial["input_provenance"] = {
        "discount_rate": {
            "low": 0.06,
            "high": 0.15,
            "source": "AI preliminary economic scenario",
            "rationale": "Editable process-specific scenario, not a calibrated probability",
        }
    }
    result = discover(state)
    discount = next(
        p
        for p in result["settings"]["parameters"]
        if p["id"] == "operating_economics.financial.discount_rate"
    )
    assert discount["minimum"] == 0.06
    assert discount["maximum"] == 0.15
    assert discount["mode"] == financial["discount_rate"]
    assert discount["source"] == "AI preliminary economic scenario"
    closure = next(
        p
        for p in result["settings"]["parameters"]
        if p["id"] == "operating_economics.financial.closure_allowance"
    )
    assert closure["minimum"] is None and not closure["enabled"]
    assert result["uncertainty_inventory"]["needs_bounds"] > 0


def test_fixed_source_observations_and_non_numeric_metadata_are_not_sample_targets():
    state = complete_state()
    before = copy.deepcopy(state["parsed"])
    data = discover(state)
    targets = [t for p in data["settings"]["parameters"] for t in p["targets"]]
    assert all(t[0] in {"equipment", "capex", "operating_economics"} for t in targets)
    assert all("equipment_key" not in t and "source" not in t for t in targets)
    assert state["parsed"] == before


def test_ai_proposals_cannot_replace_saved_central_value_or_enable_locked_inputs():
    state = complete_state()
    data = discover(state)
    selected = next(p for p in data['settings']['parameters'] if p['id'] == 'operating_economics.financial.discount_rate')
    original = selected['mode']
    state['locked'] = ['operating_economics']
    state['mc_assumption_proposals'] = [{**selected, 'mode': .9, 'minimum': .01, 'maximum': .99, 'enabled': True}]
    result = next(p for p in discover(state)['settings']['parameters'] if p['id'] == selected['id'])
    assert result['mode'] == original
    assert not result['enabled']


def test_all_eligible_factors_complete_without_inventing_offsite_scope():
    from backend.scenarios_and_uncertainty.monte_carlo.sampling import validate
    state = complete_state()
    original = Settings.model_validate(discover(state)['settings'])
    settings = original.model_copy(deep=True)
    for p in settings.parameters:
        p.enabled = bool(not p.review_required and p.minimum is not None and p.maximum is not None and p.minimum < p.maximum and p.rationale and p.mode is not None)
    offsite = next(p for p in settings.parameters if p.id == 'capex.selected_factors.offsite_facilities')
    assert offsite.review_required and not offsite.enabled
    enabled, _ = validate(settings, original)
    plan = prepare(state, settings)
    apply(plan, enabled, [p.mode for p in enabled])
    outcome = evaluate(state['parsed']['report'], state['description'], plan, set())
    assert outcome['status'] == 'complete', outcome['issues']
    offsite.enabled = True
    import pytest
    with pytest.raises(ValueError, match='nonoverlapping'):
        validate(settings, original)
    state['plan']['capex']['offsite_scope_confirmation'] = 'Explicit synthetic nonoverlapping offsite scope for this separate test'
    discovered = discover(state)
    assert not next(p for p in discovered['settings']['parameters'] if p['id'] == offsite.id)['review_required']
