"""Autopilot: one action from extracted data to a full provisional analysis.

For an analyst who wants answers first and options later. Starting from a
study whose engineering data has been extracted, Autopilot:

1. approves the extraction for a provisional run (recorded as an Autopilot
   approval, listed for review; the user started it explicitly);
2. gives every item without a model the instant matcher's best guess
   (``model_selection.origin = "autopilot"``; a user's choice is never changed);
3. runs every stage in order (equipment, CAPEX, revenue, OPEX, financial)
   through the normal stage runners, with AI proposing what the data lacks
   (sizing inputs, CAPEX factors, OPEX lines) and Python doing all arithmetic;
4. records a review queue of everything decided on the user's behalf.

Nothing here is a new calculation path: it only sequences the existing,
tested stages. A saved version is taken before the run so it can be undone.
Revenue still requires the user's Revenue Box; it is never invented.
"""

from datetime import datetime, timezone

from . import progress
from .execution import fresh
from .stage_workflow import approve, approved

VERSION = "autopilot-1"


def _now():
    return datetime.now(timezone.utc).isoformat()


def _pick_models(state):
    """Best-guess models for items with none; returns the tags picked."""
    from backend.equipment_matching.deterministic import match_register
    from backend.equipment_matching.library_preference import user_selected_model
    from backend.ingestion.design_basis import extract as design_basis

    parsed = state.get("parsed") or {}
    report = state.get("scoped_report") or state.get("effective_report") or parsed.get("report") or {}
    rows = {r.get("equipment_key"): r for r in (state.get("plan") or {}).get("equipment", [])}
    current = {k: r.get("curve_id") for k, r in rows.items() if r.get("curve_id")}
    result = match_register(report, design_basis(parsed.get("source_cells") or []), current)
    picked = []
    for m in result["matches"]:
        row = rows.get(m["equipment_key"]) or {"equipment_key": m["equipment_key"]}
        if user_selected_model(row) or row.get("manual_price"):
            continue
        if row.get("curve_id"):
            # Keep the model already there; marking it settled skips a slow AI re-match.
            if not row.get("model_selection"):
                row["model_selection"] = {"origin": "autopilot", "curve_id": row["curve_id"]}
                rows[m["equipment_key"]] = row
            continue
        if not m["options"]:
            continue
        best = m["options"][0]
        row.update(
            curve_id=best["model_id"],
            source=best["source"],
            model_selection={"origin": "autopilot", "curve_id": best["model_id"]},
            rationale=f"Autopilot best guess: {m['family_label']} · {best.get('configuration') or best['model_id']}",
            quick_match={"version": result["version"], "status": m["status"], "family": m["family"],
                         "basis": m["family_basis"], "picked_by": VERSION},
        )
        rows[m["equipment_key"]] = row
        picked.append({"tag": m["tag"], "model": best.get("configuration") or best["model_id"],
                       "status": m["status"], "options": len(m["options"])})
    state.setdefault("plan", {})["equipment"] = list(rows.values())
    return picked


