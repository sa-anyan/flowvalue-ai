"""Destructive reset is verified only against disposable temporary databases."""
import pytest
from fastapi.testclient import TestClient

import backend.api.app as api
from backend.orchestration.store import Store
from backend.tests.test_autopilot import _workbook


@pytest.fixture
def client(tmp_path, monkeypatch):
    store = Store(tmp_path/'reset.db')
    monkeypatch.setattr(api, 'store', store)
    monkeypatch.setattr(api, 'CLOUD', False)
    # Finished test-worker registries are isolated from other test suites.
    from backend.blocks import launch, analyst, progress
    from backend.blocks.opex import brainstorm
    for module, name in [(launch,'_threads'),(launch,'_inbox'),(analyst,'_live'),(progress,'_runs'),(brainstorm,'_live')]:
        monkeypatch.setattr(module, name, {})
    monkeypatch.setattr(launch, '_delivery', set())
    return TestClient(api.app), store


def seed(store):
    state = store.create({'filename':'plant.xlsx','running':False,'plan':{}}, _workbook())
    store.version(state['id'], 'Saved baseline')
    with store.db() as db: db.execute('INSERT INTO ai_cache VALUES (?,?)', ('old','{}'))
    return state


def test_reset_clears_history_and_accepts_a_fresh_upload(client):
    http, store = client
    state = seed(store)
    response = http.post('/api/assessments/reset', json={'confirm': True})
    assert response.status_code == 200
    assert response.json()['cleared'] == {'assessments':1,'versions':1,'ai_cache':1}
    assert store.all_versions() == []
    with pytest.raises(KeyError): store.get(state['id'])
    with store.db() as db:
        assert db.execute('SELECT count(*) FROM ai_cache').fetchone()[0] == 0
    assert http.post('/api/assessments/reset', json={'confirm':True}).status_code == 200
    new = http.post('/api/assessments', files={'file':('new.xlsx',_workbook())})
    assert new.status_code == 202
    assert new.json()['id'] != state['id']
    assert not store.get(new.json()['id'])['plan'].get('equipment')


@pytest.mark.parametrize('reason',['no_confirmation','cloud','stage_lock','running_state','background'])
def test_reset_refusals_never_partially_delete(client, monkeypatch, reason):
    http, store = client
    state = seed(store)
    payload = {'confirm':True}
    if reason == 'no_confirmation': payload = {'confirm':False}
    if reason == 'cloud': monkeypatch.setattr(api,'CLOUD',True)
    if reason == 'running_state':
        state['running'] = True
        store.put(state,state['revision'])
    if reason == 'background':
        from backend.blocks import analyst
        analyst._live[(state['id'],'capex')] = {'status':'running'}
    if reason == 'stage_lock': api.lock.acquire()
    try:
        response = http.post('/api/assessments/reset',json=payload)
    finally:
        if reason == 'stage_lock': api.lock.release()
    assert response.status_code in {401,403,409,422}
    assert store.get(state['id'])['filename'] == 'plant.xlsx'
    assert len(store.all_versions()) == 1
    with store.db() as db: assert db.execute('SELECT count(*) FROM ai_cache').fetchone()[0] == 1


def test_forced_reset_clears_everything_while_a_calculation_is_running(client):
    """The red Reset works mid-run; the running worker keeps its lock and its later save is dropped."""
    http, store = client
    state = seed(store)
    running = store.get(state['id'])
    running['running'] = True
    store.put(running, running['revision'])
    from backend.blocks import analyst
    analyst._live[('k', 'capex')] = {'status': 'running'}
    assert api.lock.acquire(blocking=False)  # a stage is running
    try:
        assert http.post('/api/assessments/reset', json={'confirm': True}).status_code == 409  # not forced
        response = http.post('/api/assessments/reset', json={'confirm': True, 'force': True})
        assert response.status_code == 200
        assert response.json()['cleared']['assessments'] == 1 and response.json()['cleared']['stopped_running_work']
        with pytest.raises(KeyError): store.get(state['id'])
        assert analyst._live == {}
        assert api.lock.locked()  # still owned by the running stage, not released by reset
        with pytest.raises((KeyError, ValueError)):
            store.put(running, running['revision'])  # the old run's save is dropped, nothing reappears
        assert store.all_versions() == []
    finally:
        api.lock.release()
    fresh = http.post('/api/assessments', files={'file': ('new.xlsx', _workbook())})
    assert fresh.status_code == 202
