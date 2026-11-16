"""Current-execution AI memoization, never a prior study's response cache."""

import copy
import os
from threading import RLock

from backend.orchestration.store import dump


class RunStore:
    """Delegate study persistence; cache AI responses only within this execution.

    Each run_stage receives a new instance. Identical work within that run can
    reuse its result, but a fresh run/upload never reads persistent ai_cache.
    The wrapper also works with the cloud store without changing its contract.
    """

    def __init__(self, store):
        self._store = store
        self._responses = {}
        self._guard = RLock()

    def __getattr__(self, name):
        return getattr(self._store, name)

    def cached(self, context, compute):
        if os.environ.get("FLOWVALUE_AI_RESPONSE_CACHE", "true").lower().strip() in {"false", "0", "off"}:
            return compute(), False
        key = dump(context)
        with self._guard:
            if key in self._responses:
                value = copy.deepcopy(self._responses[key])
                from backend.orchestration.ai_audit import record

                record("cache", model=os.environ.get("OPENAI_MODEL") or None,
                       context=context, response=value, cached=True)
                return value, True
        value = compute()
        with self._guard:
            self._responses[key] = copy.deepcopy(value)
        return value, False
