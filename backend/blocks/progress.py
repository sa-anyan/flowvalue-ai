"""Live progress of a running stage, kept in memory (never in the saved study).

A stage run sets the current assessment for its thread; long steps report
``step(label, done, total)``. The UI polls ``/api/assessments/{key}/progress``,
which reads this registry without loading the study from the database, so a
progress bar can update every second at no cost. Progress is informational:
it never decides results and is lost on restart (the saved receipt remains).
"""

import contextvars
import threading
import time

_current = contextvars.ContextVar("flowvalue_progress_key", default=None)
_lock = threading.Lock()
_runs = {}
_KEEP_SECONDS = 120


def begin(key, stage):
    """Start tracking; inside an already-tracked run for the same study, only
    the stage name changes and None is returned (the outer run ends it)."""
    if _current.get() == key:
        with _lock:
            if key in _runs:
                _runs[key].update(stage=stage, step="Starting", done=None, total=None, updated=time.time())
        return None
    with _lock:
        _runs[key] = {"stage": stage, "step": "Starting", "done": None, "total": None,
                      "started": time.time(), "updated": time.time(), "finished": None}
    return _current.set(key)


def step(label, done=None, total=None):
    """Report the current step of the running stage (no-op outside a stage run)."""
    key = _current.get()
    if key is None:
        return
    with _lock:
        run = _runs.get(key)
        if run is not None and run["finished"] is None:
            run.update(step=str(label), done=done, total=total, updated=time.time())


def end(key, token=None, status="finished"):
    """Finish tracking. A nested run (token None) leaves the outer run open."""
    if token is None and _current.get() == key:
        return
    with _lock:
        run = _runs.get(key)
        if run is not None:
            run.update(finished=time.time(), step=status)
    if token is not None:
        _current.reset(token)


def get(key):
    now = time.time()
    with _lock:
        for k in [k for k, r in _runs.items() if r["finished"] and now - r["finished"] > _KEEP_SECONDS]:
            del _runs[k]
        run = dict(_runs.get(key) or {})
    if not run:
        return {"running": False}
    return {
        "running": run["finished"] is None,
        "stage": run["stage"],
        "step": run["step"],
        "done": run["done"],
        "total": run["total"],
        "elapsed_seconds": round((run["finished"] or now) - run["started"], 1),
    }
