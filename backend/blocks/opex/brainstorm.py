"""Background OPEX brainstorm: the AI proposes OPEX inputs while the user works.

Starts as soon as the engineering data is approved (and again whenever the
approved data changes), off the stage lock, so the user never waits for it and
never faces an empty OPEX page. The AI proposes materials, utilities, labour
roles and headcounts, other expenses and Garrett factors; Python still does all
arithmetic when the OPEX stage runs.

Ownership rules (same as the reference defaults):

* a field that is empty is filled with the AI proposal (origin "ai");
* a value owned by the reference defaults may be refined by the AI, and an AI
  factor is kept only inside its printed reference range;
* anything the user entered, selected or overrode, and anything an earlier AI
  proposal wrote, is never replaced; a locked baseline is never touched.

The result is written only while no stage is running (the caller's stage lock
is held for that short write), so a background write can never invalidate a
running calculation.
"""

import copy
import threading
from contextvars import copy_context
from datetime import datetime, timezone
from decimal import Decimal

VERSION = "opex-brainstorm-1"
STATUS = "AI proposal — needs review"
FIELDS = ("materials", "energy", "labour", "additional_expenses", "garrett_factors")

_live = {}  # key -> {"status": "running", "started_at": ..., "fingerprint": ...}
_guard = threading.Lock()
# The API replaces this with its stage lock so results are written only between stages.
STAGE_LOCK = threading.Lock()


def _now():
    return datetime.now(timezone.utc).isoformat()


def _recent(stamp, seconds=20):
    try:
        return (datetime.now(timezone.utc) - datetime.fromisoformat(stamp)).total_seconds() < seconds
    except (TypeError, ValueError):
        return False


def _report(state):
    return ((state.get("stage_outputs") or {}).get("engineering_data") or {}).get("report") \
        or state.get("scoped_report") or state.get("effective_report") or (state.get("parsed") or {}).get("report") or {}


def fingerprint(state):
    from backend.blocks.execution import _digest

    return _digest({"version": VERSION, "report": _report(state), "description": state.get("description", "")})


def ai_available():
    try:
        from backend.orchestration.provider import EngineeringProvider

        EngineeringProvider()
        return True
    except Exception:
        return False


def wanted(state):
    """True when approved data has no brainstorm for its current fingerprint."""
    from backend.blocks.stage_workflow import approved

    if not approved(state) or "operating_economics" in (state.get("locked") or []):
        return False
    return (state.get("opex_brainstorm") or {}).get("fingerprint") != fingerprint(state)


def status(key, state):
    """Saved brainstorm record, overlaid with a live 'running' status."""
    live = _live.get(key)
    saved = dict(state.get("opex_brainstorm") or {})
    if live and live.get("fingerprint") != saved.get("fingerprint"):
        if live.get("status") == "saved":
            # Saved just after this state was read: report "running" briefly so
            # the page reads the study once more and picks up the proposals.
            return {**saved, **live, "status": "running"} if _recent(live.get("finished_at")) else saved or None
        return {**saved, **live}
    return saved or None


# --- merge -----------------------------------------------------------------

def _in_range(category, fraction):
    from backend.opex.reference_library import get_ranges

    rows = get_ranges(category, "garrett")
    if not rows:
        return False
    try:
        value = Decimal(str(fraction))
    except Exception:
        return False
    return any(Decimal(str(r["low"])) <= value <= Decimal(str(r["high"])) for r in rows)


def _ai(item):
    return dict(copy.deepcopy(item), origin="ai", status=STATUS)


def _replaceable(entry):
    return not entry or (isinstance(entry, dict) and entry.get("origin") == "reference_default")


def _refresh_questions(config):
    """Drop reference-default questions the AI has now answered."""
    record = config.get("reference_defaults")
    if not isinstance(record, dict):
        return
    items = {i.get("id"): i for root in ("energy", "materials") for i in config.get(root) or [] if isinstance(i, dict)}
    kept = []
    for q in record.get("questions") or []:
        ident = q.get("id")
        if ident == "operating_labor":
            if not config.get("labour"):
                kept.append(q)
        elif ident in items:
            item = items[ident]
            if item.get("tariff_per_kwh" if "tariff_per_kwh" in item else "unit_price") is None:
                kept.append(q)
        elif ident == "ref-specific-energy":
            if not config.get("energy"):
                kept.append(q)
        else:
            kept.append(q)
    record["questions"] = kept


