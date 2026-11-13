# Phase 2 implementation readiness

Baseline: Engineer 2 development at 9514494314fe84885363e812673e105b59f4e243. PR #9 supplies this checkpoint. PRs #3, #6, #9 and #21 were open and unmerged at inspection. The B09 branch was consulted as design and prototype evidence. Neither its changes nor PR #21 are in this baseline.

Requirements below follow [the captured formal roadmap](audits/phase0/evidence/g0_reconciliation/roadmap_paragraphs.json), paragraphs 125-166. A supported path or a passing fixture is evidence for that path. Milestone acceptance requires Engineer 1 sign-off.

| Milestone | Existing implementation and verification | Missing capability or evidence | Smallest acceptance fixture and independent work |
|---|---|---|---|
| M2.1 Canonical project and stream schema | BalanceReport, Entity, Evidence and Connection in backend/ingestion/balance/models.py cover observed material and energy properties, compositions, connections and equipment. Sizing plans, CAPEX/OPEX, Revenue and Finance have separate contracts. test_engineering_identity and test_sizing_cross_file verify selected identity and layout paths. | Functionality: no single versioned project envelope connects process units, equipment conditions, schedules, engineering evidence, project costs, contracts and financial results. Verification: three distinct layouts plus a manual process through the same project read boundary, including incompatible units and schedules. | One process expressed across three workbook layouts and manually, with one missing value and one genuine zero. Assert equivalent source-backed facts, identity links, and unchanged input bytes. Domain ownership and economic timeline mapping precede canonical writes. |
| M2.3 Source provenance and assumption register | Workbook SHA-256, observation identities and optional predecessors, B07 manual/recovered evidence, register.register and service.edit. test_engineering_identity covers stable manual revisions, historical keys and read compatibility. G1 method capture is in PR #9. | Functionality: plan metadata is inherited by path, with gaps in per-field evidence binding and approval trace across stage/scenario/report boundaries. Verification: critical field coverage and negative tests for unreviewed replacements, missing values and conflicting sources. | One source fact, one explicit user change, one unresolved value and an attempted unapproved replacement. Verify source, rationale, lock, historical values, and unchanged workbook. Improve read-only diagnostics before considering authority changes. |
| M2.4 Dependency graph and recalculation | blocks.registry.dependencies declares direct prerequisites. execution.input_fingerprint and fresh check hashes transitively. execution.refresh marks stale, and run_stage dispatches explicitly. OPEX observes optional CAPEX and Revenue availability. test_isolated_stages covers stale blockers and optional transitions. | Functionality: no live immutable receipt lineage, consumed-observation edges or granular invalidation. Verification: connected edit propagation, explicit rerun and retained unrelated output on this baseline. | G2 candidate changes reviewed vessel hold-up from 24 h to 48 h, checks independent volumes, stale/ready transitions and downstream results, and retains the existing Revenue result. Next verify optional and failure transitions in B09 shadow mode. |
| M2.5 Migration and version compatibility | SQLite Store and CloudStore have revision guards and named-version forks. B07 legacy identity projection is additive. test_phase0_version_protection and test_engineering_identity cover stale writers, snapshots and legacy reads. B09 has standalone journal and shadow evidence on its separate branch. | Functionality: no shared versioned project migration path or live receipt transaction. Verification: failed conversion recovery, exact replay, CloudStore parity, named/scenario lineage with receipts and documented conversion for unsupported versions. | Use one legacy version and one proposed-format snapshot. Inject a write failure, reject a stale writer, replay identical bytes, reopen/fork and compare originals and workbook digests. Keep the production format unchanged until approved. |

## Acceptance trace