def review_queue(state, picked, auto_approved):
    """Everything decided on the user's behalf, with where to review it."""
    stages = (state.get("results") or {}).get("stages") or {}
    runs = state.get("stage_runs") or {}
    queue = []
    if auto_approved:
        queue.append({"stage": "entry", "kind": "approval",
                      "text": "Extracted engineering data approved by Autopilot for this provisional run."})
    if picked:
        guesses = [p for p in picked if p["status"] != "auto"]
        queue.append({"stage": "entry", "kind": "models",
                      "text": f"{len(picked)} cost model(s) picked by Autopilot"
                              + (f", {len(guesses)} of them best guesses where the workbook does not state the type" if guesses else ""),
                      "items": [p["tag"] for p in picked]})
    equipment = (stages.get("equipment") or {}).get("result") or {}
    assumed = 0
    for row in (state.get("plan") or {}).get("equipment", []):
        for p in ((row.get("unit_conversion") or {}).get("input_provenance") or {}).values():
            if isinstance(p, dict) and p.get("status") in {"llm_estimate", "assumed", "derived_from_sources_and_assumptions"}:
                assumed += 1
    if assumed:
        queue.append({"stage": "equipment", "kind": "assumptions",
                      "text": f"{assumed} sizing input(s) assumed by the AI (labelled provisional; type over any of them)."})
    coverage = equipment.get("pricing_coverage") or {}
    unpriced = [r.get("equipment_tag") for r in coverage.get("review_queue") or []]
    if coverage.get("unpriced"):
        queue.append({"stage": "equipment", "kind": "unpriced",
                      "text": f"{coverage['unpriced']} item(s) still unpriced (never counted as zero): enter a size or your price.",
                      "items": unpriced})
    capex = (stages.get("capex") or {}).get("result") or {}
    if capex.get("python_defaults"):
        queue.append({"stage": "capex", "kind": "defaults",
                      "text": "CAPEX settings filled with Python defaults (process type, delivered equipment, mid-range Garrett factors, offsite facilities 0)."})
    if (runs.get("capex") or {}).get("status") == "ready" and capex.get("total_capex") is None:
        reason = next((str(i) for i in capex.get("issues") or [] if "bases differ" in str(i)), None) \
            or next((str(i) for i in capex.get("issues") or []), "a required input is missing")
        queue.append({"stage": "capex", "kind": "blocked", "text": "Total CAPEX not calculated: " + reason})
    for stage in ("equipment", "capex", "revenue", "opex", "financial"):
        run = runs.get(stage) or {}
        if run.get("status") in (None, "ready"):
            continue
        message = str(run.get("message") or run.get("status"))
        if stage == "revenue" and "Revenue Box" in message:
            queue.append({"stage": "revenue", "kind": "needs_input",
                          "text": "Tell FlowValue how the project earns money (Revenue Box) to get revenue, NPV and IRR. "
                                  "Income is never invented."})
        elif stage == "financial" and "run Revenue first" in message:
            continue  # follows from the revenue item above
        else:
            queue.append({"stage": stage, "kind": "blocked",
                          "text": f"{stage.replace('_', ' ').capitalize()} did not finish: {message}"})
    return queue


def headline(state):
    """Key numbers for the results card; values copied from Python results."""
    stages = (state.get("results") or {}).get("stages") or {}
    get = lambda s: (stages.get(s) or {}).get("result") or {}
    equipment, capex, opex, financial = get("equipment"), get("capex"), get("opex"), get("financial")
    metrics = {}
    for item in financial.get("metrics") or []:
        if isinstance(item, (list, tuple)) and len(item) == 2 and isinstance(item[1], dict):
            metrics[item[0]] = item[1].get("value")
    coverage = equipment.get("pricing_coverage") or {}
    return {
        "currency": capex.get("currency") or financial.get("currency") or "USD",
        "equipment_purchased": equipment.get("equipment_cost_total"),
        "equipment_priced": coverage.get("priced"),
        "equipment_unpriced": coverage.get("unpriced"),
        "total_capex": capex.get("total_capex"),
        "fixed_capital": capex.get("fixed_capital"),
        "annual_opex": opex.get("known_cash_opex_subtotal"),
        "npv": metrics.get("project_npv"),
        "irr": metrics.get("project_irr"),
    }


def run(store, key, *, use_ai=False, provider=None):
    """Execute Autopilot for one study (called on the worker thread)."""
    from .stage_workflow import queue as queue_stages
    from .stage_workflow import run as run_stages

    token = progress.begin(key, "autopilot")
    started = _now()
    try:
        state = store.get(key)
        if not fresh(state, "engineering_data"):
            raise ValueError("Extract engineering data before running Autopilot")
        auto_approved = False
        if not approved(state):
            progress.step("Approving extracted data for a provisional run")
            state = approve(store, key, state["revision"])
            state["engineering_approval"]["by"] = VERSION
            auto_approved = True
        progress.step("Picking cost models")
        picked = _pick_models(state)
        state["autopilot"] = {"status": "running", "version": VERSION, "started_at": started, "use_ai": use_ai}
        store.put(state, state["revision"])
        queue_stages(store, key)
        state = run_stages(store, key, use_ai=use_ai, provider=provider)
        state["autopilot"] = {
            "status": "finished", "version": VERSION, "started_at": started, "finished_at": _now(),
            "use_ai": use_ai, "picked_models": picked, "headline": headline(state),
            "review": review_queue(state, picked, auto_approved),
        }
        return store.put(state, state["revision"])
    except Exception as exc:
        state = store.get(key)
        state["running"] = False
        state.pop("queued_stage", None)
        state["autopilot"] = {"status": "failed", "version": VERSION, "started_at": started,
                              "finished_at": _now(), "error": str(exc)[:300]}
        store.put(state, state["revision"])
        raise
    finally:
        progress.end(key, token)
