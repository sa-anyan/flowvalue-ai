"""Real registry recovery/scaling; mocked model review, no paid/network calls."""
import copy

import pytest

from backend.blocks.equipment.calculation import calculate_equipment
from backend.equipment_costing.fallback import garrett_candidates
from backend.equipment_costing.unit_conversion.bridges.automatic import repair_pricing
from backend.equipment_costing.unit_conversion.bridges.service import evaluate
from backend.orchestration.store import Store
from backend.tests.test_automatic_equipment_inputs import decision
from backend.tests.test_unit_conversion_bridges import REPORT


def failed_plan():
    inputs = dict(product_rate_kg_h=100, production_allocation_fraction=1,
                  volumetric_productivity_kg_m3_h=0.5, working_fraction=0.8)
    return {"equipment": [{
        "equipment_key": "e", "curve_id": "fermenter_reactor_turton_2001",
        "quantity": 2,
        "unit_conversion": {
            "enabled": True, "origin": "llm_selected_python_equation",
            "model_id": "fermenter_reactor_turton_2001", "method": "vessel_productivity",
            "operating_mode": "continuous", "measurement_id": None, "derivations": [],
            "inputs": inputs,
            "input_provenance": {n: {"status": "llm_estimate", "value": v} for n, v in inputs.items()},
            "unit_context": {"target_gallon_basis": None},
        },
        "costing_options": {"allow_unverified": True},
    }]}


class Review:
    model = "offline-fallback-review"
    calls = 0

    def generate(self, **kw):
        self.calls += 1
        feedback = kw['context']['repair_feedback'][0]
        assert 'G258-007' in feedback['recovered_candidate_model_ids']
        assert feedback['preserve_physical_basis']
        d = decision()
        d.update(model_id='G258-007', method='vessel_productivity',
                 operating_mode='continuous', measurement_id=None,
                 rationale='Preliminary 50 psi agitated-reactor costing proxy; pressure rating differs from ambient baseline. No aeration/media/bioreactor internals priced; configuration requires user review.')
        # Deliberately different AI guesses must not replace the saved 250 m3.
        units = {'product_rate_kg_h': 'kg/h', 'production_allocation_fraction': 'fraction',
                 'volumetric_productivity_kg_m3_h': 'kg/m3/h', 'working_fraction': 'fraction'}
        inputs = failed_plan()['equipment'][0]['unit_conversion']['inputs']
        d['assumptions'] = [{'name': n, 'value': v * (2 if n == 'product_rate_kg_h' else 1),
                             'unit': units[n], 'rationale': 'Review proposal', 'limitations': 'Preliminary'}
                            for n, v in inputs.items()]
        return {'decisions': [d]}


