"""Entry revenue-only orchestration using the canonical parser and revenue engine."""

import copy
import json

from backend.opex.models import Basis
from backend.revenue import calculate_revenue
from backend.revenue.authority import bind, questions, runtime

from .advisor import propose
from .codec import plain
from .ingest import parse
from .operating_economics import _revenue_project, operating_schedule
from .register import mark_ai, register
from .workbook_review import review


def _interpret_box(store, state, report, provider):
    """Identical fresh commercial interpretation for Entry and saved Box edits."""
    parsed = dict(state["parsed"], effective_report=report,
                  revenue_box=state.get("revenue_description", ""), revenue_edit=True)
    locked = [name for name in state.get("locked", []) if name != "operating_economics"]
    response, metadata = propose(parsed, state["description"], state["plan"], locked,
                                 store, provider, requested_sections=("revenue",), force_refresh=True)
    if len(response["sections"]) != 1 or response["sections"][0]["section"] != "operating_economics":
        raise ValueError("AI must return one revenue interpretation")
    response = copy.deepcopy(response)
    section = response["sections"][0]
    config = json.loads(section["value_json"])
    for field in ("sales", "commercial_lines", "avoided_costs", "pending_inputs", "scope_notes", "questions"):
        config.setdefault(field, [])
    config.setdefault("commercial_intent", {})
    section["value_json"] = json.dumps(config)
    return response, metadata


def reinterpret_revenue(store, state, *, provider=None):
    """Fresh AI interpretation of a saved Box; no workbook or other engine rerun."""
    state["running"] = True
    state.pop("revenue_approval", None)
    state.pop("error", None)
    try:
        if not state.get("parsed"):
            raise ValueError("Upload and parse a mass and energy balance first")
        if not state.get("revenue_description", "").strip():
            raise ValueError("Describe how this project earns revenue before interpreting it")
        if provider is None:
            from .provider import EngineeringProvider
            provider = EngineeringProvider()
        report = state.get("scoped_report") or state.get("effective_report") or state["parsed"]["report"]
        response, metadata = _interpret_box(store, state, report, provider)
        section = response["sections"][0]
        fresh = mark_ai(json.loads(section["value_json"]))
        old = state["plan"].get("operating_economics", {})
        if old.get("price_basis") and fresh.get("price_basis") != old["price_basis"]:
            raise ValueError("AI changed the saved revenue currency or price period; review the price basis explicitly")
        revised = copy.deepcopy(old)
        for field in ("sales", "commercial_lines", "avoided_costs", "pending_inputs", "commercial_intent", "scope_notes", "questions"):
            revised[field] = fresh.get(field, [] if field != "commercial_intent" else {})
        # Initial incomplete drafts can acquire their first declared schedule/basis.
        for field in ("operating", "financial", "price_basis", "assumption_date", "methodology", "origin"):
            if not revised.get(field) and field in fresh:
                revised[field] = fresh[field]
        state.setdefault("revenue_interpretation_history", []).append({
            "previous_inputs": copy.deepcopy(old), "model": metadata.get("model"),
            "origin": "user_requested_revenue_box_reinterpretation",
        })
        state["plan"]["operating_economics"] = revised
        state.pop("revenue_approval", None)
        bind(state)
        state["assumptions"]["operating_economics"] = dict(section, origin="llm_estimate", status="revenue_draft")
        state["assumption_register"] = register(state["plan"], state["assumptions"])
        state["questions"] = response["questions"]
        state["revenue_questions"] = list(dict.fromkeys(response["questions"] + questions(
            revised, state["revenue_description"], report, require_approval=True)))
        if state.get("results"):
            names = ("revenue",) if state.get("workflow") == "revenue" else ("revenue", "financial")
            for name in names:
                state["results"].setdefault("stages", {})[name] = {
                    "status": "pending_user_input", "result": None,
                    "issues": state["revenue_questions"] or ["Review and approve the new commercial assumptions."],
                }
        state.setdefault("ai", {}).update(status="connected", revenue=metadata)
        state["ai"].pop("revenue_refresh_error", None)
        state["status"] = "Revenue reinterpreted; review and approve the new assumptions"
        state["progress"] = [{"stage": "revenue_planning", "status": "proposed"}]
    except Exception as exc:
        from .service import _diagnostic
        state["error"] = str(exc)[:500] if isinstance(exc, ValueError) else _diagnostic(exc)
        state["status"] = "Revenue Box saved; AI interpretation unavailable"
        state.setdefault("ai", {})["revenue_refresh_error"] = state["error"]
        state["progress"] = [{"stage": "revenue_planning", "status": "unavailable"}]
    state["running"] = False
    return store.put(state, state["revision"])


