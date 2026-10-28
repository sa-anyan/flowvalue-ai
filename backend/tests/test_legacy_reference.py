"""Reference snapshots retain source values and never become engine results."""
from fastapi.testclient import TestClient

from app.main import app, demo_assessment

client=TestClient(app)
def reference():
    p=demo_assessment().model_dump(mode="json")
    p['legacy_reference']={'schema_version':'flowvalue-legacy-reference-v1','source_name':'Synthetic reference.xlsx','source_sha256':'a'*64,'currency':'GBP','sheets':[{'name':'Capex','cells':{'B3':{'value':12345.67,'cached':True},'B4':{'value':0,'cached':False}}}]}
    return p

def test_reference_validation_preserves_original_currency_zero_and_cached_results(monkeypatch):
    monkeypatch.setenv('REQUIRE_AUTH','false')
    r=client.post('/api/projects/validate-reference',json=reference())
    assert r.status_code==200
    snapshot=r.json()['legacy_reference']
    assert snapshot['currency']=='GBP'
    assert snapshot['sheets'][0]['cells']['B3']['value']==12345.67
    assert snapshot['sheets'][0]['cells']['B4']['value']==0

def test_reference_is_rejected_as_a_calculated_assessment_or_export(monkeypatch):
    monkeypatch.setenv('REQUIRE_AUTH','false')
    for route in ['/api/assessment','/api/export/excel','/api/export/pdf']:
        r=client.post(route,json=reference())
        assert r.status_code==409

def test_source_cells_are_data_only_with_unique_sheets_and_valid_addresses(monkeypatch):
    monkeypatch.setenv('REQUIRE_AUTH','false')
    p=reference();p['legacy_reference']['sheets'][0]['cells']['B3']['formula']='=ANYTHING()'
    assert client.post('/api/projects/validate-reference',json=p).status_code==422
    p=reference();p['legacy_reference']['sheets'].append(p['legacy_reference']['sheets'][0])
    assert client.post('/api/projects/validate-reference',json=p).status_code==422
    p=reference();p['legacy_reference']['sheets'][0]['cells']['bad address']={'value':1}
    assert client.post('/api/projects/validate-reference',json=p).status_code==422

def test_reference_save_keeps_owner_scoped_snapshot_without_running_dcf(monkeypatch):
    from app.auth import authenticated_user
    user={'id':'00000000-0000-4000-8000-00000000a001'}
    async def auth():return user
    writes=[]
    async def rest(request,method,path,*,body=None):
        writes.append((method,path,body))
        return [{'id':'00000000-0000-4000-8000-00000000a002','user_id':user['id'],'revision':1}]
    monkeypatch.setenv('REQUIRE_AUTH','false')
    monkeypatch.setattr('app.main.project_rest',rest)
    app.dependency_overrides[authenticated_user]=auth
    try:
        response=client.post('/api/projects',json={'name':'Synthetic reference','project':reference(),'streams':[]})
        assert response.status_code==200
        assert writes[0][1]=='rpc/save_project_version'
        saved=writes[0][2]['p_payload']['project']['legacy_reference']
        assert saved['currency']=='GBP'
        assert saved['sheets'][0]['cells']['B3']['value']==12345.67
    finally:app.dependency_overrides.clear()