def test_recovers_garrett_when_original_match_has_no_alternatives(tmp_path):
    plan = failed_plan()
    original = copy.deepcopy(plan)
    total, _ = calculate_equipment(REPORT, plan)
    assert total.equipment[0].amount is None
    assert any('MODEL_OUT_OF_RANGE' in i for i in total.equipment[0].issues)
    reviewer = Review()
    updated, audit = repair_pricing(REPORT, plan, total, '', Store(tmp_path / 'fallback.db'), reviewer)
    row = updated['equipment'][0]
    assert reviewer.calls == 1
    assert row['curve_id'] == 'G258-007'
    assert row['unit_conversion']['inputs'] == original['equipment'][0]['unit_conversion']['inputs']
    assert row['unit_conversion']['unit_context']['target_gallon_basis'] == 'US'
    assert evaluate(REPORT, 'e', row['unit_conversion'])['size'] == pytest.approx(66043.0130895)
    priced, _ = calculate_equipment(REPORT, updated)
    from backend.orchestration.codec import plain
    from backend.orchestration.pricing_status import annotate
    display = plain(priced)
    annotate(display, REPORT, updated)
    assert display['equipment'][0]['decision']['matching'].startswith('ambiguous')
    line = priced.equipment[0]
    assert line.amount > 0 and line.quantity == 2
    assert line.calculation.estimate.extrapolated is True
    assert line.calculation.estimate.exponent == 0.53
    assert line.calculation.estimate.period == 'early 1987'
    assert line.calculation.estimate.currency == 'USD'
    assert any(a['status'] == 'retained_physical_basis' for a in audit)
    assert any(a['status'] == 'cost_fallback_candidates_discovered' for a in audit)
    assert plan == original  # Preview never mutates saved caller state.
    from backend.equipment_costing.cost_to_future.cost_translation import DEFAULT_POLICY
    from backend.capex.connectors import prepare_capex_inputs
    current, _ = calculate_equipment(REPORT, updated, DEFAULT_POLICY)
    repeat, _ = calculate_equipment(REPORT, updated, DEFAULT_POLICY)
    after = current.equipment[0]
    assert after.amount == repeat.equipment[0].amount
    assert after.amount == pytest.approx(line.amount * 336.940 / 113.6)
    assert after.calculation.historical_amount == line.calculation.historical_amount
    assert after.calculation.estimate.period == '2026-09'
    assert after.calculation.estimate.currency == 'USD'
    assert after.amount == pytest.approx(after.calculation.amount * 2)
    prepared = prepare_capex_inputs(current, process_type='fluids', delivery_basis='delivered')
    assert prepared.equipment[0].period == '2026-09'
    assert prepared.equipment[0].index_series == 'PRICE_BASIS:USD:2026-09'


@pytest.mark.parametrize('protection', ['manual', 'quote', 'user_model', 'user_sizing', 'alias', 'unsuitable', 'graph_off'])
def test_protected_or_disallowed_rows_do_not_open_fallback(tmp_path, protection):
    plan = failed_plan()
    total, _ = calculate_equipment(REPORT, plan)
    row = plan['equipment'][0]
    if protection == 'manual': row['manual_price'] = {'amount': 100}
    if protection == 'quote': row['external_quote'] = {'amount': 100}
    if protection == 'user_model': row['model_selection'] = {'origin': 'user', 'curve_id': row['curve_id']}
    if protection == 'user_sizing': row['unit_conversion']['input_provenance']['working_fraction']['status'] = 'user_input'
    if protection == 'alias': row['scope_decision'] = 'alias'
    if protection == 'unsuitable': row['matching'] = {'conceptual_validation': 'unsuitable'}
    if protection == 'graph_off': plan['equipment_input_policy'] = {'allow_provisional_graph_estimates': False}
    class NoCall:
        def generate(self, **kw): raise AssertionError('Protected row must not call AI')
    updated, _ = repair_pricing(REPORT, plan, total, '', Store(tmp_path / (protection+'.db')), NoCall())
    assert updated == plan


def test_discovery_does_not_offer_tank_or_mixer_for_reactor():
    row = failed_plan()['equipment'][0]
    assert garrett_candidates(REPORT, 'e', row) == ['G258-006', 'G258-007', 'G299-133']
    assert garrett_candidates(REPORT, 'e', row, excluded=['G258-006', 'G258-007', 'G299-133']) == []
    row['unit_conversion']['inputs']['working_fraction'] = 0
    assert garrett_candidates(REPORT, 'e', row) == []


def test_reviewer_can_decline_without_fabricating_a_price(tmp_path):
    plan = failed_plan()
    original = copy.deepcopy(plan)
    total, _ = calculate_equipment(REPORT, plan)
    class Decline(Review):
        def generate(self, **kw):
            result = super().generate(**kw)
            result['decisions'][0]['status'] = 'unresolved'
            result['decisions'][0]['rationale'] = 'None of these configurations is suitable for the stated service.'
            return result
    reviewer = Decline()
    updated, audit = repair_pricing(REPORT, plan, total, '', Store(tmp_path/'decline.db'), reviewer)
    assert updated == original
    assert reviewer.calls <= 2  # Existing resolver permits one review repair, never an unbounded loop.
    priced, _ = calculate_equipment(REPORT, updated)
    assert priced.equipment[0].amount is None
    assert any(a['status'] == 'input_resolution_unresolved' for a in audit)
