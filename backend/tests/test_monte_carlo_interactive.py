"""200-draw analyst studies: exact replay, configuration lineage and access isolation."""
import copy
import io
import json

import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook
from pydantic import ValidationError

from backend.tests.test_monte_carlo import complete_state
from backend.scenarios_and_uncertainty.monte_carlo.discovery import discover
from backend.scenarios_and_uncertainty.monte_carlo.engine import simulate, evaluate
from backend.scenarios_and_uncertainty.monte_carlo.models import Settings
from backend.scenarios_and_uncertainty.monte_carlo.inspection import inspect_run, run_index
from backend.scenarios_and_uncertainty.monte_carlo.exports import export
from backend.orchestration.store import Store


@pytest.fixture(scope='module')
def simulation():
    state=complete_state()
    settings=Settings.model_validate(discover(state)['settings'])
    price=next(p for p in settings.parameters if p.targets[0]==['equipment',0,'manual_price','amount'])
    price.enabled=True
    price.minimum=8000;price.mode=10000;price.maximum=12000
    price.source='Synthetic purchase price range'
    price.rationale='Synthetic analyst stress range, not a measured probability model'
    settings.parameters=[price]
    return state,settings,simulate(state,settings)


@pytest.mark.parametrize('count',[0,1,199,201,1000,5000,10000])
def test_only_200_variations_can_be_requested(count):
    assert Settings().iterations==200
    with pytest.raises(ValidationError): Settings(iterations=count)


def test_configuration_replays_canonical_outputs_and_keeps_fixed_inputs(simulation):
    state,settings,result=simulation
    before=copy.deepcopy(result)
    original=copy.deepcopy(state)
    assert len(result['runs'])==200
    for i in (0,99,199):
        inspected=inspect_run(result,i)
        config=inspected['configuration']
        assert config['fingerprint_verified'] is True
        plan=config['plan']
        assert plan['equipment'][0]['manual_price']['amount']==inspected['samples'][settings.parameters[0].id]
        assert plan['capex']==result['effective_fixed_plan']['capex']
        replay=evaluate(config['source_report'],config['process_description'],copy.deepcopy(plan),[])
        assert replay['metrics']==inspected['metrics']
        assert replay['cash_flow']==inspected['cash_flow']
        assert config['parameters'][0]['values'][0]['baseline']==10000
    assert result==before and state==original


def test_tampered_sample_is_not_presented_as_the_original_configuration(simulation):
    _,settings,result=simulation
    tampered=copy.deepcopy(result)
    tampered['runs'][0]['samples'][settings.parameters[0].id]+=1
    with pytest.raises(ValueError,match='fingerprint'): inspect_run(tampered,0)


def test_sensitivity_groups_link_to_exact_eligible_runs(simulation):
    _,settings,result=simulation
    driver=next(d for d in result['summary']['drivers'] if d['metric']=='capex')
    assert driver['low_runs'] and driver['high_runs']
    assert not set(driver['low_runs'])&set(driver['high_runs'])
    p=settings.parameters[0].id
    assert max(result['runs'][i]['samples'][p] for i in driver['low_runs']) < min(result['runs'][i]['samples'][p] for i in driver['high_runs'])
    index=run_index(result)
    assert len(index)==200 and index[0]['configuration_hash']==result['runs'][0]['configuration_hash']
    assert all('capex' in index[i]['metric_eligible'] for i in driver['low_runs'])


def test_exports_contain_reproducible_inputs_and_full_configuration(simulation):
    _,_,result=simulation
    data,mime=export(result,'json')
    restored=json.loads(data)
    assert mime=='application/json'
    assert inspect_run(restored,199)['configuration']['hash']==inspect_run(result,199)['configuration']['hash']
    data,_=export(result,'xlsx')
    book=load_workbook(io.BytesIO(data),read_only=True)
    config_rows=list(book['Configurations'].values)
    assert config_rows[0]==('run','chunk','json')
    payload=''.join(row[2] for row in config_rows[1:] if row[0]==0)
    assert json.loads(payload)['plan']==inspect_run(result,0)['configuration']['plan']


def test_configuration_api_is_owner_scoped_and_does_not_write_baseline(tmp_path,monkeypatch,simulation):
    import backend.api.app as api
    state,settings,result=simulation
    store=Store(tmp_path/'mc.db')
    baseline=store.create(state,b'original')
    snapshot=store.create({'kind':'monte_carlo_snapshot','assessment':baseline},b'')
    saved=store.create({'kind':'monte_carlo_results','source_job':'pending','result':result},b'')
    job=store.create({'kind':'monte_carlo_job','parent_assessment':baseline['id'],'snapshot_id':snapshot['id'],'result_id':saved['id'],'settings':settings.model_dump(),'status':'complete'},b'')
    saved['source_job']=job['id'];store.put(saved,saved['revision'])
    monkeypatch.setattr(api,'store',store)
    http=TestClient(api.app)
    path=f"/api/assessments/{baseline['id']}/monte-carlo/jobs/{job['id']}/runs"
    assert len(http.get(path).json())==200
    response=http.get(path+'/0?download=true')
    assert response.status_code==200
    assert 'attachment' in response.headers['Content-Disposition']
    assert response.json()['configuration']['fingerprint_verified']
    assert http.get(path+'/200').status_code==404
    assert http.get(path.replace(baseline['id'],'not-the-owner')+'/0').status_code==404
    assert store.get(baseline['id'])==baseline


def test_calculation_rows_reconcile_and_keep_non_cash_costs_distinct(simulation):
    from decimal import Decimal
    _, _, result = simulation
    for index in (0, 99, 199):
        run = result['runs'][index]
        trace = run['calculation_trace']
        capex = trace['capex']
        assert Decimal(capex['fixed_capital']) + Decimal(capex['startup_expenses']) + Decimal(capex['working_capital']) == Decimal(capex['total_capex'])
        opex = trace['opex']
        cash = sum((Decimal(line['amount']) for line in opex['first_year_lines'] if line['accounting'] == 'cash' and line['scope'] == 'recurring'), Decimal(0))
        assert cash == Decimal(opex['first_year_cash_opex'])
        assert float(capex['total_capex']) == run['metrics']['capex']
        assert float(opex['first_year_cash_opex']) == run['metrics']['opex']
        assert trace['equipment']['equipment'][0]['price_coverage'] == 'priced'


def test_historical_breakdown_replay_is_verified_and_read_only(simulation):
    from backend.scenarios_and_uncertainty.monte_carlo.inspection import inspect_calculations
    _, _, result = simulation
    historical = copy.deepcopy(result)
    expected = historical['runs'][0].pop('calculation_trace')
    before = copy.deepcopy(historical)
    inspected = inspect_calculations(historical, 0)
    assert inspected['trace_verification']['status'] == 'replayed'
    assert inspected['calculation_trace'] == expected
    assert historical == before
    # Fingerprinted inputs alone cannot validate outputs from a different engine.
    historical['runs'][0]['metrics']['capex'] += 1
    inspected = inspect_calculations(historical, 0)
    assert inspected['trace_verification']['status'] == 'mismatch'
    assert 'calculation_trace' not in inspected
