"""Assessment lifecycle: bounded proposal generation, locked edits, reproducible reruns."""

import copy
import json

from .advisor import propose
from .feedback import equipment_feedback
from .ingest import parse
from .pipeline import SECTIONS, empty_plan, run
from .register import mark_ai, register
from .workbook_review import review


def _diagnostic(exc):
    from backend.revenue.advisor import RevenueAIError

    if isinstance(exc, RevenueAIError):
        return str(exc)[:350]
    if isinstance(exc, ValueError) and str(exc).startswith(
        (
            "AI context exceeds",
            "One equipment planning region",
            "A source cell/description",
        )
    ):
        return str(exc)[:350]
    if isinstance(exc, (ValueError, TypeError, KeyError)):
        return (
            "Structured interpretation could not be applied ("
            + type(exc).__name__
            + ")."
        )
    return "Engineering service unavailable; previous results and inputs retained."


def new_assessment(store, content, filename, description, revenue_description=""):
    return store.create(
        {
            "filename": filename,
            "process_description": description,
            "revenue_description": revenue_description,
            "description": description
            + (
                "\n\nUSER REVENUE DESCRIPTION:\n" + revenue_description
                if revenue_description.strip()
                else ""
            ),
            "plan": empty_plan(),
            "locked": [],
            "assumptions": {},
            "running": True,
            "progress": [{"stage": "parse", "status": "queued"}],
            "results": None,
        },
        content,
    )


def execute(store, key, *, content=None, use_ai=False, provider=None):
    """Public compatibility entry: every workbook uses the shared stage workflow.

    Saved inputs may be reused, but saved result numbers are never supplied to
    the calculators. The Entry engineering action still stops after Equipment.
    """
    from backend.blocks.engineering_workflow import queue, run as run_engineering

    state = store.get(key)
    if content is not None and content != store.workbook(key):
        original = state
        state = new_assessment(
            store,
            content,
            original["filename"],
            original.get("process_description", original.get("description", "")),
            original.get("revenue_description", ""),
        )
        state.update(
            plan=copy.deepcopy(original.get("plan", empty_plan())),
            locked=copy.deepcopy(original.get("locked", [])),
        )
        state = store.put(state, state["revision"])
        key = state["id"]
    # Legacy new_assessment marked a not-yet-started source as running.
    if (
        state.get("execution_mode") is None
        and state.get("running")
        and state.get("results") is None
        and state.get("progress") == [{"stage": "parse", "status": "queued"}]
    ):
        state["running"] = False
        store.put(state, state["revision"])
    queue(store, key)
    return run_engineering(store, key, use_ai=use_ai, provider=provider)