def merge(config, proposed):
    """Fill gaps and refine reference defaults with the AI proposal. Returns (config, added)."""
    config = copy.deepcopy(config or {})
    owners = config.setdefault("value_owners", {})
    added = []
    for field in FIELDS:
        value = proposed.get(field)
        if not value:
            continue
        current = config.get(field)
        if field == "garrett_factors" and isinstance(value, dict):
            factors = copy.deepcopy(current) if isinstance(current, dict) else {}
            for category, choice in value.items():
                if not isinstance(choice, dict) or not _replaceable(factors.get(category)):
                    continue
                documented = choice.get("override") and choice.get("override_reason")
                if not documented and not _in_range(category, choice.get("fraction")):
                    continue  # the AI may refine only inside the printed range
                factors[category] = _ai(choice)
                owners[f"garrett_factors.{category}"] = "ai"
                added.append(f"garrett_factors.{category}")
            config[field] = factors
        elif isinstance(value, list):
            items = current if isinstance(current, list) else []
            if items and not all(isinstance(i, dict) and i.get("origin") == "reference_default" for i in items):
                continue  # the user or an earlier AI proposal owns this list
            if items:
                # Keep reference-default items the AI did not cover (e.g. a feed).
                covered = {i.get("stream_key") for i in value if isinstance(i, dict)} - {None}
                keep = [i for i in items if i.get("stream_key") not in covered or not i.get("stream_key")]
                if field == "energy":
                    keep = [i for i in keep if i.get("equipment_key") not in {v.get("equipment_key") for v in value}]
            else:
                keep = []
            new = [_ai(i) for i in value if isinstance(i, dict)]
            config[field] = keep + new
            for item in new:
                owners[f"{field}.{item.get('id')}"] = "ai"
                added.append(f"{field}.{item.get('id')}")
    for field in ("price_basis", "operating", "assumption_date", "methodology"):
        if not config.get(field) and proposed.get(field):
            config[field] = copy.deepcopy(proposed[field])
    _refresh_questions(config)
    return config, added


# --- background job ----------------------------------------------------------

def _propose(state, store, provider):
    from backend.blocks.models import Context
    from backend.blocks.shared import proposal

    engineering = (state.get("stage_outputs") or {}).get("engineering_data") or {}
    ctx = Context(copy.deepcopy(state), _report(state), {"engineering_data": engineering}, store, None, provider, True)
    sections = ("revenue", "opex")
    values, meta = proposal(ctx, sections, basis_only=True, allow_missing_opex=True)
    return values.get("operating_economics") or {}, meta


def save(store, key, record, stage_lock=None):
    """Write the result while no stage runs; merge into the OPEX inputs."""
    with stage_lock or STAGE_LOCK:
        for attempt in range(3):
            state = store.get(key)
            if record.get("fingerprint") != fingerprint(state):
                return state  # the approved data changed meanwhile; a new run follows
            added = []
            if record.get("status") == "ready" and "operating_economics" not in (state.get("locked") or []):
                plan = state.setdefault("plan", {})
                plan["operating_economics"], added = merge(plan.get("operating_economics"), record.get("proposal") or {})
            state["opex_brainstorm"] = {**record, "added": added}
            try:
                return store.put(state, state["revision"])
            except ValueError:
                if attempt == 2:
                    raise  # an edit outside the stage lock won the race three times


def run(store, key, stage_lock=None, provider=None):
    state = store.get(key)
    record = {"version": VERSION, "fingerprint": fingerprint(state), "started_at": _now()}
    try:
        from backend.orchestration.provider import EngineeringProvider

        proposed, meta = _propose(state, store, provider or EngineeringProvider())
        keep = {k: proposed[k] for k in (*FIELDS, "price_basis", "operating", "scope_notes") if k in proposed}
        record.update(status="ready", proposal=keep, model=(meta or {}).get("model"), finished_at=_now())
    except Exception as exc:  # recorded for the page; reference defaults still apply
        record.update(status="failed", error=str(exc)[:300], finished_at=_now())
    # The live entry is never simply dropped: a reader that loaded the study just
    # before the save must still see "running" (and poll again), not nothing.
    outcome = {"status": "saved"}
    try:
        state = save(store, key, record, stage_lock)
        if (state.get("opex_brainstorm") or {}).get("fingerprint") != record["fingerprint"]:
            outcome = {"status": "superseded"}  # the approved data changed meanwhile
        return state
    except Exception as exc:
        outcome = {"status": "failed", "error": "Could not save AI proposals: " + str(exc)[:200]}
        raise
    finally:
        with _guard:
            if (_live.get(key) or {}).get("fingerprint") == record["fingerprint"]:
                _live[key] = {**_live[key], **outcome, "finished_at": _now()}


def kick(store, key, stage_lock=None, provider=None, *, executor=None):
    """Start a brainstorm if the approved data has none; never blocks the caller."""
    try:
        state = store.get(key)
    except Exception:
        return False
    if provider is None and not ai_available():
        return False
    if not wanted(state):
        return False
    stamp = fingerprint(state)
    with _guard:
        if (_live.get(key) or {}).get("status") == "running":
            return False  # one brainstorm per study at a time
        _live[key] = {"status": "running", "fingerprint": stamp, "started_at": _now(), "version": VERSION}
    context = copy_context()

    def work():
        try:
            run(store, key, stage_lock, provider)
        except Exception:
            pass  # recorded in the live status for the page

    if executor is not None:
        executor.submit(context.run, work)
    else:
        threading.Thread(target=context.run, args=(work,), name=f"opex-brainstorm-{key[:8]}", daemon=True).start()
    return True
