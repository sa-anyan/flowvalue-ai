"""Fresh inputs, honest provisional choices and batched review; no network."""
import copy
from types import SimpleNamespace
from unittest.mock import patch

from backend.blocks.autopilot import _pick_models
from backend.blocks.equipment.runner import prepare
from backend.blocks.run_store import RunStore
from backend.equipment_matching.service import apply_matches, catalogue, match_report
from backend.equipment_matching.library_preference import apply_preference
from backend.orchestration.store import Store


def gas_report():
    return {'entities': [
        {'key': 'e', 'kind': 'equipment', 'identifier': 'P-1', 'values': [], 'stream_keys': ['s'],
         'id_evidence': {'id': 'tag', 'original_value': 'P-1'}},
        {'key': 's', 'kind': 'material', 'identifier': 'Nitrogen', 'values': [
            {'id': 'd', 'property': 'description', 'normalized_value': 'Nitrogen gas enters P-1 for compression',
             'original_value': 'Nitrogen gas enters P-1 for compression'},
            {'id': 'm', 'property': 'mass_flow', 'normalized_value': 1000, 'normalized_unit': 'kg/h', 'status': 'verified'}]},
    ]}


def test_prefix_only_guess_is_not_selected_and_ai_sees_current_process(tmp_path):
    report = gas_report()
    state = {'effective_report': report, 'plan': {'equipment': []},
             'description': 'Compress nitrogen gas. There is no liquid pumping.'}
    _pick_models(state)
    assert not state['plan']['equipment'][0].get('curve_id')
    assert state['plan']['equipment'][0]['quick_match']['status'] == 'prefix_only'
    compressor = next(m for m in catalogue() if m['source'] == 'openpytea'
                      and m['equipment_name'].startswith('Compressors') and not m['coordinate_issues']
                      and m['availability'] != 'disabled')
    class Review:
        model = 'offline-gas-review'
        calls = []
        def generate(self, **kw):
            self.calls.append(1)
            assert 'nitrogen' in str(kw['context']).lower()
            return {'matches': [{
                'equipment_key': 'e', 'equipment_function': 'Gas compression', 'match_status': 'matched',
                'match_method': 'engineering_equivalence', 'candidate_model_ids': [compressor['model_id']],
                'selected_model_id': compressor['model_id'], 'model_scope': 'equipment',
                'conceptual_validation': 'suitable', 'reason': 'Compression of nitrogen gas, not liquid transfer.',
                'caveats': ['Pressure ratio remains a sizing input.'], 'context_evidence_ids': ['d']}]}
    provider = Review()
    ctx = SimpleNamespace(report=report, plan=state['plan'], state=state, use_ai=True,
                          store=RunStore(Store(tmp_path/'gas.db')), provider=provider)
    def no_sizing(report, plan, *a, **kw): return plan, []
    with patch('backend.equipment_resolution.duplicates.reconcile', return_value=(report, state['plan'], {})), \
         patch('backend.blocks.equipment.runner.expand', side_effect=lambda report, plan: (report, plan)), \
         patch('backend.blocks.equipment.runner.workbook_parameters_for', return_value={}), \
         patch('backend.equipment_costing.unit_conversion.bridges.automatic.resolve', side_effect=no_sizing):
        _, plan, _, issues, matching, *_ = prepare(ctx)
    assert len(provider.calls) == 1
    assert plan['equipment'][0]['curve_id'] == compressor['model_id']
    assert not any('you confirmed' in i for i in issues)
    assert matching['matches'][0]['equipment_function'] == 'Gas compression'


def test_all_autopilot_picks_still_receive_one_batch_review(tmp_path):
    report = gas_report()
    state = {'plan': {'equipment': [{'equipment_key': 'e', 'curve_id': 'G258-004',
                                     'model_selection': {'origin': 'autopilot', 'curve_id': 'G258-004'}}]}}
    ctx = SimpleNamespace(report=report, plan=state['plan'], state=state, use_ai=True, store=None, provider=None)
    with patch('backend.equipment_resolution.duplicates.reconcile', return_value=(report, state['plan'], {})), \
         patch('backend.blocks.equipment.runner.expand', side_effect=lambda r, p: (r, p)), \
         patch('backend.blocks.equipment.runner.workbook_parameters_for', return_value={}), \
         patch('backend.equipment_costing.unit_conversion.bridges.automatic.resolve', side_effect=lambda r,p,*a,**kw: (p,[])), \
         patch('backend.blocks.equipment.runner.match_report', return_value={'matches': [], 'batches': []}) as review, \
         patch('backend.blocks.equipment.runner.apply_matches', side_effect=lambda rows, result: rows):
        out = prepare(ctx)
    review.assert_called_once()
    assert not any('you confirmed' in i for i in out[3])


