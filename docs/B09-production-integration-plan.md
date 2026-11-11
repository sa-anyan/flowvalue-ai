# B09 Increment 4 · Production integration plan

**Status: PARTIAL.** This is a proposal for review. Repository observations refer to B09 tip `d8c65cd`, which includes the sizing-trace follow-ups. The standalone contract is in [B09 receipts and invalidation](B09-calculation-receipts-and-invalidation.md). No Engineer 1 decision is assumed approved.

## Verified interface map

| Boundary | Existing function and data | Proposed integration point |
|---|---|---|
| Dispatch and input preparation | [execution.py](../backend/blocks/execution.py) `queue_stage` and `run_stage` manage the queue, prerequisite check and `Context`. [preparation.py](../backend/blocks/preparation.py) `prepare_stage` is a separate preparation path. [shared.py](../backend/blocks/shared.py) `proposal`, `operating_proposal`, `translate_inputs` and `basis_and_schedule` can resolve effective settings after dispatch. | Freeze the initial context immediately before `get_runner(block)(ctx)`. Capture effective inputs after preparation, at engine entry. A preparation call alone is not a calculation. |
| Completion and freshness | `_apply` applies updates. `stage_outputs[block]` stores `Product.payload`, `results.stages[block]` stores the result and issues, and `stage_runs[block]` stores mutable lifecycle information. `input_fingerprint` uses `_inputs` and required upstream hashes. OPEX hashes fresh optional bases inside its input slice. `fresh` and `refresh` retain stale results and enforce the current scheduling behavior. | Capture receipt facts before final `Store.put`. Keep the frozen execution digest separate from the existing post-update fingerprint. Initially compare the new evaluation in shadow mode. |
| SQLite and cloud | [Store](../backend/orchestration/store.py) `get/put/version/load` uses JSON text and revision-conditional writes. [CloudStore](../backend/cloud/store.py) uses owner-filtered caller-token PostgREST and revision-conditional PATCH. [Cloud schema](../backend/cloud/schema.sql) applies ownership RLS. A cloud response is capped at 16 MiB. | Define one logical append-and-publish operation for both stores. Avoid a second network request to append a receipt after publishing a result. |
| Named versions and scenarios | Both stores snapshot state and reopen via `load` into a new assessment ID. [Monte Carlo service](../backend/scenarios_and_uncertainty/monte_carlo/service.py) `start/work` freezes the baseline revision, settings, job and snapshot IDs and a source-tree hash. Its evaluator uses the [connected pipeline](../backend/orchestration/pipeline.py) `run`, which bypasses the isolated runner. | Preserve original receipt scope on historical reads. Instrument scenario capture independently, with a frozen baseline reference and scenario-local receipts. |
| Reports and exports | [API](../backend/api/app.py) `get/reopen/study_report/study_snapshot/monte_export` builds read responses. [Study report](../backend/dashboard_reporting/study_report.py) uses `render_study/render_partial`; [sizing trace](../backend/dashboard_reporting/sizing_trace.py) exposes saved method evidence; [Monte Carlo export](../backend/scenarios_and_uncertainty/monte_carlo/exports.py) serializes saved job results. | Project receipt status and recorded provenance from saved state before presentation or currency formatting. Keep existing stale labels and numeric projections during shadow verification. |

## Stage capture map

Verified inputs and outputs are described below. The final column is proposed. Capture references only when consumption is established, retaining coarse evidence for unresolved paths. Use engine-provided identity where available. A label, parser version, selected model or Git SHA alone is not a G1 implementation fingerprint.

