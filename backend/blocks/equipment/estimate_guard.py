"""Keep AI sizing estimates stable from run to run.

The AI may re-estimate an item's sizing inputs on a later run (a pricing repair,
another model, a cleared row). Without a guard the same M&E can give 15.6 m3
on one run and 156 m3 on the next. This module anchors each item's first
AI-derived size and measures every later AI size against it:

* same M&E basis, same size unit, drift within ``TOLERANCE``: kept (stable);
* same basis but drift above ``TOLERANCE``: the anchored estimate is kept and
  the new one is recorded as a proposal for the user to review ("held"), with
  both values and the drift shown; nothing silently jumps;
* the M&E for that item changed, or the size unit changed: legitimate change,
  re-anchored;
* the user entered any sizing input: the user owns it, re-anchored, never held.

When two AI estimates disagree, the AI assumptions they share get their
observed spread recorded as a low/high range, which Monte Carlo then varies.
Python does all arithmetic; this module only compares and restores inputs.
"""

import copy
from datetime import datetime, timezone

TOLERANCE = 0.25  # relative change in size allowed between AI runs
GUARD = "ai_estimate_guard"
LLM = "llm_estimate"


def _now():
    return datetime.now(timezone.utc).isoformat()


def basis(report, key):
    """Digest of what the M&E says about this item and its connected streams."""
    from backend.blocks.execution import _digest

    streams = {c["stream_key"] for c in report.get("connections", []) if c.get("equipment_key") == key}
    keep = ("property", "component", "normalized_value", "normalized_unit")
    values = {
        e["key"]: sorted((tuple(str(v.get(k)) for k in keep) for v in e.get("values", [])))
        for e in report.get("entities", []) if e.get("key") == key or e.get("key") in streams
    }
    return _digest(values)


def owner(row):
    """'user', 'ai' or None for who set this item's sizing inputs."""
    if row.get("manual_price") or row.get("external_quote"):
        return None
    conversion = row.get("unit_conversion") or {}
    if not conversion.get("enabled"):
        return None
    statuses = {p.get("status") for p in (conversion.get("input_provenance") or {}).values() if isinstance(p, dict)}
    if "user_input" in statuses:
        return "user"
    if LLM in statuses or str(conversion.get("origin", "")).startswith("llm"):
        return "ai"
    return None


def _assumptions(conversion):
    return {name: p for name, p in (conversion.get("input_provenance") or {}).items()
            if isinstance(p, dict) and p.get("status") == LLM and isinstance(p.get("value"), (int, float))}


def _widen(conversion, other):
    """Record the spread between two AI estimates as each shared assumption's range."""
    mine = _assumptions(conversion)
    for name, theirs in _assumptions(other).items():
        p = mine.get(name)
        if not p or p["value"] == theirs["value"]:
            continue
        values = [p["value"], theirs["value"]] + [x for x in (p.get("low"), p.get("high")) if isinstance(x, (int, float))]
        p["low"], p["high"] = min(values), max(values)
        p["range_basis"] = "Spread between independent AI estimates for the same M&E (and the AI's stated range)."


def guard(plan, sizes, report):
    """Return (plan, held equipment keys). ``sizes`` are the calculated sizing rows."""
    plan = copy.deepcopy(plan)
    rows = {r.get("equipment_key"): r for r in plan.get("equipment", [])}
    held = []
    for line in sizes or []:
        key = (line.get("parsed_source") or {}).get("equipment_key")
        row = rows.get(key)
        size, unit = line.get("size"), line.get("size_unit")
        if row is None or not isinstance(size, (int, float)) or size <= 0:
            continue
        who = owner(row)
        if who is None:
            continue
        state = copy.deepcopy(row.get(GUARD) or {})
        current = {"size": float(size), "size_unit": unit, "basis": basis(report, key),
                   "conversion": copy.deepcopy(row["unit_conversion"]), "at": _now(), "by": who}
        anchor = state.get("anchor")
        if who == "user" or not anchor or anchor.get("basis") != current["basis"] or anchor.get("size_unit") != unit:
            state.update(anchor=current, status="anchored", drift=0.0)
            state.pop("held", None)
        else:
            drift = abs(current["size"] - anchor["size"]) / anchor["size"]
            state["drift"] = round(drift, 4)
            if drift > TOLERANCE and current["conversion"] != anchor["conversion"]:
                restored = copy.deepcopy(anchor["conversion"])
                _widen(restored, current["conversion"])
                proposal = {k: current[k] for k in ("size", "size_unit", "at", "conversion")}
                proposal["drift"] = round(drift, 4)
                proposal["assumptions"] = [
                    {"name": n, "value": p["value"], "unit": p.get("unit"), "rationale": str(p.get("rationale", ""))[:240]}
                    for n, p in _assumptions(current["conversion"]).items()]
                state["held"] = proposal
                state["proposals"] = ((state.get("proposals") or []) + [
                    {k: proposal[k] for k in ("size", "size_unit", "drift", "at")}])[-5:]
                state["status"] = "held"
                row["unit_conversion"] = restored
                anchor["conversion"] = copy.deepcopy(restored)
                held.append(key)
            else:
                state["status"] = "stable"
                state.pop("held", None)
        row[GUARD] = state
    return plan, held
