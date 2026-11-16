"""Bounded independent AI requests; callers validate/apply in source order."""
from concurrent.futures import Future, ThreadPoolExecutor
from contextvars import copy_context


def ordered_prefetch(requests, fetch, workers=3):
    requests = list(requests)
    if len(requests) <= 1:
        for request in requests:
            future = Future()
            try:
                future.set_result(fetch(request))
            except Exception as exc:
                future.set_exception(exc)
            yield request, future
        return
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix='equipment-ai') as pool:
        futures = [pool.submit(copy_context().run, fetch, request) for request in requests]
        for request, future in zip(requests, futures):
            yield request, future
