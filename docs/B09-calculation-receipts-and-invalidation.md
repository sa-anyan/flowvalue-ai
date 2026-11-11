# B09 · Calculation receipts and dependency invalidation

**Acceptance: PARTIAL.** This increment implements a versioned contract, a registry-backed dependency evaluator and SQLite round-trip tests. Live execution, storage conventions and reporting adoption require a separate reviewed increment.

## Current architecture

- [Registry](../backend/blocks/registry.py) declares stage IDs and hard prerequisites. An arrow below means the source is a direct prerequisite. The adapter calls the existing registry function. It owns no duplicate stage list.
- [Isolated stage execution](../backend/blocks/execution.py) records one mutable lifecycle entry per stage in `stage_runs`: pipeline, producer, status, AI flag, execution flag, start/completion times, elapsed time and, on success, input/output hashes and completeness. It has no immutable receipt ID or explicit upstream receipt IDs. The input hash combines the stage-specific configuration slice and upstream output hashes. Successful hashes are taken after updates are applied. That timing is a separate design concern from recording the exact frozen execution inputs.
- OPEX has required Engineering data and consumes CAPEX and Revenue only when fresh. Their availability and output hashes are included in the existing OPEX input slice. The execution context can also fall back to the Engineering report when the direct upstream payload has none. A fallback or consumed observation belongs in the future execution capture. This increment leaves the scheduler’s hard edges intact.
- `fresh` checks input hashes, saved payload presence and recursively fresh prerequisites. `refresh` retains prior result payloads and marks stale display results. Equipment can use an earlier saved costing result as a stale view. That mechanism uses stage-level hashes. It cannot establish which observation an old equipment line consumed.
- [B07](B07-engineering-identities.md) records workbook revisions, observation IDs, equipment record keys and reviewed physical identities. [Sizing trace projection](../backend/dashboard_reporting/sizing_trace.py) retains executed preparation and nested method metadata and exposes legacy rows as unversioned. These are provenance inputs for a future receipt writer. A method fingerprint does not identify the selected inputs or prove suitability.
- [SQLite store](../backend/orchestration/store.py) saves assessment JSON with optimistic revision writes. A named version freezes JSON, and reopening creates a new editable assessment ID while preserving original result metadata. The [API](../backend/api/app.py) projects saved state into history, snapshot and HTML report responses. Those paths do not create calculation receipts.
- [Monte Carlo](../backend/scenarios_and_uncertainty/monte_carlo/service.py) freezes a baseline revision, job/snapshot IDs, settings and a source-tree hash, then uses the connected pipeline for evaluations and separate [exports](../backend/scenarios_and_uncertainty/monte_carlo/exports.py). That job fingerprint does not replace G1 method metadata or a per-stage receipt. This increment does not wire scenario jobs into the graph.

~~~mermaid
flowchart LR
  E[Engineering data] --> Q[Equipment]
  Q --> C[CAPEX]
  E --> R[Revenue]
  E --> O[OPEX]
  C -. optional when consumed .-> O
  R -. optional when consumed .-> O
  C --> F[Financial]
  R --> F
  O --> F
~~~

## Receipt contract and canonical digest

[Contract and evaluator](../backend/orchestration/calculation_receipts.py) use an immutable Pydantic schema. A receipt captures one declared assessment/scenario scope, a stage, receipt ID, timezone-aware execution timestamp, input revision, input and optional configuration digests, scoped upstream receipt references, observed method records, output digest and execution outcome. Provenance and approval references are optional lists. Approval records and the rules granting approval are separate. Failed and blocked executions have no output digest. Ready and partial executions carry one.

`semantic_digest` hashes the FlowValue JSON wire representation under domain `flowvalue-semantic-v1`. It uses sorted keys, compact JSON, UTF-8, and rejects non-finite values. Ordered sequences retain their order. The existing codec converts Decimal/date values to strings, so a Decimal and its exact serialized text have the same digest. Different Decimal text, including scale, can yield different digests. Callers must provide schema-normalized payloads with unambiguous string keys after wire serialization. Receipt IDs, timestamps and storage revision numbers remain lineage. They enter semantic identity only when the caller explicitly includes a value that the calculation consumed. Method identity affects a digest when included in its semantic payload. A read must never hash currently loaded engineering code to fill an absent historical fingerprint.

Example receipt shape, with fixture digests abbreviated for readability:

~~~json
{
  "schema_version": 1,
  "receipt_id": "equipment-run-42",
  "scope": {"assessment_id": "study-a", "scenario_id": null},
  "stage": "equipment",
  "executed_at": "2026-01-01T12:00:00Z",
  "input_revision": 7,
  "input_digest": "sha256:<64 hex digits>",
  "configuration_digest": null,
  "upstream": [{
    "scope": {"assessment_id": "study-a", "scenario_id": null},
    "stage": "engineering_data",
    "receipt_id": "parse-run-8",
    "output_digest": "sha256:<64 hex digits>"
  }],
  "methods": [],
  "output_digest": "sha256:<64 hex digits>",
  "outcome": "ready",
  "provenance_refs": ["observation:example"],
  "approval_refs": []
}
~~~

Empty methods mean the implementation identity is unavailable. Receipt schema version and method version are independent.

## Read-only dependency evaluation

The caller supplies active receipts and current semantic input/configuration digests for one scope. The evaluator combines the registry’s direct prerequisites with upstream references captured by each receipt. It rejects cycles and multiple active receipts for one stage in the scope. Receipt references must belong to the same assessment and scenario. A future scenario fork would need to record its frozen baseline as source lineage before capturing scenario-local references.

| State | Meaning |
|---|---|
| Current | The recorded input and configuration digests match and all captured upstream outputs are current and match. Partial outputs can be current for their inputs while remaining partial. |
| Stale | The input/configuration identity or a captured upstream output changed, or a captured upstream result is stale. Reasons name the failed comparison or immediate upstream stage. |
| Missing | There is no output-bearing receipt or known legacy output for this stage. |
| Unknown | A legacy output has no versioned receipt, current evidence is absent, or original dependency or upstream evidence is unavailable. |

An upstream receipt ID records original lineage. Re-execution with the same output digest does not alone invalidate downstream. Optional inputs not captured in an old run need an explicit change to the caller-supplied semantic input identity when they become applicable. Unaffected receipt payloads stay intact. Evaluation returns statuses and reasons without executing, replacing or storing a result. The adapter does not infer that every costing line consumed every workbook observation. The coarse production Engineering stage currently carries a whole-report dependency.

## Persistence, adoption and remaining risks

The SQLite test stores a fixture receipt in the existing JSON envelope and reopens a named version. Stored snapshot bytes, original receipt scope, and results are preserved. A legacy read returns the original fields. Passing known legacy output names to the adapter yields unknown without assigning method metadata. There is no production schema migration or receipt write path in this increment.

Before wiring production, review with Engineer 1:

1. Confirm the execution capture point, input normalization and provenance for each calculator and optional basis. Confirm which source observations, equipment keys and method layers can be recorded as consumed.
2. Agree which stage output is the semantic handoff and when an identical rerun may be reused. Define behavior for changed implementation metadata with identical numerical output, and for partial/failed executions alongside a previous result.
3. Confirm how a named-version fork and a scenario freeze inherit lineage. A live scenario must not acquire references from another scenario or a subsequently edited baseline.
4. Agree immutable receipt retention, optimistic writes, legacy read states and how each report/export labels unknown or stale results. Test staged parity before changing existing freshness consumers.

Broader wiring, per-observation invalidation, cloud storage parity and receipt-aware exports remain pending. Existing pricing, financial and Monte Carlo policies remain outside this increment.


## Verification

Windows 11, Python 3.12.14 with default encoding, AI/cloud disabled and temporary SQLite and pytest paths. Both commands used a unique `--basetemp`.

~~~powershell
python -m pytest backend/tests/test_calculation_receipts.py -q -ra --tb=short -p no:cacheprovider
python -m pytest backend/tests/test_calculation_receipts.py backend/tests/test_isolated_stages.py backend/tests/test_stage_connections.py backend/tests/test_sizing_trace_handoff.py backend/tests/test_equipment_resolution.py -q -ra --tb=short -p no:cacheprovider
~~~

- Focused: 10 passed, 0 failed, 0 skipped, 0 warnings in 1.99 seconds.
- Relevant backend: 52 passed, 0 failed, 1 skipped, 1 warning in 97.47 seconds. The private workbook fixture was unavailable. The warning was the existing Starlette TestClient/httpx deprecation. The selection includes equipment-to-finance propagation and manual-price Monte Carlo parity.
- This increment changes only backend contract/test files and documentation. Frontend and the full backend suite were outside this verification selection.