def test_library_preference_cannot_turn_agitated_into_nonagitated():
    models = {m['model_id']: m for m in catalogue()}
    alt = next(m for m in models.values() if m['source'] == 'openpytea'
               and m['equipment_name'].startswith('Reactors') and 'nonagitated' in m['configuration'])
    decision = {'selected_model_id': 'G258-007', 'candidate_model_ids': ['G258-007', alt['model_id']]}
    result, audit = apply_preference(decision, models)
    assert result['selected_model_id'] == 'G258-007'
    assert result['candidate_model_ids'][0] == alt['model_id']
    assert audit['applied'] is False


def test_model_review_does_not_deactivate_current_user_sizing():
    old = {'equipment_key': 'e', 'curve_id': 'G258-004', 'unit_conversion': {
        'enabled': True, 'inputs': {'residence_time_h': 1},
        'input_provenance': {'residence_time_h': {'status': 'user_input', 'value': 1}}}}
    match = {'equipment_key': 'e', 'review_available': True, 'match_status': 'matched',
             'selected_model_id': 'G258-008', 'candidate_model_ids': ['G258-008'],
             'conceptual_validation': 'suitable', 'source': 'garrett', 'reason': 'Alternative model'}
    row = apply_matches([old], {'matches': [match]})[0]
    assert row['unit_conversion'] == old['unit_conversion']
    assert row['curve_id'] == old['curve_id']
    assert row['matching_attempt'] == match


def test_no_persistent_response_reuse_across_runs(tmp_path):
    store = Store(tmp_path/'cache.db')
    context = {'task': 'matching', 'equipment': ['P-1']}
    with store.db() as db:
        db.execute('INSERT INTO ai_cache VALUES (?,?)', ('old', '{"confirmed":true}'))
    # A poisoned shared cache must never be consulted.
    store.cached = lambda *a: (_ for _ in ()).throw(AssertionError('Old response cache read'))
    calls = []
    def compute():
        calls.append(1)
        return {'proposal': len(calls)}
    a = RunStore(store)
    first, cached = a.cached(context, compute)
    assert cached is False
    first['proposal'] = 99
    assert a.cached(context, compute) == ({'proposal': 1}, True)
    b = RunStore(store)
    assert b.cached(context, compute) == ({'proposal': 2}, False)
    assert len(calls) == 2


def test_new_studies_do_not_inherit_choices(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    import backend.api.app as api
    from backend.tests.test_autopilot import _workbook
    store = Store(tmp_path/'new.db')
    monkeypatch.setattr(api, 'store', store)
    client = TestClient(api.app)
    content = _workbook()
    a = client.post('/api/assessments', files={'file': ('plant.xlsx', content)}).json()['id']
    old = store.get(a)
    old['plan']['equipment'] = [{'equipment_key': 'e', 'curve_id': 'G258-004',
                                 'model_selection': {'origin': 'user', 'curve_id': 'G258-004'}}]
    old['plan']['register_review'] = {'pump': {'decision': 'out_of_scope', 'basis': 'Previous project'}}
    old['locked'] = ['equipment']
    store.put(old, old['revision'])
    b = client.post('/api/assessments', files={'file': ('plant.xlsx', content)}).json()['id']
    fresh = store.get(b)
    assert a != b
    assert not fresh['plan'].get('equipment')
    assert not fresh['plan'].get('register_review')
    assert 'equipment' not in fresh.get('locked', [])
    assert store.get(a)['plan']['register_review'] == old['plan']['register_review']


def test_slow_background_review_does_not_hold_the_save_response(tmp_path, monkeypatch):
    from threading import Event
    from fastapi.testclient import TestClient
    import backend.api.app as api
    from backend.blocks import launch
    from backend.tests.test_autopilot import _workbook
    store = Store(tmp_path/'responsive.db')
    monkeypatch.setattr(api, 'store', store)
    monkeypatch.setattr(api._opex_brainstorm, 'ai_available', lambda: True)
    entered, finish = Event(), Event()
    def slow_run(*a, **kw):
        assert kw['use_ai'] is True
        entered.set()
        assert finish.wait(5)
    monkeypatch.setattr(launch, 'run', slow_run)
    client = TestClient(api.app)
    key = client.post('/api/assessments', files={'file': ('plant.xlsx', _workbook())}).json()['id']
    try:
        response = client.post(f'/api/assessments/{key}/launch', json={'use_ai': True})
        assert response.status_code == 202 and response.json()['started']
        assert entered.wait(1)
        assert not finish.is_set()  # Save already returned while work remains blocked.
    finally:
        finish.set()
        launch._threads[key].join(timeout=2)
