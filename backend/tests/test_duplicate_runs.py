"""Repeated UI requests join an existing job without changing calculation inputs."""
import copy
import threading

import pytest
from fastapi.testclient import TestClient
import backend.api.app as api
from backend.tests.test_opex_brainstorm import _extracted
from backend.blocks.stage_workflow import approve


@pytest.mark.parametrize('first,second', [('capex','capex'),('capex','opex'),('equipment','equipment')])
def test_duplicate_requests_have_one_job_and_one_checkpoint(tmp_path,monkeypatch,first,second):
    monkeypatch.setattr('backend.blocks.opex.brainstorm.ai_available',lambda:False)
    store,key=_extracted(tmp_path)
    state=store.get(key);approve(store,key,state['revision'])
    jobs=[]
    class Held:
        def submit(self,fn,*args):jobs.append((fn,args))
    gate=threading.Lock()
    monkeypatch.setattr(api,'store',store)
    monkeypatch.setattr(api,'lock',gate)
    monkeypatch.setattr(api,'executor',Held())
    client=TestClient(api.app)
    try:
        a=client.post(f'/api/assessments/{key}/stages/{first}/run',json={'use_ai':False})
        saved=copy.deepcopy(store.get(key));versions=store.versions(key)
        b=client.post(f'/api/assessments/{key}/stages/{second}/run',json={'use_ai':False})
        assert a.status_code==b.status_code==202
        assert b.json()['already_running'] is True
        assert len(jobs)==1 and store.get(key)==saved and store.versions(key)==versions
        other=client.post(f'/api/assessments/{key}/stages/financial/run',json={'use_ai':False})
        assert other.status_code==409 and len(jobs)==1
    finally:
        if gate.locked():gate.release()