| Stage and executed entry | Verified inputs and config | Verified output and completion | Proposed observation/method capture |
|---|---|---|---|
| [Engineering data](../backend/blocks/engineering_data/runner.py) `calculate → parse` | Workbook bytes and filename, optional AI review using description and provider, saved register edits replayed after extraction. No required stage. | Report and source-cell payload. Absent workbook raises `DataRequired`; optional review can fail while extraction remains available. | Capture workbook content revision, actual parser/review metadata and edit IDs. Treat emitted B07 observation IDs as output lineage, not as pre-existing consumed inputs. |
| [Equipment](../backend/blocks/equipment/runner.py) `prepare/calculate` and [calculate_equipment](../backend/blocks/equipment/calculation.py) | Engineering report, equipment plan, quantity and scope choices, conversion inputs and translation policy. Reconciliation, scope expansion, optional matching and price repair can change the effective inputs. | Costing total, sizing rows, report and unpriced list. Completeness follows the runner's unpriced check. | Bind B07 equipment keys, measured cells/streams actually selected in sizing and conversion, assumptions, manual prices and costing curve. Keep executed preparation and nested G1 method tuples verbatim. Capture each executed attempt of a repaired calculation or declare earlier attempts unavailable. |
| [CAPEX](../backend/blocks/capex/runner.py) `calculate → calculate_capital` | Equipment total and unpriced coverage, eligible scoped lines, effective CAPEX plan including optional proposal, translation and description. | Capital result, completeness flag and screening comparisons. Unpriced equipment or absent total gives incomplete coverage. | Reference equipment receipt and included costing record keys. Retain observed capital model and factor provenance. Carry source lineage through the equipment result. |
| [Revenue](../backend/blocks/revenue/runner.py) `calculate → _revenue_project → calculate_revenue` | Engineering report, effective operating proposal, commercial intent/lines, avoided costs, description and approval, translated basis and operating hours/ramp. Approval questions and invalid basis can block output. | Revenue, schedule and effective config; completion is based on engine issues. | Record selected stream/observation bindings where the builder can expose them, payment IDs and saved approval reference. Record executed commercial method evidence only when emitted. |
| [OPEX](../backend/blocks/opex/runner.py) `calculate → _costs_for_year/_opex` | Engineering report, annual schedule and effective operating costs, basis, fixed phasing, optional fresh CAPEX and Revenue. Revenue can supply sales-dependent expenses and avoided costs. | Annual years, config and complete flag; any missing annual cash OPEX or pending item makes it incomplete. | Capture per-year quantity sources and expense line IDs where proven. Record which optional outputs were supplied and which factor lines consumed them. Keep operating method and phasing evidence separate. |
| [Financial](../backend/blocks/financial/runner.py) `calculate → prepare_study_financials → calculate_financials` | CAPEX, Revenue and OPEX outputs, translation and finance policy. Blocks on incomplete CAPEX/OPEX or mismatched CAPEX/Revenue basis. | Display ledger and metrics in `Product.result`. The existing stage payload contains `financial_inputs` only, so its hash does not attest the display ledger. | Bind the three receipts and exact canonical finance inputs, and record both handoff and ledger digests. Use saved upstream lineage for source observations. Capture executed financial method identity only if available. |

Map final product with `complete=True` to ready, and a product with `complete=False` to partial. Prerequisite denial is blocked with no executed method. A runner can raise `DataRequired` after dispatch or fail validation while applying updates. The existing lifecycle collapses those outcomes into `data_required`. Future capture should preserve execution attempted, reason, and separately classify exception vs domain block once agreed. No failed or blocked attempt publishes a new output digest. Receipt history and active/retained output pointers are distinct.

## Dependencies and invalidation

~~~mermaid
flowchart LR
  W[Workbook, process, register edits] --> E[Engineering data]
  E --> Q[Equipment]
  E --> R[Revenue]
  E --> O[OPEX]
  Q --> C[CAPEX]
  C -. optional when consumed .-> O
  R -. optional when consumed .-> O
  C --> F[Financial]
  R --> F
  O --> F
~~~

Solid stage edges come from the registry. The runner can fall back to the engineering report when the direct upstream payload has none. Record a consumed fallback as provenance during capture. It is not an additional hard edge today.

| Changed input | Safe current granularity | Candidate refinement |
|---|---|---|
| Workbook, source cell, register edit | Whole engineering report. Equipment, Revenue and OPEX depend on it. CAPEX and Financial follow transitive dependencies. | Sizing has candidate per-equipment measurements and B07 record keys. Use those only after accounting for shared streams, duplicate reconciliation, selected conversions and provider fallbacks. Otherwise keep the coarse report dependency. |
| Equipment plan or translation | Equipment stage and its consumers. Translation also appears in other stage input slices. | Track keyed equipment consumption and scoped capital lines after the contracts capture all relevant config. |
| Revenue payment, schedule or authority | Revenue stage and Finance. OPEX tracks availability of fresh Revenue even when some expense lines are independent. | Per-line/year coverage is feasible when commercial bindings and sales/savings consumers are explicit. Preserve current whole-stage behavior during rollout. |
| OPEX rates, staffing or finance assumptions | Whole OPEX or Financial stage according to `_inputs`, including shared schedule and basis. | Track source consumption by cost line/year in shadow evaluation. Keep annual aggregation coarse until completeness and parity are proven. |

A missing consumed-input trace is unknown or coarse. A fresh replacement with identical handoff digest can preserve numerical freshness while provenance changes. Stale, unknown, completeness and approval are separate. Never recalculate on read or change current freshness behavior during the initial increments.

## Proposed persistence

