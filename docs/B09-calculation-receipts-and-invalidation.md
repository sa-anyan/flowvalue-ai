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


## Increment 2 · Lifecycle and freshness safety

The existing isolated runner can keep a prior result while replacing its mutable stage attempt record. The B09 lifecycle adapter models those independently. It is a pure projection from immutable schema-v1 receipts supplied in persisted append order, scoped to one assessment and scenario. The order must come from the future store or caller. Timestamp sorting cannot disambiguate concurrent writes.

- The **latest attempt** is the last unique receipt in the stage history, regardless of outcome. Identical retransmissions of a receipt ID are idempotent. A conflicting payload with the same ID in the same scope is rejected.
- The **active output** is the latest output-bearing ready or partial receipt. A failed or blocked attempt leaves that pointer on the retained output. A partial result may be active as partial. An earlier complete result remains available through `previous_complete_receipt_id`. Selection describes the available output and confers no permission to promote it into an approved baseline.
- `superseded_receipt_ids` contains older output-bearing receipts in append order. Failed and blocked receipts stay in history. The projection never mutates that history or the associated numerical payloads.
- Numerical freshness uses current input/configuration identities and active upstream output digests. Known digest changes are stale. Missing evidence is unknown. A retained output with unverified or changed method identity is unknown unless a known input change already makes it stale. A downstream consumer of a formerly complete result cannot be marked current solely because a replacement partial result has the same digest.
- `provenance` compares recorded method identity to supplied current identity (Increment 3 supersedes the earlier later-attempt fallback). For a direct upstream rerun it compares the original and replacement input/configuration and complete method tuples. A missing original receipt or incomplete method identity yields unknown unless an observed change is already known. Matching means the compared evidence matches. It says nothing about mathematical equivalence, scientific validity or policy approval.
- `approval_status` is explicitly unknown. Stored approval references are retained, with authorization, scope, expiry and invalidation policy outside this evaluator.

| Rerun or read condition | Numerical freshness | Provenance and history |
|---|---|---|
| Same inputs, method and output digest | Current when dependencies are current | Matching evidence when available. The prior receipt is superseded. |
| Upstream inputs changed but its fresh rerun has an identical output | Downstream may remain current | Direct upstream provenance changed. |
| Upstream method changed but its fresh rerun has an identical output | Downstream may remain current | Direct upstream provenance changed. Review is required before treating lineage as equivalent. |
| Upstream output digest changed | Downstream stale | Provenance independently reflects recorded input/method evidence. |
| Failed or blocked attempt after a successful run | Evaluate the retained output against current evidence | The failed or blocked receipt is latest, and the previous successful receipt remains active. |
| Partial after complete | Evaluate the partial output on its own inputs | Earlier complete output remains available. A dependent that had consumed a complete result needs explicit completeness review when the replacement is partial. |
| Original upstream receipt missing but its digest matches a fresh upstream replacement | Current numerically if the other checks pass | Original lineage is unknown. |
| Legacy or named-version fork without a scope-local receipt | Unknown for known historical output | A fork retains original scope and receipt bytes. It acquires no active receipt by inheritance. |

Example stage projection for a failed recalculation after a relevant input edit:

~~~json
{
  "latest_attempt_id": "equipment-run-43",
  "latest_outcome": "failed",
  "active_receipt_id": "equipment-run-42",
  "active_completeness": "complete",
  "previous_complete_receipt_id": null,
  "superseded_receipt_ids": [],
  "freshness": {"state": "stale", "reasons": ["Input or configuration digest changed"]},
  "provenance": {"state": "unknown", "reasons": ["Current or recorded method identity unavailable"]},
  "approval_status": "unknown"
}
~~~

**Engineer 1 review before integration.** Confirm append sequencing under concurrent writes, the frozen inputs and methods captured for failed attempts, criteria for consuming partial outputs, and which method/input comparisons need transitive review. Agree the consumer policy when a digest matches but provenance changed, and keep approval reevaluation separate. Confirm how historical lineage is presented for scenario and named-version forks before wiring live persistence, UI or exports. No production runner, database, report, numerical kernel or B08 policy is changed by this increment. B09 remains **PARTIAL**.


### Increment 2 verification

Same isolated Windows 11 / Python 3.12.14 setup and commands as above, with new temporary database and pytest directories. The test-first run reported **10 passed and 10 failed** in 1.69 seconds because the new lifecycle API did not exist. With the implementation, the focused suite reported **20 passed, 0 failed, 0 skipped, 0 warnings** in 2.33 seconds. The relevant backend selection reported **62 passed, 0 failed, 1 skipped, 1 warning** in 90.98 seconds. The skip was the unavailable private workbook and the warning was the existing Starlette TestClient/httpx deprecation.

The full backend and frontend suites were outside this increment’s verification boundary. The changes are confined to the existing standalone B09 contract, its tests and this note. Live execution and persistence modules were untouched.



## Increment 3 · Receipt integrity and adoption readiness

