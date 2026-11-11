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


def evaluate_dependencies(scope, graph, receipts, current_inputs, *, legacy_outputs=()):
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
            unknown = []
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
