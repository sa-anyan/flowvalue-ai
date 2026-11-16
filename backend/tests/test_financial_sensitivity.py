"""Independent financial snapshots: no baseline writes or upstream execution."""
import copy
import json
from decimal import Decimal as D

import pytest
from fastapi.testclient import TestClient

from backend.financial_modelling import calculate_financials, snapshot_id
from backend.orchestration.codec import plain
from backend.orchestration.store import Store
from backend.scenarios_and_uncertainty.financial_sensitivity import baseline, preview, save
from backend.tests.test_financial_modelling import fixture


def study(store):
    inputs = fixture(life=10,revenue=100)
    result = calculate_financials(inputs)
    assert not result.issues
    state = {'running':False,'plan':{'operating_economics':{'financial':{'tax_rate':0.99,'discount_rate':0.99}}},
             'results':{'stages':{'financial':{'result':plain(result),'issues':['run OPEX']},
                                   'opex':{'result':{'fixed':123}},'capex':{'result':{'capital':456}},'revenue':{'result':{'annual':789}}}},
             'stage_runs':{'opex':{'status':'stale'},'financial':{'status':'ready'}},
             'stage_outputs':{'financial':{'financial_inputs':plain(inputs)}}}
    return store.create(state,b'unchanged workbook'),inputs


def metric(result,key): return dict(result.metrics)[key].value


def test_preview_changes_tax_and_preserves_every_original_upstream_and_state(tmp_path):
    store=Store(tmp_path/'a.db')
    state,inputs=study(store)
    original=copy.deepcopy(store.get(state['id']))
    base=baseline(state)
    assert D(base['policy']['tax_rate']) == D('.25')  # Actual calculation, not stale edited plan .99.
    result=save(store,state['id'],{'tax_rate':0.5},base['baseline_snapshot_id'])
    assert store.get(state['id']) == original
    case=store.load(result['version_id'])
    assert case['financial_sensitivity']['baseline_id'] == state['id']
    assert case['results']['stages']['opex'] == original['results']['stages']['opex']
    assert case['results']['stages']['capex'] == original['results']['stages']['capex']
    assert case['results']['stages']['revenue'] == original['results']['stages']['revenue']
    scenario,calculated=preview(state,{'tax_rate':0.5},snapshot_id(inputs))
    assert scenario.operations == inputs.operations
    assert scenario.capital == inputs.capital
    assert scenario.upstream_snapshots_json == inputs.upstream_snapshots_json
    assert metric(calculated,'project_npv') < metric(calculate_financials(inputs),'project_npv')
    restored=baseline(store.get(state['id']))
    assert restored == base


@pytest.mark.parametrize('overrides',[{'tax_rate':True},{'tax_rate':2},{'discount_rate':-1},{'closure_allowance':'NaN'},
                                      {'tax_rate':'bad'},{'depreciation_years':1.5},{'depreciation_years':0},{'opex':100}])
def test_invalid_overrides_do_not_save_or_change_baseline(tmp_path,overrides):
    store=Store(tmp_path/'b.db'); state,inputs=study(store)
    with pytest.raises(ValueError): save(store,state['id'],overrides,snapshot_id(inputs))
    assert store.get(state['id']) == state
    assert not store.all_versions()


def test_all_exposed_levers_use_canonical_financial_engine_and_keep_original(tmp_path):
    store=Store(tmp_path/'c.db');state,inputs=study(store)
    overrides={'discount_rate':0.15,'tax_rate':0.3,'depreciation_years':4,'salvage_fraction':0.1,
               'working_capital_recovery_fraction':0.5,'closure_allowance':20}
    scenario,result=preview(state,overrides,snapshot_id(inputs))
    assert not result.issues
    assert scenario.assumptions.project_discount_rate.value == D('.15')
    assert scenario.assumptions.tax.annual_rates[0][1].value == D('.3')
    assert scenario.capital[0].depreciation.life == 4
    assert scenario.capital[0].disposal_proceeds.amount == D('10')
    assert scenario.assumptions.working_capital.recovery_fraction.value == D('.5')
    assert scenario.assumptions.closure_cost.amount == D('20')
    assert plain(result) == plain(calculate_financials(scenario))
    assert store.get(state['id']) == state


def test_snapshot_mismatch_is_rejected(tmp_path):
    store=Store(tmp_path/'d.db');state,_=study(store)
    with pytest.raises(ValueError,match='baseline changed'):
        save(store,state['id'],{'tax_rate':0.3},'0'*64)
    assert not store.all_versions()


def test_http_scenario_is_independent_of_stale_opex_and_revenue(tmp_path,monkeypatch):
    import backend.api.app as api
    store=Store(tmp_path/'e.db');state,_=study(store)
    monkeypatch.setattr(api,'store',store)
    http=TestClient(api.app)
    base=http.get(f"/api/assessments/{state['id']}/financial-sensitivity").json()
    response=http.post(f"/api/assessments/{state['id']}/financial-sensitivity",json={
        'baseline_snapshot_id':base['baseline_snapshot_id'],'overrides':{'tax_rate':0.35}})
    assert response.status_code == 200,response.text
    assert response.json()['result']['ledger']
    assert store.get(state['id']) == state


def test_cloud_snapshot_save_checks_owner_access_before_inserting(monkeypatch):
    from backend.cloud.store import CloudStore
    store=CloudStore('https://example.supabase.co','public','caller-token','owner')
    calls=[]
    monkeypatch.setattr(store,'get',lambda key: calls.append(('get',key)) or {'id':key})
    monkeypatch.setattr(store,'request',lambda table,method='GET',**kw: calls.append((table,method,kw)))
    store.version('study','Scenario',snapshot={'id':'study','running':False,'results':{'independent':True}})
    assert calls[0] == ('get','study')
    assert len(calls)==2
    assert calls[1][0:2] == ('versions','POST')
    assert calls[1][2]['data']['owner_id']=='owner'
    with pytest.raises(ValueError,match='belong'):
        store.version('study','Wrong',snapshot={'id':'other'})
    assert len(calls)==3  # Only the access check, no insert.
    def denied(key): raise KeyError('not owned')
    monkeypatch.setattr(store,'get',denied)
    with pytest.raises(KeyError): store.version('other','Denied',snapshot={'id':'other'})
    assert len(calls)==3
