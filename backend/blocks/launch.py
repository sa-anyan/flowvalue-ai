"""Save & go: one Save on Entry runs the whole study in the background.

After the user uploads the M&E balance and presses Save, this chain runs on
its own thread, waiting its turn for the study lock instead of refusing:

1. read the workbook with Python (seconds) so the revenue form can show the
   streams at once;
2. with AI ticked: the AI workbook review (the background analyst starts as
   soon as the workbook is readable);
3. a provisional approval of the extracted data, recorded and listed for review
   (the user reviews it later from the Equipment page);
4. instant model picks for unmatched items, then equipment (AI sizing when
   ticked), CAPEX, revenue, OPEX and financial with Python.

Meanwhile the user defines revenue. Their saves never wait for the background
run: each is checked at once, held in a small per-study inbox and applied
between steps. If revenue arrives after the revenue step ran, revenue, OPEX
and financial are calculated again at the end.
"""

import copy
import threading
from contextvars import copy_context
from datetime import datetime, timezone

VERSION = "save-and-go-1"
STAGE_LOCK = threading.Lock()  # replaced by the API's stage lock
_guard = threading.Lock()
_inbox = {}  # study key -> {kind: payload}, latest wins per kind
_threads = {}


def _now():
    return datetime.now(timezone.utc).isoformat()


# --- inbox: user inputs that arrive while the background run holds the study ---

def put(key, kind, payload):
    with _guard:
        _inbox.setdefault(key, {})[kind] = copy.deepcopy(payload)


def pending(key):
    with _guard:
        return sorted(_inbox.get(key) or {})


def _apply_revenue(store, key, payload):
    from backend.revenue.setup import apply

    state = store.get(key)
    out = apply(store, key, state["revision"], payload)
    if out["questions"]:
        state = store.get(key)
        state["revenue_questions"] = list(out["questions"])
        store.put(state, state["revision"])


def _apply_context(store, key, payload):
    state = store.get(key)
    state["project_context"] = payload
    store.put(state, state["revision"])
    from .analyst import kick

    kick(store, key)


HANDLERS = {"revenue_setup": _apply_revenue, "project_context": _apply_context}


def drain(store, key):
    """Apply held inputs now (caller holds the study lock). Returns the kinds applied."""
    with _guard:
        items = _inbox.pop(key, {})
    applied = []
    for kind, payload in items.items():
        try:
            HANDLERS[kind](store, key, payload)
            applied.append(kind)
        except Exception as exc:  # recorded for the page; never stops the run
            state = store.get(key)
            state.setdefault("inbox_errors", []).append({"kind": kind, "error": str(exc)[:300], "at": _now()})
            store.put(state, state["revision"])
    return applied


# --- the chain ------------------------------------------------------------------

def _mark(store, key, **fields):
    state = store.get(key)
    state["launch"] = {**(state.get("launch") or {}), **fields}
    return store.put(state, state["revision"])


def run(store, key, *, use_ai=False, provider=None):
    """The whole background run for one study (caller holds the study lock)."""
    from .autopilot import _pick_models
    from .execution import fresh, run_stage
    from .stage_workflow import approve, approved

    _mark(store, key, status="running", version=VERSION, use_ai=use_ai, started_at=_now(), step="reading")
    try:
        state = run_stage(store, key, "engineering_data", use_ai=False, provider=provider)
        if not fresh(state, "engineering_data"):
            return _mark(store, key, status="needs_input", step="reading", finished_at=_now(),
                         message="The workbook could not be read; check it on the Entry page.")
        if use_ai:
            _mark(store, key, step="ai_review")
            state = run_stage(store, key, "engineering_data", use_ai=True, provider=provider)
        drain(store, key)
        state = store.get(key)
        if not approved(state):
            state = approve(store, key, state["revision"])
            state["engineering_approval"]["by"] = VERSION
            state["engineering_approval"]["provisional"] = True
            state = store.put(state, state["revision"])
        state = store.get(key)
        _pick_models(state)
        store.put(state, state["revision"])
        late = False  # revenue applied after the revenue step had already run
        for stage in ("equipment", "capex", "revenue", "opex", "financial"):
            _mark(store, key, step=stage)
            if "revenue_setup" in drain(store, key) and stage in ("opex", "financial"):
                late = True
            run_stage(store, key, stage, use_ai=use_ai and stage == "equipment", provider=provider)
        if "revenue_setup" in drain(store, key) or late:
            for stage in ("revenue", "opex", "financial"):  # revenue arrived late
                _mark(store, key, step=stage)
                run_stage(store, key, stage, use_ai=False, provider=provider)
        return _mark(store, key, status="finished", step="done", finished_at=_now())
    except Exception as exc:
        state = store.get(key)
        state["running"] = False
        state.pop("queued_stage", None)
        state["launch"] = {**(state.get("launch") or {}), "status": "failed", "error": str(exc)[:300],
                           "finished_at": _now()}
        store.put(state, state["revision"])
        raise


def start(store, key, *, use_ai=False, provider=None, stage_lock=None):
    """Start the chain on its own thread; it waits for the study lock, never refuses."""
    lock = stage_lock or STAGE_LOCK
    with _guard:
        thread = _threads.get(key)
        if thread and thread.is_alive():
            return False
    # A new study is idle, so this small write cannot race a run on it; the
    # request never waits for another study's run.
    state = store.get(key)
    if state.get("running"):
        return False
    state["launch"] = {"status": "queued", "version": VERSION, "use_ai": use_ai, "queued_at": _now(), "step": "waiting"}
    store.put(state, state["revision"])

    def work():
        with lock:
            try:
                run(store, key, use_ai=use_ai, provider=provider)
            except Exception:
                pass  # recorded on the study for the page

    thread = threading.Thread(target=copy_context().run, args=(work,), name=f"save-and-go-{key[:8]}", daemon=True)
    with _guard:
        _threads[key] = thread
    thread.start()
    return True


def running(key):
    with _guard:
        thread = _threads.get(key)
        return bool(thread and thread.is_alive())
