"""Versioned execution receipts and read-only assessment dependency checks."""

from hashlib import sha256
import json
from typing import Annotated, Literal, Self

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from backend.blocks.registry import dependencies, list_blocks
from backend.orchestration.codec import plain

Identifier = Annotated[str, Field(min_length=1, strict=True)]
Digest = Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]


def semantic_digest(payload) -> str:
    """Hash the existing FlowValue wire representation, with a versioned domain."""
    encoded = json.dumps(
        plain(payload), sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return "sha256:" + sha256(b"flowvalue-semantic-v1\0" + encoded).hexdigest()


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class CalculationScope(Contract):
    assessment_id: Identifier
    scenario_id: Identifier | None = None


class MethodIdentity(Contract):
    method_id: Identifier
    method_version: Identifier | None = None
    implementation_fingerprint: Identifier | None = None
    fingerprint_scheme: Identifier | None = None
    execution_layer: Identifier | None = None


class UpstreamReceipt(Contract):
    scope: CalculationScope
    stage: Identifier
    receipt_id: Identifier
    output_digest: Digest


class CalculationReceipt(Contract):
    schema_version: Literal[1] = 1
    receipt_id: Identifier
    scope: CalculationScope
    stage: Identifier
    executed_at: AwareDatetime
    input_revision: int = Field(ge=0, strict=True)
    input_digest: Digest
    configuration_digest: Digest | None = None
    upstream: tuple[UpstreamReceipt, ...]
    methods: tuple[MethodIdentity, ...] = ()
    output_digest: Digest | None = None
    outcome: Literal["ready", "partial", "failed", "blocked"]
    provenance_refs: tuple[Identifier, ...] = ()
    approval_refs: tuple[Identifier, ...] = ()

    @model_validator(mode="after")
    def consistent(self) -> Self:
        stages = [ref.stage for ref in self.upstream]
        if len(stages) != len(set(stages)) or self.stage in stages:
            raise ValueError("Upstream receipt stages must be unique and distinct from this stage")
        if any(ref.scope != self.scope for ref in self.upstream):
            raise ValueError("Upstream receipt belongs to a different calculation scope")
        if (self.output_digest is not None) != (self.outcome in {"ready", "partial"}):
            raise ValueError("Only ready or partial receipts carry an output digest")
        return self


class DependencyStatus(Contract):
    state: Literal["current", "stale", "missing", "unknown"]
    reasons: tuple[str, ...] = ()


def required_stage_graph(state) -> dict[str, tuple[str, ...]]:
    """Read the isolated runner registry. Optional bases are captured per execution."""
    return {block["id"]: tuple(dependencies(block["id"], state)) for block in list_blocks()}


def evaluate_dependencies(
    scope, graph, receipts, current_inputs, *, legacy_outputs=(), uncertainty=None,
):
    """Evaluate one scope using current per-stage (input, configuration) digests.

    Receipt IDs bind the original lineage. A rerun yielding the same upstream
    output digest does not invalidate downstream solely because its ID changed.
    """
    selected = {}
    for receipt in receipts:
        if receipt.scope != scope:
            continue
        if receipt.stage in selected:
            raise ValueError(f"Multiple active receipts for {receipt.stage}")
        selected[receipt.stage] = receipt
    legacy = set(legacy_outputs)
    edges = {stage: set(upstream) for stage, upstream in graph.items()}
    for stage, receipt in selected.items():
        edges.setdefault(stage, set()).update(ref.stage for ref in receipt.upstream)
    for stage in legacy | set(current_inputs) | {key for parents in edges.values() for key in parents}:
        edges.setdefault(stage, set())

    results = {}
    visiting = set()

    def evaluate(stage):
        if stage in visiting:
            raise ValueError(f"Dependency cycle at {stage}")
        if stage in results:
            return results[stage]
        visiting.add(stage)
        parents = {key: evaluate(key) for key in sorted(edges[stage])}
        visiting.remove(stage)
        receipt = selected.get(stage)
        if receipt is None:
            status = DependencyStatus(
                state="unknown" if stage in legacy else "missing",
                reasons=("Legacy output has no versioned receipt",) if stage in legacy else ("No receipt",),
            )
        elif receipt.output_digest is None:
            status = DependencyStatus(
                state="unknown" if stage in legacy else "missing",
                reasons=(f"Execution outcome: {receipt.outcome}",),
            )
        else:
            stale = []
            unknown = list((uncertainty or {}).get(stage, ()))
            observed = current_inputs.get(stage)
            if observed is None:
                unknown.append("Current input identity unavailable")
            elif observed != (receipt.input_digest, receipt.configuration_digest):
                stale.append("Input or configuration digest changed")
            refs = {ref.stage: ref for ref in receipt.upstream}
            for key, parent in parents.items():
                if key not in refs:
                    unknown.append(f"{key}: original upstream receipt reference unavailable")
                    continue
                upstream = selected.get(key)
                if parent.state == "stale":
                    stale.append(f"{key}: upstream is stale")
                elif upstream and upstream.output_digest and upstream.output_digest != refs[key].output_digest:
                    stale.append(f"{key}: upstream output digest changed")
                elif parent.state != "current":
                    unknown.append(f"{key}: upstream is {parent.state}")
            status = DependencyStatus(
                state="stale" if stale else "unknown" if unknown else "current",
                reasons=tuple(stale + unknown),
            )
        results[stage] = status
        return status

    for stage in edges:
        evaluate(stage)
    return results


class ProvenanceStatus(Contract):
    state: Literal["matching", "changed", "unknown"]
    reasons: tuple[str, ...] = ()


class StageLifecycle(Contract):
    latest_attempt_id: Identifier | None = None
    latest_outcome: Literal["ready", "partial", "failed", "blocked"] | None = None
    active_receipt_id: Identifier | None = None
    active_completeness: Literal["complete", "partial"] | None = None
    previous_complete_receipt_id: Identifier | None = None
    superseded_receipt_ids: tuple[Identifier, ...] = ()
    freshness: DependencyStatus
    provenance: ProvenanceStatus
    approval_status: Literal["unknown"] = "unknown"


def _known_methods(methods):
    return bool(methods) and all(
        m.method_version and m.implementation_fingerprint
        and m.fingerprint_scheme and m.execution_layer for m in methods
    )


def evaluate_lifecycle(
    scope, graph, history, current_inputs, *, current_methods=None, legacy_outputs=(),
):
    """Project one scope from immutable receipts in persisted append order."""
    from collections import defaultdict

    by_id = {}
    attempts = defaultdict(list)
    for item in history:
        if item.scope != scope:
            continue
        previous = by_id.get(item.receipt_id)
        if previous is not None:
            if previous != item:
                raise ValueError(f"Conflicting immutable receipt: {item.receipt_id}")
            continue
        by_id[item.receipt_id] = item
        attempts[item.stage].append(item)

    latest = {stage: runs[-1] for stage, runs in attempts.items()}
    outputs = {
        stage: [item for item in runs if item.output_digest is not None]
        for stage, runs in attempts.items()
    }
    active = {stage: runs[-1] for stage, runs in outputs.items() if runs}
    provenance = {}
    uncertainty = defaultdict(list)
    for stage, item in active.items():
        changed = []
        unknown = []
        expected = (current_methods or {}).get(stage)
        if expected is None and latest[stage] != item:
            expected = latest[stage].methods
        if not _known_methods(item.methods) or not _known_methods(expected):
            unknown.append("Current or recorded method identity unavailable")
            if latest[stage] != item:
                uncertainty[stage].append("Retained output method identity is unverified")
        elif item.methods != tuple(expected):
            changed.append("Current method identity differs")
            uncertainty[stage].append("Current method identity differs from active output")
        for ref in item.upstream:
            original = by_id.get(ref.receipt_id)
            replacement = active.get(ref.stage)
            if original is None or original.stage != ref.stage or original.output_digest != ref.output_digest:
                unknown.append(f"{ref.stage}: original receipt unavailable")
                continue
            if replacement is None or original == replacement:
                continue
            if (original.input_digest, original.configuration_digest) != (
                replacement.input_digest, replacement.configuration_digest,
            ):
                changed.append(f"{ref.stage}: upstream inputs or configuration changed")
            if not _known_methods(original.methods) or not _known_methods(replacement.methods):
                unknown.append(f"{ref.stage}: upstream method identity unavailable")
            elif original.methods != replacement.methods:
                changed.append(f"{ref.stage}: upstream method identity changed")
            if original.outcome == "ready" and replacement.outcome == "partial":
                uncertainty[stage].append(f"{ref.stage}: complete upstream output replaced by a partial output")
        provenance[stage] = ProvenanceStatus(
            state="changed" if changed else "unknown" if unknown else "matching",
            reasons=tuple(changed + unknown),
        )

    selected = (active.get(stage, attempt) for stage, attempt in latest.items())
    statuses = evaluate_dependencies(
        scope, graph, selected, current_inputs,
        legacy_outputs=legacy_outputs, uncertainty=uncertainty,
    )
    views = {}
    for stage, status in statuses.items():
        item, attempt = active.get(stage), latest.get(stage)
        superseded = outputs.get(stage, [])[:-1]
        previous_complete = next(
            (prior.receipt_id for prior in reversed(superseded) if prior.outcome == "ready"),
            None,
        )
        views[stage] = StageLifecycle(
            latest_attempt_id=attempt.receipt_id if attempt else None,
            latest_outcome=attempt.outcome if attempt else None,
            active_receipt_id=item.receipt_id if item else None,
            active_completeness=("complete" if item.outcome == "ready" else "partial") if item else None,
            previous_complete_receipt_id=previous_complete,
            superseded_receipt_ids=tuple(prior.receipt_id for prior in superseded),
            freshness=status,
            provenance=provenance.get(stage, ProvenanceStatus(state="unknown", reasons=("No active receipt",))),
        )
    return views