def execute_revenue(store, state, *, content=None, use_ai=False, provider=None):
    state["running"], state["progress"] = True, []
    state["results"] = None
    state.pop("error", None)

    def save():
        nonlocal state
        state = store.put(state, state["revision"])

    def progress(stage, status):
        state["progress"].append({"stage": stage, "status": status})
        save()

    try:
        if not state.get("process_description", "").strip():
            raise ValueError("Describe your process before running revenue")
        if content is None and not state.get("parsed"):
            content = store.workbook(state["id"])
        if content is not None:
            progress("parse", "running")
            state["parsed"] = parse(content, state["filename"])
            progress("parse", "parsed")
        if not state.get("parsed"):
            raise ValueError("Upload a mass and energy balance before running revenue")
        bind(state)
        report = state.get("effective_report", state["parsed"]["report"])
        if use_ai:
            if provider is None:
                from .provider import EngineeringProvider
                provider = EngineeringProvider()
            progress("engineering_review", "running")
            effective, interpretation, decisions, metadata = review(
                state["parsed"], state["description"], store, provider
            )
            state.update(effective_report=effective, engineering_review=interpretation,
                         recoveries=decisions, questions=interpretation["questions"],
                         ai={"review": metadata, "status": "reviewed"})
            report = effective
            progress("engineering_review", metadata.get("status", "reviewed"))
            if "operating_economics" not in state["locked"]:
                progress("revenue_planning", "running")
                response, metadata = _interpret_box(store, state, report, provider)
                for section in response["sections"]:
                    if section["section"] != "operating_economics":
                        raise ValueError("Revenue-only planning returned an unrelated section")
                    state["plan"]["operating_economics"] = mark_ai(json.loads(section["value_json"]))
                    state["assumptions"]["operating_economics"] = dict(section, origin="llm_estimate", status="revenue_scenario")
                state["questions"] = list(dict.fromkeys(state["questions"] + response["questions"]))
                state["ai"].update(status="connected", revenue=metadata)
                progress("revenue_planning", "proposed")
        config = copy.deepcopy(state["plan"].get("operating_economics", {}))
        state["revenue_questions"] = questions(config, state.get("revenue_description", ""), report,
                                               approval=state.get("revenue_approval"))
        progress("revenue", "running")
        stage = {"status": "pending_user_input", "result": None, "issues": state["revenue_questions"]}
        if not state["revenue_questions"]:
            if any(s.get("price_mode") == "cost_plus" for s in config.get("sales", [])):
                raise ValueError("Revenue-only runs require explicit selling prices; cost-plus pricing needs a full operating study")
            config["_revenue_authority"] = runtime(config, state["plan"]["revenue_authority"], report)
            hours, ramp = operating_schedule(config)
            result = calculate_revenue(_revenue_project(report, state["revenue_description"], config,
                                                       Basis(**config["price_basis"]), hours, ramp, {}),
                                       engineering_scenario=True)
            stage = {"status": "calculated", "result": plain(result), "issues": list(result.issues)}
        state["results"] = {"stages": {"revenue": stage}, "scope": "revenue only",
                            "exclusions": [], "notice": "Revenue-only workflow; review source quantities and commercial assumptions."}
        state["assumption_register"] = register(state["plan"], state["assumptions"])
        state["status"] = "revenue_calculated" if stage["result"] else "revenue_pending_user_input"
        progress("revenue", stage["status"])
    except Exception as exc:
        state["status"] = "failed"
        from .service import _diagnostic
        state["error"] = str(exc)[:500] if isinstance(exc, ValueError) else _diagnostic(exc)
    state["running"] = False
    save()
    return state
