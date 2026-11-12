"""Opt-in evidence from an isolated attempt, independent of receipt policy."""

from dataclasses import dataclass
from hashlib import sha256
import json
import logging
from typing import Callable
from uuid import uuid4

from backend.dashboard_reporting.sizing_trace import sizing_trace
from backend.orchestration.calculation_receipts import CalculationScope, semantic_digest

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DispatchEvidence:
    attempt_id: str
    input_revision: int
    stage_input_digest: str
    context_digest: str | None
    workbook_sha256: str | None
    supplied_upstream: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class ExecutionObservation:
    scope: CalculationScope
    attempt_id: str
    stage: str
    dispatch: DispatchEvidence
    outcome: str
    complete: bool | None
    effective_inputs: tuple[tuple[str, str], ...] = ()
    consumed_upstream: tuple[str, ...] = ()
    source_observation_ids: tuple[str, ...] = ()
    emitted_methods_json: tuple[str, ...] = ()
    handoff_digest: str | None = None
    result_digest: str | None = None
    financial_ledger_digest: str | None = None


ObservationCollector = Callable[[ExecutionObservation], None]


def capture_dispatch(state, stage_inputs, ctx=None):
    return DispatchEvidence(
        attempt_id=uuid4().hex,
        input_revision=state["revision"],
        stage_input_digest=semantic_digest(stage_inputs),
        context_digest=semantic_digest({
            "state": ctx.state,
            "report": ctx.report,
            "use_ai": ctx.use_ai,
        }) if ctx else None,
        workbook_sha256=sha256(ctx.content).hexdigest() if ctx and ctx.content is not None else None,
        supplied_upstream=tuple(
            (name, semantic_digest(payload)) for name, payload in sorted(ctx.upstream.items())
        ) if ctx else (),
    )


def publish_observation(collector, *, key, scenario_id, block, dispatch, outcome, product):
    payload = product.payload if product else {}
    effective = tuple(
        (field, semantic_digest(payload[field]))
        for field in ("financial_inputs", "config") if field in payload
    )
    methods, observations = [], []
    if product and block == "equipment":
        for row in product.result.get("equipment", []):
            methods.extend(json.dumps(method, sort_keys=True) for method in sizing_trace(row)["engineering_methods"])
            sizing = (row.get("parsed_source") or {}).get("sizing") or {}
            observations.extend(
                record["observation_id"]
                for record in sizing.get("source_measurements", ())
                if record.get("observation_id")
            )
    # The financial runner explicitly constructs inputs from these three payloads.
    financial = {"capex", "revenue", "opex"}
    consumed = tuple(name for name, _ in dispatch.supplied_upstream if name in financial) if (
        product and block == "financial"
    ) else ()
    ledger = product.result.get("ledger") if product and block == "financial" else None
    collector(ExecutionObservation(
        scope=CalculationScope(assessment_id=key, scenario_id=scenario_id),
        attempt_id=dispatch.attempt_id,
        stage=block,
        dispatch=dispatch,
        outcome=outcome,
        complete=product.complete if product else None,
        effective_inputs=effective,
        consumed_upstream=consumed,
        source_observation_ids=tuple(dict.fromkeys(observations)),
        emitted_methods_json=tuple(methods),
        handoff_digest=semantic_digest(payload) if product else None,
        result_digest=semantic_digest(product.result) if product else None,
        financial_ledger_digest=semantic_digest(ledger) if ledger is not None else None,
    ))


def observe_safely(action, *args, **kwargs):
    """Surface instrumentation failures locally and leave stage execution alone."""
    try:
        return action(*args, **kwargs)
    except Exception as exc:
        logger.warning("B09 execution observation failed in %s (%s)", action.__name__, type(exc).__name__)
        return None