def _execute_connected_reference(
    store, key, *, content=None, use_ai=False, provider=None
):
    """Retired connected coordinator, retained only by historical regression tests.

    No API, UI, current view or public execute() action dispatches here.
    """
    state = store.get(key)
    if state.get("execution_mode") == "isolated_stages_v1":
        raise ValueError("Stages are disconnected. Select an individual stage to run.")
    from backend.revenue.authority import bind

    bind(state)
    from backend.equipment_costing.cost_to_future.cost_translation import DEFAULT_POLICY

    if state["plan"].get("operating_economics") or not any(
        state["plan"].get(k) for k in SECTIONS
    ):
        state["plan"].setdefault("cost_translation", dict(DEFAULT_POLICY))
    state["running"] = True
    state["progress"] = []

    def save():
        nonlocal state
        state = store.put(state, state["revision"])

    def progress(stage, status):
        state["progress"].append({"stage": stage, "status": status})
        save()

    try:
        if content is not None:
            progress("parse", "running")
            state["parsed"] = parse(content, state["filename"])
            progress("parse", "parsed")
        if "parsed" not in state:
            raise ValueError("No parsed workbook available")
        if use_ai:
            from .provider import EngineeringProvider

            if provider is None:
                try:
                    provider = EngineeringProvider()
                except (
                    Exception
                ):  # noqa: BLE001 -- deterministic path remains available
                    provider = None
            progress("engineering_review", "running")
            try:
                effective, interpretation, decisions, review_meta = review(
                    state["parsed"], state["description"], store, provider
                )
                state["effective_report"] = effective
                state["engineering_review"] = interpretation
                state["recoveries"] = decisions
                state["questions"] = interpretation["questions"]
                state["ai"] = {"review": review_meta, "status": "reviewed"}
                progress("engineering_review", review_meta.get("status", "reviewed"))
            except (
                Exception
            ) as exc:  # noqa: BLE001 -- independent stages continue on provider failure
                state["ai"] = {
                    "status": "review_unavailable",
                    "notice": _diagnostic(exc),
                }
                progress("engineering_review", "unavailable")
            reviewed = dict(
                state["parsed"],
                revenue_box=state.get("revenue_description", ""),
                effective_report=state.get(
                    "effective_report", state["parsed"]["report"]
                ),
            )
            report = reviewed["effective_report"]
            from .analyst_team import coverage_register, review_team
            from .workbook_scope import calculation_scope

            state["analyst_reviews"] = review_team(
                report,
                state["description"],
                "engineering",
                store,
                provider,
                review_notes=state.get("review_decisions", []),
                progress=progress,
            )
            scope_review = next(
                (
                    r
                    for r in state["analyst_reviews"]
                    if r["role"] == "process_equipment_engineer"
                    and r.get("sheet_decisions")
                ),
                None,
            )
            if scope_review:
                try:
                    report = calculation_scope(report, scope_review["sheet_decisions"])
                    state["scoped_report"] = report
                    reviewed["effective_report"] = report
                except ValueError as exc:
                    state["scope_warning"] = str(exc)
                    try:
                        from .scope_recovery import recover

                        report = recover(report)
                        state["scoped_report"] = report
                        reviewed["effective_report"] = report
                    except ValueError:
                        pass
            state["cost_coverage"] = coverage_register(state["analyst_reviews"])
            ids = {
                v["id"]
                for e in report["entities"]
                for v in [e["id_evidence"], *e["values"]]
            }
            interim = None
            for requested in (
                ("equipment", "capex"),
                ("revenue", "opex"),
                ("financial",),
            ):
                if (
                    requested in {("revenue", "opex"), ("financial",)}
                    and "operating_economics" in state["locked"]
                ):
                    continue
                if requested == ("financial",) and state["plan"].get(
                    "operating_economics"
                ):
                    progress(
                        "financial_advisor",
                        "shared operating-study policy feeds the canonical financial engine",
                    )
                    continue
                if all(name in state["locked"] for name in requested):
                    continue
                if requested == ("financial",) and interim:
                    necessary = [
                        interim["stages"].get(k, {})
                        for k in ("capex", "revenue", "opex")
                    ]
                    if any(
                        s.get("status") in {"unresolved", "needs_review"}
                        for s in necessary
                    ):
                        progress(
                            "financial_advisor",
                            "awaiting upstream quantities and assumptions",
                        )
                        continue
                stage_name = "engineering_advisor:" + "+".join(requested)
                progress(stage_name, "running")
                try:
                    if requested == ("revenue", "opex"):
                        capital = (interim or {}).get("stages", {}).get(
                            "capex", {}
                        ).get("result") or {}
                        state["analyst_reviews"] += review_team(
                            report,
                            state["description"],
                            "operating",
                            store,
                            provider,
                            prior=state["analyst_reviews"],
                            capital=capital,
                            review_notes=state.get("review_decisions", []),
                            progress=progress,
                        )
                        state["cost_coverage"] = coverage_register(
                            state["analyst_reviews"]
                        )
                    summary = {}
                    if interim:
                        for stage_key in ("capex", "revenue", "opex"):
                            stage = interim["stages"].get(stage_key, {})
                            result = stage.get("result") or {}
                            summary[stage_key] = {
                                "status": stage.get("status"),
                                "issues": stage.get("issues"),
                                "result": {
                                    k: v
                                    for k, v in result.items()
                                    if k
                                    not in {
                                        "evidence",
                                        "methodology_source",
                                        "snapshot_id",
                                        "sources",
                                    }
                                },
                            }
                    response, meta = propose(
                        reviewed,
                        state["description"],
                        state["plan"],
                        state["locked"],
                        store,
                        provider,
                        requested_sections=requested,
                        stage_results=summary,
                        analyst_reviews=state["analyst_reviews"],
                    )
                    state["ai"].setdefault("advisors", {})["+".join(requested)] = meta
                    state["ai"]["status"] = "connected"
                    state["review"] = (
                        state.get("review", []) + response["source_review"]
                    )
                    state["questions"] = list(
                        dict.fromkeys(
                            state.get("questions", []) + response["questions"]
                        )
                    )
                    for section in response["sections"]:
                        name = section["section"]
                        if name not in state["locked"]:
                            value = mark_ai(
                                json.loads(section["value_json"]), evidence_ids=ids
                            )
                            if name == "equipment":
                                from .approved_equipment import retain_approved

                                value = retain_approved(
                                    state["plan"].get("equipment", []), value
                                )
                            state["plan"][name] = value
                            state["assumptions"][name] = dict(
                                section,
                                origin="llm_estimate",
                                status="engineering_scenario",
                            )
                    interim = run(report, state["description"], state["plan"])
                    state["results"] = interim
                    feedback = (
                        equipment_feedback(interim)
                        if requested == ("equipment", "capex")
                        else None
                    )
                    if feedback and "equipment" not in state["locked"]:
                        progress("engineering_validation_correction", "running")
                        corrected, correction_meta = propose(
                            reviewed,
                            state["description"],
                            state["plan"],
                            state["locked"],
                            store,
                            provider,
                            requested_sections=requested,
                            stage_results=feedback,
                            analyst_reviews=state["analyst_reviews"],
                        )
                        state["ai"]["advisors"][
                            "equipment_correction"
                        ] = correction_meta
                        for section in corrected["sections"]:
                            if section["section"] not in state["locked"]:
                                value = mark_ai(
                                    json.loads(section["value_json"]), evidence_ids=ids
                                )
                                if section["section"] == "equipment":
                                    from .approved_equipment import retain_approved

                                    value = retain_approved(
                                        state["plan"].get("equipment", []), value
                                    )
                                state["plan"][section["section"]] = value
                                state["assumptions"][section["section"]] = dict(
                                    section,
                                    origin="llm_estimate",
                                    status="engineering_scenario",
                                )
                        state["questions"] = list(
                            dict.fromkeys(state["questions"] + corrected["questions"])
                        )
                        interim = run(report, state["description"], state["plan"])
                        state["results"] = interim
                        progress("engineering_validation_correction", "applied")
                    if requested == ("equipment", "capex"):
                        from .design_handoff import complete

                        state["plan"], state["design_handoffs"] = complete(
                            report,
                            state["description"],
                            state["plan"],
                            state["locked"],
                            store,
                            provider,
                            progress=progress,
                        )
                        interim = run(report, state["description"], state["plan"])
                        state["results"] = interim
                    progress(stage_name, "proposed")
                except (
                    Exception
                ) as exc:  # noqa: BLE001 -- retain independent engineering work
                    state["ai"].setdefault("advisor_errors", {})[
                        "+".join(requested)
                    ] = _diagnostic(exc)
                    state["ai"]["notice"] = (
                        "Workbook interpretation retained; "
                        + "+".join(requested)
                        + " advisor: "
                        + _diagnostic(exc)
                    )
                    progress(stage_name, "unavailable")
        state["assumption_register"] = register(state["plan"], state["assumptions"])
        state["results"] = run(
            state.get(
                "scoped_report",
                state.get("effective_report", state["parsed"]["report"]),
            ),
            state["description"],
            state["plan"],
            progress=progress,
        )
        if state.get("edit_baseline"):
            from backend.equipment_resolution.comparison import compare_results

            state["recalculation_comparison"] = compare_results(
                state["edit_baseline"]["results"], state["results"]
            )
        stages = state["results"]["stages"]
        if any(
            (s.get("result") or {}).get("complete") is False for s in stages.values()
        ):
            state["status"] = (
                "partial_assessment; resolved calculations available, dependencies pending"
            )
        else:
            state["status"] = (
                "calculated_with_disclosures"
                if stages.get("financial", {}).get("result")
                else "incomplete_assessment; review stage issues"
            )
    except (
        Exception
    ) as exc:  # noqa: BLE001 -- always release running state at task boundary
        state["status"] = "failed"
        state["error"] = (
            str(exc)[:500]
            if isinstance(exc, ValueError)
            else "Assessment failed; source retained for review"
        )
    from backend.revenue.authority import questions

    state["revenue_questions"] = questions(
        state["plan"].get("operating_economics", {}),
        state.get("revenue_description", ""),
        state.get("scoped_report")
        or state.get("effective_report")
        or state.get("parsed", {}).get("report", {}),
        approval=state.get("revenue_approval"),
    )
    state["running"] = False
    save()
    return state


