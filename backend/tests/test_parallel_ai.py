"""Real concurrent execution with deterministic consumption and isolated failures."""
import contextvars
import threading
from backend.orchestration.parallel_ai import ordered_prefetch


def test_independent_calls_overlap_but_results_remain_in_input_order():
    lock=threading.Lock();gate=threading.Event();active=0;peak=0
    scope=contextvars.ContextVar('test_scope',default=None);scope.set('this-run')
    def fetch(index):
        nonlocal active,peak
        assert scope.get()=='this-run'
        with lock:
            active+=1;peak=max(peak,active)
            if active==3:gate.set()
        assert gate.wait(3), 'independent requests did not overlap'
        with lock:active-=1
        if index==2:raise ValueError('isolated failure')
        return index*2
    output=[]
    for request,future in ordered_prefetch(range(6),fetch):
        try:output.append((request,future.result()))
        except ValueError:output.append((request,'failed'))
    assert [i for i,_ in output]==list(range(6))
    assert output[2]==(2,'failed') and output[5]==(5,10)
    assert peak==3