- The lifecycle projection exposes `active_methods`, `latest_attempt_methods` and independently supplied `current_methods` separately. A later failed or blocked attempt is historical evidence, even when its method tuple is complete. It cannot certify current method identity. Missing or incomplete current evidence leaves the method comparison unknown. A retained output then has unknown numerical freshness unless a known input or upstream change already makes it stale. An ordinary output-bearing attempt can still be numerically current on matching input/output evidence while method provenance remains unknown. There is no read-time fingerprint generation or approval inference.
- Same-scope receipt IDs are immutable and duplicate delivery of identical payloads is idempotent. Projection follows first appearance in append order, independent of execution timestamps. When a referenced receipt is present, it must precede its consumer and match the recorded stage and output digest. Contradictions are rejected, including on superseded attempts. If the original receipt is absent, its lineage remains unknown. A known complete-to-partial replacement cannot certify downstream freshness just by matching the digest. The graph evaluator continues to reject cycles and isolate assessment/scenario scopes.
- Receipt digests and current input/configuration digests must use a lowercase, 64-hex SHA-256 identifier with no extra characters. Non-finite floats are rejected by JSON serialization. Non-finite Decimal values are rejected before the wire codec can turn them into strings. Method fingerprints remain opaque, scheme-tagged observations.
- An unfamiliar stage ID can be retained in immutable history and projected as unknown. A caller must explicitly register it in the graph before it can be evaluated as current. This leaves room for future stages without silently assuming they have no prerequisites.

### Adoption checklist

| Boundary | Engineer 2 implementation point | Engineer 1 review before activation |
|---|---|---|
| Frozen execution inputs | At `run_stage`, bind a stable attempt ID to the queued operation. Freeze the exact state revision, report/workbook revision, config, provider flags and required/optional upstream payloads at the Context construction boundary immediately before runner dispatch. Capture blocked attempts from the prerequisite check without recording a method execution. Keep this pre-dispatch input digest separate from the current post-update `input_fingerprint`. | Agree which data are semantically consumed, including report fallbacks, optional OPEX bases and engine normalization. |
| Stable ID and optimistic append | Generate a unique ID once per attempt and reuse it only to retry delivery of the same immutable payload. At final `Store.put(state, expected)`, propose one compare-and-swap write for receipt append plus result state and active pointer. On a revision conflict reload and reconcile the exact attempt, then retry an identical append or surface the conflict. Assign append sequence at commit, never from wall time. | Review retry/re-execution distinctions and the treatment of results whose input revision changes while running. |
| Storage and retrieval | Validate scope and schema at ingestion, load histories in committed append order, and keep original scope and output references. Start with an additive isolated-store design after retention and transaction ownership are agreed. Test replay, conflicting IDs, concurrent appends and restoration before proposing a storage change. | Agree retention policy and how previous complete outputs are retained alongside failed or partial attempts. |
| Executed methods and B07 provenance | After runner return and before serialization or `_apply`, capture the exact executed G1 method tuples, including preparation and native layers. Record B07 observation and equipment IDs actually consumed where the runner exposes them. Preserve absent metadata as unknown. Record independently verified current method evidence separately. | Confirm the capture layer per engine and whether observed lineage is sufficient to allow equivalent rerun reuse. |
| Active result and partial policy | Map final `product.complete` and outcome into the receipt, evaluate lifecycle on read, and expose latest attempt independently from active output. Preserve historical results and distinguish stale and unknown when projection evidence is insufficient. | Decide whether each consumer may use partial output, how complete-to-partial transitions affect CAPEX and Finance, and when changed provenance blocks reuse despite equal digests. |
| Named versions and scenarios | At `Store.version/load` and Monte Carlo freeze, preserve original history and source scope. Record explicit parent-version or frozen baseline references before new scenario-local capture. Test original snapshot bytes, derived scope and no cross-scenario active receipt inheritance. | Review which historical results may serve as comparison inputs and whether a new scenario requires re-execution. |
| Report/export and approval | At assessment read and export boundaries, project active/superseded receipt IDs, completeness, original provenance, and stale/unknown reasons from the saved history. Preserve approval references as a separate record. | Agree export labels and eligibility, approval scope/expiry and reapproval triggers. Numerical freshness and matching lineage grant no approval. |

No production writes, migrations, per-observation invalidation, UI or export integration land here. **B09 remains PARTIAL** until the integration checklist has been implemented, verified and accepted.


### Increment 3 verification

Windows 11, Python 3.12.14, AI/cloud disabled, isolated SQLite and unique pytest temporary directories.

~~~powershell
python -m pytest backend/tests/test_calculation_receipts.py -q --tb=line -p no:cacheprovider
python -m pytest backend/tests/test_calculation_receipts.py -q -ra --tb=short -p no:cacheprovider
python -m pytest backend/tests/test_calculation_receipts.py backend/tests/test_isolated_stages.py backend/tests/test_stage_connections.py backend/tests/test_sizing_trace_handoff.py backend/tests/test_equipment_resolution.py -q -ra --tb=short -p no:cacheprovider
~~~

Each command also supplied a unique `--basetemp`. The test-first run recorded 21 passed and 14 failed in 2.62 seconds. The existing complete-to-partial guard already passed its new regression. Final focused verification recorded 35 passed, zero failures, skips or warnings in 2.61 seconds. Relevant backend verification recorded 77 passed, zero failures, one private workbook skip and one existing Starlette TestClient/httpx warning in 104.88 seconds. The full backend suite was outside this verification boundary because runner and persistence code were untouched.