- **155 / three workbooks and a manual process.** test_sizing_cross_file covers rows, columns and units-row fixtures in XLSX/XLSM/XLS. A shared manual-vs-workbook project fixture is still needed.
- **156 / repeated tags, missing properties, conflicting units and schedules, approved edits.** test_engineering_identity covers identity and evidence distinctions, test_sizing_cross_file covers missing heat units, test_monetary_timeline_contracts covers standalone schedule validation, and the G2 candidate covers an explicit reviewed edit. Same-tag costing and scenario acceptance are in PR #21. A production fixture for conflicting schedules and incompatible units across adapters remains needed.
- **157 / independent mutation arithmetic.** The G2 candidate independently expects 24 and 48 m3, then checks downstream direction and freshness. Independent exact CAPEX/OPEX/Finance expected amounts remain a sign-off requirement.
- **158, 165 / failed migration and history.** Named-version protection and legacy read tests exist. Failed project-format conversion and cloud recovery remain unverified.
- **160 / every critical quantity sourced or assumed.** Workbook evidence, the assumption register and method traces provide partial coverage. A critical-field inventory and automated assertion for each handoff are missing.
- **161 / supported dependencies recalculate.** Isolated-stage tests and the G2 candidate exercise the existing explicit-run model. Conditional, scenario and receipt adoption paths still require coverage.
- **162 / approved assumptions protected.** service.edit records a rationale and locks edits. Revenue approval and isolated-stage tests verify specific paths. Cross-domain authority and all writer-path coverage remain open.
- **163 / missing versus zero.** Evidence permits null and numeric zero. Standalone B08 tests cover monetary semantics. Cross-domain saved round-trip remains required.
- **164 / original workbook unchanged.** G2 compares stored workbook bytes before and after the edit and reruns. Extend to every accepted import layout.
- **166 / G2.** The candidate is one SQLite, no-AI, explicitly recalculated engineering change. It does not replace the full acceptance matrix or Engineer 1 sign-off.

## Dependencies and integration order

1. Build additive contract tests and read-only diagnostics on PR #9's baseline. PR #9 includes identity, method evidence and standalone B08 contracts. It remains an integration dependency.
2. Review PR #6's B07 identity decisions and PR #21's costing/Monte Carlo implementation together. Use PR #21's distinct, alias, split and AB cases in the integrated G2 suite after authorized integration. Keep all four PRs untouched during independent verification.
3. Apply PR #3's approved economic semantics only when its production integration is authorized. It gates shared monetary basis, operating schedules and financial comparisons. A prototype contract is not approval to change production.
4. Review the B09 package below. Run a production-shaped shadow trial before considering authority changes. Obtain Engineer 1 acceptance with independent downstream expected totals, both stores and browser evidence where applicable.

## M2.5 / next B09 review package

Existing local B09 documents on engineer-2/b09-versioning are docs/B09-production-integration-plan.md and docs/B09-acceptance-and-decisions.md. They record six agreed policies. Activation and closure approvals remain pending. Confirm those policies are carried into the eventual integrated branch without changing current behavior.

| Step | Boundary and acceptance |
|---|---|
| 1. Pre-commit capture and atomic adapter | At blocks.execution.run_stage freeze the dispatch input and collect actual method/observation evidence. Replace the post-commit best-effort callback for any future live write. Prototype against the Store.put and CloudStore.put compare-and-swap boundaries. Test same-transaction result and receipt, exact replay, stale writer and interruption. Keep cloud work in an approved isolated test environment. |
| 2. Read-only shadow with lineage | Bind immutable attempt scope and original receipt lineage through Store.version/load, CloudStore.version/load and scenario snapshots. Compare optional OPEX basis transitions, equal output with changed provenance, failed retained output and partial results. Legacy without receipts remains unknown in shadow. Compare historical bytes before and after reads. |
| 3. Read/export projection | Add labels and original method references only after saved receipt parity. Reconcile JSON, HTML, CSV and XLSX. Preserve partial and previous results and separate approval evidence. |
| 4. Activation gate | Obtain approval for transaction deployment and freshness authority separately. Run exact numerical and saved-byte parity with the feature enabled and disabled. Before activation, roll back by disabling the adapter and using the existing snapshots and freshness authority. |

No production receipt writes, migration or authority changes are included in this package.

## Executed evidence and review branches

- [Draft PR #24](https://github.com/sa-anyan/flowvalue-ai/pull/24) adds the three-layout stream regression.
- [Draft PR #23](https://github.com/sa-anyan/flowvalue-ai/pull/23) adds the zero/unresolved provenance regression.
- [Draft PR #22](https://github.com/sa-anyan/flowvalue-ai/pull/22) adds the G2 candidate.
- Windows, AI and cloud disabled, temporary SQLite and a unique pytest base directory. The G2/isolated-stage/version selection returned 15 passed. The stream/provenance/identity/cross-file selection returned 81 passed. Each selection emitted one existing Starlette TestClient/httpx deprecation warning. Neither selection skipped tests.
- The changes close verification gaps. The missing unified schema, cross-stage approval and receipt adoption functionality require shared interfaces or activation approval.