- Allocate an opaque attempt ID once. Serialize the immutable receipt canonically with its scope, frozen input references and independent observed method evidence. Same ID and identical bytes is an idempotent replay. Same ID and different payload is a conflict. Assign monotonic append order at successful commit, independent of timestamps.
- Publish receipt append, active pointer and new result atomically against the expected assessment revision. SQLite can use a single transaction. Cloud must use a single revision-conditional update for a bounded envelope or a reviewed owner-scoped transactional RPC for separate storage. Separate PATCH and POST calls cannot satisfy this invariant. Retry after reloading only if the frozen basis and identity still match, otherwise preserve/report the conflict without publishing a stale output. Decide how to record conflicted attempts before production activation.
- Retrieve histories in append order by original scope and retain superseded receipts plus referenced output artifacts. Start with a bounded assessment-local pilot design and size tests. If archival is needed, require stable references and named-version-aware retention before adopting separate storage. Do not silently prune referenced history. Cloud validation compares canonical content because JSONB does not promise original text byte ordering. SQLite version reads must leave stored bytes unchanged.
- Named versions retain original receipt IDs, scope and references. Editable forks keep lineage but acquire no active receipt in the new scope. Freeze scenario inputs by baseline assessment revision and snapshot ID. Scenario executions keep separate receipt IDs and cannot acquire a newer baseline implicitly. Legacy snapshots retain existing fields and render unavailable receipt/method evidence as unknown. There is no migration or backfill in this plan.

## Recommended implementation order

| Increment | Expected files | Acceptance and numerical parity | Review gate and rollback |
|---|---|---|---|
| 4A · Capture in memory | `backend/blocks/execution.py`, `models.py`, `shared.py`, per-stage runner adapters and a new capture test module. | Test exact pre-dispatch and effective inputs, optional OPEX bases, source/method identity, blocked and failed paths, and incomplete products. Compare stage payloads, totals, ledger and current freshness to fixed baseline fixtures with capture enabled and disabled. | Decisions 1 and 2. Keep the collector injectable and off by default. Remove it without touching stored data. |
| 4B · Atomic isolated persistence pilot | `backend/orchestration/store.py`, `backend/cloud/store.py` or a transaction adapter, persistence tests. Any migration is a separately approved follow-up. | Test optimistic conflict, append order, replay, owner isolation, failure with retained output, JSON size bounds, named-version restore and SQLite/cloud contract parity with mocked PostgREST before an isolated cloud test. Stored numerical results and snapshots remain identical. | Decisions 3 and 4. Keep legacy readers and gate writes; disable receipt writes without deleting history. |
| 4C · Shadow invalidation and scenario lineage | `backend/orchestration/calculation_receipts.py`, `backend/blocks/execution.py`, `backend/scenarios_and_uncertainty/monte_carlo/service.py` and shadow tests. | Verify direct/transitive invalidation, unrelated observations, unknown dependencies, optional bases, equivalent reruns, partial/failed transitions and frozen scenarios. Compare existing freshness, exact stage totals, scenario samples and central results; explain disagreements before enabling any behavior change. | Decisions 1, 2, 4 and 5. Keep existing freshness authoritative. Turn off shadow projections independently. |
| 4D · Read/export adoption | `backend/api/app.py`, `backend/dashboard_reporting/study_report.py`, `backend/scenarios_and_uncertainty/monte_carlo/exports.py` and report tests. UI changes require their own review. | Verify current, stale, unknown and legacy output labels; serialize original method evidence; compare JSON/HTML/CSV/XLSX values and scope against saved outputs. Confirm no writes or engine dispatch on read. | Decisions 4, 5 and 6. Keep metadata additive and retain the existing export path behind a compatibility option until accepted. |

## Six unresolved decisions for Engineer 1

1. **Consumed inputs and method capture.** Agree engine-specific source bindings, shared report fallbacks, normalized config and which executed layers count as receipt evidence.
2. **Semantic output and equivalent reruns.** Agree handoff versus display digests, digest-preserving changes in method provenance and the distinction between numerical freshness and permission to reuse.
3. **Append and retention semantics.** Agree retry versus re-execution, race and conflict outcomes, immutable output retention and what a superseded receipt must still reference.
4. **Named-version and scenario lineage.** Agree how a fork/frozen scenario references the original, when it must re-execute and how to keep existing exports comparable.
5. **Partial and failed result consumption.** Agree which consumers may use partial output, required coverage, and retained-output behavior for failed/blocked attempts. Do not promote partial totals into approved results implicitly.
6. **Read/export and approval boundaries.** Agree stale/unknown labels and export eligibility, approval scope, expiry and reevaluation triggers. Preserve authority separately from calculation receipts.

Engineer 2 can prepare capture instrumentation, schema validation, scope isolation, fixture replay, and store contract tests. Consumer eligibility, calculation meaning and approval rules stay behind these review gates.