def edit(store, key, revision, section, value, rationale):
    if (
        section not in (*SECTIONS, "operating_economics", "cost_translation")
        or not rationale.strip()
    ):
        raise ValueError("Known section and edit rationale required")
    if len(json.dumps(value)) > 250000:
        raise ValueError("Input section exceeds safe limit")
    state = store.get(key)
    if state["running"]:
        raise ValueError("Wait for assessment to finish before editing")
    if state["revision"] != revision:
        raise ValueError("Assessment changed; reload before editing")
    value = copy.deepcopy(value)
    if section == "equipment":
        previous = {
            r.get("equipment_key"): r for r in state["plan"].get("equipment", [])
        }

        def approve(rows, old_rows):
            old = {r.get("asset_id", r.get("equipment_key")): r for r in old_rows}
            for row in rows:
                prior = old.get(row.get("asset_id", row.get("equipment_key")), {})
                price = row.get("manual_price")
                requested = (
                    bool(price.pop("approval_requested", False)) if price else False
                )
                prior_price = prior.get("manual_price") or {}
                changed_price = bool(price) and any(
                    price.get(k) != prior_price.get(k)
                    for k in (
                        "amount",
                        "currency",
                        "price_period",
                        "source",
                        "cost_scope",
                        "purchased_component",
                        "installation_factor",
                    )
                )
                if (
                    price
                    and price.get("approved") is True
                    and (
                        requested
                        or prior_price.get("approved") is not True
                        or changed_price
                    )
                ):
                    price["approval_origin"] = "explicit_user_edit"
                    price["approval_rationale"] = rationale
                if row.get("physical_assets"):
                    approve(row["physical_assets"], prior.get("physical_assets", []))

        approve(value, list(previous.values()))
    if section == "operating_economics":
        from backend.revenue.commercial_intent import capture_manual_methods

        def methods(config):
            return [
                (row.get("id"), "product_sales") for row in config.get("sales", [])
            ] + [
                (row.get("id"), row.get("category"))
                for row in config.get("commercial_lines", [])
            ]

        if methods(value) != methods(state["plan"].get(section, {})):
            value = capture_manual_methods(
                value, rationale, revenue_box=state.get("revenue_description", "")
            )
    if state.get("results") is not None:
        state["edit_baseline"] = {
            "revision": state["revision"],
            "results": copy.deepcopy(state["results"]),
            "plan": copy.deepcopy(state["plan"]),
        }
    state["plan"][section] = value
    state["locked"] = sorted(set(state["locked"]) | {section})
    state["assumptions"][section] = {
        "origin": "user_assumption",
        "status": "user_override",
        "rationale": rationale,
        "uncertainty": "User-defined scenario; not independently verified",
    }
    state["assumption_register"] = register(state["plan"], state["assumptions"])
    state["status"] = "stale; Run Again required"
    if state.get("execution_mode") == "isolated_stages_v1":
        from backend.blocks.execution import refresh

        refresh(state)
    else:
        state["results"] = None
    return store.put(state, revision)


def compare(left, right):
    def metrics(state):
        stages = (state.get("results") or {}).get("stages", {})
        return {name: stages.get(name, {}).get("result") for name in SECTIONS}

    return {
        "left": metrics(left),
        "right": metrics(right),
        "changed_sections": [
            k
            for k in (*SECTIONS, "operating_economics")
            if left["plan"].get(k) != right["plan"].get(k)
        ],
        "left_scope": (left.get("results") or {}).get("scope"),
        "right_scope": (right.get("results") or {}).get("scope"),
    }
