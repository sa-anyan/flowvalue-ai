"""Manual block lifecycle. Prerequisites are checked, never executed implicitly."""

import copy
import hashlib
import json
import time
from datetime import datetime, timezone

from backend.orchestration.codec import plain
from .models import Context, DataRequired
from .execution_observation import (
    ObservationCollector, capture_dispatch, observe_safely, publish_observation,
)
from .registry import BLOCKS, dependencies, get_runner, list_blocks

MODE = "isolated_stages_v1"
PIPELINE_ID = "flowvalue-shared-stage-pipeline-v1"


def _digest(value):
    return hashlib.sha256(
        json.dumps(
            plain(value), sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()


def initialize(state):
    if state.get("execution_mode") == MODE:
        return state
    state["source_sha256"] = state.get("source_sha256") or state.get("parsed", {}).get(
        "report", {}
    ).get("sha256")
    from backend.equipment_costing.cost_to_future.cost_translation import DEFAULT_POLICY

    state.setdefault("plan", {}).setdefault("cost_translation", dict(DEFAULT_POLICY))
    state["execution_mode"] = MODE
    state["stage_runs"] = {}
    state["stage_outputs"] = {}
    state["results"] = {
        "stages": {},
        "scope": "Individually executed stages; no automatic propagation.",
        "exclusions": [],
        "screening_comparisons": [],
        "notice": "Only explicitly run stages have outputs. Missing/stale prerequisites are not calculated automatically.",
    }
    for key in (
        "parsed",
        "effective_report",
        "scoped_report",
        "engineering_review",
        "financial_inputs",
    ):
        state.pop(key, None)
    return state


def _inputs(state, block):
    plan = state.get("plan", {})
    config = plan.get("operating_economics", {})
    if block == "engineering_data":
        return {
            "source": state.get("source_sha256"),
            "filename": state.get("filename"),
            "process": state.get("process_description", state.get("description", "")),
        }
    if block == "equipment":
        return {
            "equipment": plan.get("equipment", []),
            "translation": plan.get("cost_translation"),
        }
    if block == "capex":
        return {
            "capex": plan.get("capex", {}),
            "translation": plan.get("cost_translation"),
        }
    shared = {
        k: config.get(k)
        for k in ("methodology", "assumption_date", "price_basis", "operating")
    }
    shared["schedule"] = {
        k: config.get("financial", {}).get(k)
        for k in ("operating_years", "production_ramp")
    }
    shared["translation"] = plan.get("cost_translation")
    if block == "revenue":
        shared.update(
            {
                k: config.get(k)
                for k in (
                    "sales",
                    "commercial_lines",
                    "avoided_costs",
                    "commercial_intent",
                )
            }
        )
        if config.get("cashflow_schedule"):
            shared["cashflow_schedule"] = config["cashflow_schedule"]
        shared["box"] = state.get("revenue_description", "")
        shared["approval"] = (state.get("revenue_approval") or {}).get("fingerprint")
    if block == "opex":
        shared["optional_cost_bases"] = {
            key: (
                state.get("stage_runs", {}).get(key, {}).get("output_hash")
                if fresh(state, key)
                else None
            )
            for key in ("capex", "revenue")
        }
        shared.update(
            {
                k: config.get(k)
                for k in (
                    "materials",
                    "energy",
                    "labour",
                    "additional_expenses",
                    "garrett_factors",
                )
            }
        )
    if block == "financial":
        shared["financial"] = config.get("financial", {})
    return shared


def input_fingerprint(state, block):
    return _digest(
        {
            "inputs": _inputs(state, block),
            "upstream": {
                key: state.get("stage_runs", {}).get(key, {}).get("output_hash")
                for key in dependencies(block, state)
            },
        }
    )


def fresh(state, block, trail=()):
    if block in trail:
        return False
    receipt = state.get("stage_runs", {}).get(block, {})
    return (
        receipt.get("status") == "ready"
        and block in state.get("stage_outputs", {})
        and receipt.get("input_hash") == input_fingerprint(state, block)
        and all(
            fresh(state, key, (*trail, block)) for key in dependencies(block, state)
        )
    )


def previous_equipment_result(state):
    current = (
        state.get("results", {}).get("stages", {}).get("equipment", {}).get("result")
    )
    baseline = (
        state.get("edit_baseline", {})
        .get("results", {})
        .get("stages", {})
        .get("equipment", {})
        .get("result")
    )
    saved = state.get("stage_outputs", {}).get("equipment", {}).get("total")
    return copy.deepcopy(
        current if current is not None else baseline if baseline is not None else saved
    )


def refresh(state):
    """Invalidate views only; this never calls any engine or changes saved data."""
    for key in BLOCKS:
        receipt = state.setdefault("stage_runs", {}).get(key)
        if receipt and receipt.get("status") == "ready" and not fresh(state, key):
            receipt["status"] = "stale"
            state.setdefault("results", {}).setdefault("stages", {})[key] = {
                "status": "stale",
                "result": (
                    previous_equipment_result(state)
                    if key == "equipment"
                    else state["results"]["stages"].get(key, {}).get("result")
                ),
                "result_is_stale": True,
                "issues": [
                    "Inputs changed. Run "
                    + BLOCKS[key]["label"]
                    + " explicitly to update this result."
                ],
            }
    equipment_view = state.get("results", {}).get("stages", {}).get("equipment", {})
    if equipment_view.get("status") == "stale" and equipment_view.get("result") is None:
        equipment_view.update(
            result=previous_equipment_result(state), result_is_stale=True
        )
    return state


def view(saved):
    historical = saved.get("execution_mode") != MODE and bool(saved.get("results"))
    state = initialize(copy.deepcopy(saved))
    refresh(state)
    state["pipeline_id"] = PIPELINE_ID
    if historical:
        state["status"] = (
            "Historical snapshot: run Engineering to calculate through the shared pipeline"
        )
        state["execution_notice"] = (
            "These saved results were produced by the retired connected workflow. They are retained as history; run Engineering data and Equipment through the shared pipeline for current results."
        )
    if any(
        state.get(key, {}).get("status") == "running"
        for key in ("engineering_workflow", "stage_workflow")
    ):
        state["running"] = True
    if not fresh(state, "engineering_data"):
        for field in ("parsed", "effective_report", "scoped_report"):
            state.pop(field, None)
    from .stage_workflow import approved

    state["engineering_data_approved"] = approved(state)
    state["stage_definitions"] = [
        dict(item, requires=dependencies(item["id"], state)) for item in list_blocks()
    ]
    return state


def _apply(state, block, updates):
    """A runner can publish its own inputs/report, never another block's result."""
    allowed = {
        "engineering_data": {
            "parsed",
            "effective_report",
            "engineering_review",
            "recoveries",
            "ai",
            "source_sha256",
        },
        "equipment": {"plan"},
        "capex": {"plan"},
        "revenue": {"plan"},
        "opex": {"plan"},
        "financial": {"plan"},
    }[block]
    if set(updates) - allowed:
        raise ValueError("Block tried to write outside its owned boundary")
    updates = copy.deepcopy(updates)
    changes = updates.pop("plan", {})
    allowed_plan = {
        "equipment": {"equipment"},
        "capex": {"capex"},
        "revenue": {"operating_economics"},
        "opex": {"operating_economics"},
        "financial": {"financial", "operating_economics"},
        "engineering_data": set(),
    }[block]
    if set(changes) - allowed_plan:
        raise ValueError("Block tried to change another stage’s assumptions")
    if "operating_economics" in changes:
        before = state.get("plan", {}).get("operating_economics", {})
        after = changes["operating_economics"]
        other = {
            "revenue": (
                "materials",
                "energy",
                "labour",
                "additional_expenses",
                "garrett_factors",
            ),
            "opex": ("sales", "commercial_lines", "avoided_costs", "commercial_intent", "pending_inputs"),
        }.get(block, ())
        if any(before.get(key) != after.get(key) for key in other):
            raise ValueError("A stage cannot overwrite another stage’s assumptions")
    state.setdefault("plan", {}).update(changes)
    state.update(updates)


def run_stage(
    store, key, block, *, use_ai=False, provider=None,
    observation_collector: ObservationCollector | None = None,
    observation_scenario_id: str | None = None,
):
    if block not in BLOCKS:
        raise ValueError("Unknown stage: " + block)
    state = store.get(key)
    if state.get("running") and state.get("queued_stage") != block:
        raise ValueError("Another stage is running")
    if state.get("execution_mode") != MODE and state.get("results"):
        state["previous_connected_version"] = store.version(
            key, "Before isolated stage execution"
        )
    state = initialize(state)
    refresh(state)
    started = time.monotonic()
    receipt = {
        "status": "running",
        "pipeline_id": PIPELINE_ID,
        "producer": "backend.blocks." + block + ".runner.calculate",
        "executed": False,
        "use_ai": use_ai,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
    missing = [p for p in dependencies(block, state) if not fresh(state, p)]
    dispatch = None
    outcome = "failed"
    if missing:
        outcome = "blocked"
        if observation_collector is not None:
            dispatch = observe_safely(lambda: capture_dispatch(state, _inputs(state, block)))
        error = DataRequired(
            "Data required: run "
            + ", ".join(BLOCKS[p]["label"] for p in missing)
            + " first.",
            missing,
        )
        product = None
    else:
        state["running"] = True
        state["queued_stage"] = block
        state.setdefault("stage_runs", {})[block] = receipt
        state = store.put(state, state["revision"])
        try:
            upstream = {
                p: copy.deepcopy(state["stage_outputs"][p])
                for p in dependencies(block, state)
            }
            if block == "opex":
                for optional in ("capex", "revenue"):
                    if fresh(state, optional):
                        upstream[optional] = copy.deepcopy(
                            state["stage_outputs"][optional]
                        )
            report = upstream.get("engineering_data", {}).get("report", {})
            if not report:
                report = (
                    state.get("stage_outputs", {})
                    .get("engineering_data", {})
                    .get("report", {})
                )
            ctx = Context(
                copy.deepcopy(state),
                report,
                upstream,
                store,
                store.workbook(key) if block == "engineering_data" else None,
                provider,
                use_ai,
            )
            if observation_collector is not None:
                dispatch = observe_safely(lambda: capture_dispatch(state, _inputs(state, block), ctx))
            receipt["executed"] = True
            product = get_runner(block)(ctx)
            error = None
        except DataRequired as exc:
            outcome = "blocked"
            product, error = None, exc
        except (
            ValueError,
            TypeError,
            KeyError,
            ArithmeticError,
            AttributeError,
        ) as exc:
            product, error = None, DataRequired(
                "Data required or invalid input for "
                + BLOCKS[block]["label"]
                + ": "
                + str(exc)
            )
        except Exception as exc:
            product, error = None, DataRequired(
                "This stage could not finish ("
                + type(exc).__name__
                + "). Other stages were not run."
            )
    if product is not None:
        try:
            _apply(state, block, product.updates)
        except (ValueError, TypeError, AttributeError) as exc:
            product, error = None, DataRequired(
                "Stage output could not be applied: " + str(exc)
            )
    if product is not None:
        state.setdefault("stage_outputs", {})[block] = plain(product.payload)
        value = plain(product.result)
        receipt.update(
            status="ready",
            complete=product.complete,
            input_hash=input_fingerprint(state, block),
            output_hash=_digest(product.payload),
        )
        state["results"]["stages"][block] = {
            "status": (
                value.get("status", "calculated")
                if isinstance(value, dict)
                else "calculated"
            ),
            "result": value,
            "issues": list(product.issues),
        }
        if block == "equipment":
            state["results"]["exclusions"] = [
                {
                    "equipment_tag": tag,
                    "reason": "No purchased cost available",
                    "cost": None,
                }
                for tag in product.payload.get("unpriced", [])
            ]
        if block == "financial":
            state["results"]["financial_inputs"] = plain(
                product.payload.get("financial_inputs")
            )
        if block == "capex":
            state["results"]["screening_comparisons"] = plain(
                product.payload.get("screening_comparisons", [])
            )
    else:
        _apply(state, block, error.updates)
        receipt.update(
            status="data_required", requires=error.stages, message=str(error)
        )
        state["results"]["stages"][block] = {
            "status": "data_required",
            "result": (
                previous_equipment_result(state)
                if block == "equipment"
                else state["results"]["stages"].get(block, {}).get("result")
            ),
            "result_is_stale": True,
            "issues": [str(error)],
        }
    receipt["elapsed_seconds"] = time.monotonic() - started
    receipt["completed_at"] = datetime.now(timezone.utc).isoformat()
    state["stage_runs"][block] = receipt
    state["running"] = False
    state.pop("queued_stage", None)
    state["status"] = BLOCKS[block]["label"] + ": " + receipt["status"]
    state["progress"] = [{"stage": block, "status": receipt["status"]}]
    refresh(state)
    from backend.revenue.authority import questions

    report = (
        state.get("stage_outputs", {}).get("engineering_data", {}).get("report", {})
    )
    state["revenue_questions"] = questions(
        state.get("plan", {}).get("operating_economics", {}),
        state.get("revenue_description", ""),
        report,
        approval=state.get("revenue_approval"),
    )
    saved = store.put(state, state["revision"])
    if observation_collector is not None and dispatch is not None:
        if product is not None:
            outcome = "ready" if product.complete else "partial"
        observe_safely(
            publish_observation, observation_collector, key=key,
            scenario_id=observation_scenario_id, block=block, dispatch=dispatch,
            outcome=outcome, product=product,
        )
    return saved


def queue_stage(store, key, block):
    if block not in BLOCKS:
        raise ValueError("Unknown stage: " + block)
    state = store.get(key)
    if state.get("running"):
        raise ValueError("Another stage is running")
    if state.get("execution_mode") != MODE and state.get("results"):
        state["previous_connected_version"] = store.version(
            key, "Before isolated stage execution"
        )
    state = initialize(state)
    state.update(
        running=True,
        queued_stage=block,
        progress=[{"stage": block, "status": "queued"}],
    )
    return store.put(state, state["revision"])
