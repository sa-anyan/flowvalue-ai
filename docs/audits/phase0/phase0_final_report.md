# Phase0 final Engineer1 report

**G0 BLOCKED — required evidence and the actual official exit conditions are unavailable.**

This is an evidence-backed baseline audit of `FlowValue-latest` at **74f364d**, completed locally on **10 November2026**. No Phase1 implementation, calculation-policy changes, deployment, production assessment edits or paid AI/research calls were performed. Historical acceptance documents remain intact.

## Current status

The current product contains connected deterministic sizing/costing, CAPEX, OPEX, the authoritative six-category Revenue Box, an annual financial ledger, report/currency views and Monte Carlo recalculation. Frontend production build and45 tests passed. This is executable preliminary engineering software; completeness/accuracy for arbitrary industrial files, real AI selection and industrial validation are not demonstrated. The Scenario & Sensitivity workspace is a scaffold.

The original full backend suite yielded **1,717 passed, 1 failed, 2 skipped**, plus **367 passing subtests**. The documented unittest command alone passes336 and misses much of the pytest suite. Two new synthetic version-protection tests passed. The existing failure was preserved: commercial-year schedule mismatch prevents full Monte Carlo economic/financial completion despite successful equipment pricing.

## Engineering calculations and verification

- **12** explicitly registered preliminary sizing methods; their dimensional contracts/equations are listed as `ENG-SIZE-01`–`12`.
- **236** statically discovered numerical function candidates plus those12 registry-contract rows = **248 engineering-register rows**. Helpers, duplicated entry points and delegates are included;248 is not a count of distinct physical models.
- **112/236** candidates have a discovered direct module reference in tests;124 do not. This is static linkage, not execution or independent numerical coverage.
- Independent synthetic finance arithmetic and pinned upstream software parity exist. Full per-method original-source/numerical sign-off is not established. All unresolved source assertions remain **SOURCE NOT VERIFIED** and individual numerical approval remains **NUMERICALLY UNVERIFIED** where appropriate.
- No industrial validation certificate, independent plant outcome comparison or accreditation evidence was established.

## Equipment costing and escalation

The canonical registry returns **594 configurations**: **154 Garrett**, **421 OpenPyTEA**, **15 Nottingham**, **4 additional-source models**. OpenPyTEA has **403 provisionally available and18 disabled** entries;55 rows lack one or both primary size bounds. Catalogue presence does not mean automatic sizing or pricing coverage.

The Garrett integrated dispatcher has **7 direct-equation configurations and147 graph-fit configurations**. Some graph fits use printed exponents; they are not therefore standalone direct-price equations. Legacy individual wrapper files are not counted as additional independent correlations. Original graph readings and correction interpretations remain provisional. Installation, pressure, material, unit-capital and per-length scopes vary.

Price-period translation and FX use deterministic dated data. Default historical translation permits a same-currency consumer-inflation proxy to September2026, **not a verified CEPCI/current equipment quotation**. FX uses a pinned November2026 reference snapshot. Original dated observations were not independently revalidated in this audit; no verified current-price claim is made. Actual Charlie/Team8 pricing coverage was not measured in this Phase0 audit because the private reference fixtures were skipped/unavailable.

## Economic model status

Garrett detailed, Nottingham detailed and separate Nottingham Lang methods exist; factors preserve different bases. OPEX has19 historical category definitions plus explicit quantity, staffing, utility, percentage and allowance pathways. Six Revenue Box categories and avoided-cost separation remain unchanged. Core finance handles construction/ramp, tax/losses, depreciation, WC, explicit financing, NPV/IRR/MIRR/payback/ROI/PI and unit economics through a shared ledger.

Limitations: historical source parameters still require independent checks, commercial/horizon adapters have a reproduced failure, 13-field requested record mapping differs from actual15-field `CommercialLine`, jurisdictional/tax/market assumptions remain planning scenarios, and browser/API/export financial reconciliation is not fully demonstrated.

## Prioritised findings

| Priority | Finding / supporting location | Consequence / owner |
|---|---|---|
| High R-01 | `backend/tests/test_equipment_resolution.py:375`; `monte_carlo/engine.py:90` | Synthetic full-run expected complete but partial: mismatched revenue years → unresolved dependent OPEX → pending finance. E2+E1 |
| High R-02 | Engineering/costing registers and stored source metadata | Deterministic arithmetic is not independent coefficient/unit/applicability verification. E1 |
| High R-03 | `backend/equipment_costing/cost_to_future/cost_translation.py:14` | “2026” may be a consumer-inflation proxy; dated sources not independently checked. E1 |
| High R-04 | `backend/revenue/models.py:232` | Task's13-field contract not mapped to actual15-field record; preserve compatibility pending agreement. E2+E1 |
| High R-06/R-07 | `backend/ingestion/balance/workbook.py`; `backend/equipment_matching/service.py` | Cached formula/layout limits and unmeasured live AI suitability can affect upstream interpretation. E2+E1 |
| High R-08/R-09/R-10 | Cost aggregation, stage execution, financial connectors | Scope/double-counting/freshness/timing and export parity need independent reconciliation. E1+E2 |
| High R-11 | `backend/api/app.py:842`; `backend/cloud/` | Live tenant auth/restore/approved-baseline security remains unverified; no confirmed exploit found. E2 |

The risk register contains16 open findings, ranked by engineering consequence. **No confirmed Critical security exploit was demonstrated**; narrow scans cannot rule one out. Security/infrastructure findings are handed to Engineer2 rather than represented as completed certification.

## Engineer1 action plan

The first10 tasks, with dependencies and measurable acceptance, are in `phase1_execution_backlog.md`: source/gate agreement; dimensional references;12 sizing method verification; native-coordinate adapter parity; direct correlation verification; graph/factor/extrapolation review; quantity/installation/plant reconciliation; price-period/FX verification; OPEX/Revenue schedule verification; full ledger/metrics/reference reconciliation. They are proposals, not implemented changes.

## Engineer2 handover

Agree P0–P9/G0 and current schema contract; fix R-01 annual horizon handoff with E1 tests; reconcile block/connected freshness and optional bases; build permission-cleared real-file/AI truth sets; maintain source/assumption distinctions; verify browser/API/export parity, tenant isolation, backup/restore and old-version compatibility; review127 untracked duplicates without deleting user work; execute hosted CI and clean dependency install; reconcile stale AGENTS/notices paths and complete dependency/security/licence audit. Full details and owners are in requirement/risk/interface registers.

## G0 assessment

The only repository roadmap found is `docs/product-build-roadmap.md` (A–I), not the named Industry-Standard P0–P9 roadmap. The task's checklist is assessed below provisionally; it cannot substitute for actual official gate evidence.

| Requested condition | Result | Evidence / blocker |
|---|---|---|
| Architecture mapped | PASS for inspected baseline | `system_architecture.md`; actual/planned distinguished |
| Capability/gap register | PASS | CSV+Markdown,19 capability groups |
| Engineering/economic inventory | PARTIAL |248 numerical/contract rows,594 cost configs and factor registry; full semantic/source review pending |
| Source/verification gaps documented | PASS for inventory | Explicit unverified states; independent examples distinguished |
| Current tests recorded | PASS | Original full failure and skips preserved in evidence |
| Reproducibility assessed | PASS assessment / BLOCKED clean install | Clean source archive passed many checks; fresh offline dependencies absent |
| Critical security triaged | PARTIAL | No narrow-scan findings; live/cloud/comprehensive audit unavailable |
| Project revisions protected/checked | PARTIAL | Synthetic reopen/stale-write tests passed; real/cloud historical reopen not exercised |
| Requirements and acceptance criteria | PASS provisional register |26 requirements; official mapping awaits agreement |
| Baseline automation | PARTIAL | CI definitions/local checks added; hosted execution and clean dependencies unverified; known suite failure remains |
| Reference project proposed | PASS proposal only | Wastewater study; **PROPOSED — REQUIRES ENGINEER AGREEMENT** |
| Issue ownership | PASS |16 risk entries with E1/E2/shared owner and phase |
| Actual official G0 satisfied | BLOCKED | Official roadmap/gate not located; missing evidence above |

**Phase1 readiness: conditional, not released.** Begin only individually agreed verification tasks with exact source documents, permission-cleared reference data, independent numerical expected results and explicit tolerances. Do not claim the system numerically or industrially validated from this audit.

## Phase0 changes and validation

- Added13 requested audit files plus evidence manifests/logs/registries and a provisional test-purpose index.
- Added `tools/phase0_baseline_checks.py`: tracked Python AST syntax and narrow secret-pattern checks (values suppressed); observed545 original tracked Python files, zero findings.
- Added `backend/tests/test_phase0_version_protection.py`: two synthetic local SQLite tests, **2 passed**.
- Added `backend/requirements-phase0-tests.txt` and `.github/workflows/backend-baseline.yml`; pinned already-used test packages. Hosted job **not executed** and is expected to expose the existing failure.
- Updated `.github/workflows/frontend-quality.yml` to include `.cjs` tests alongside `.mjs`;45 committed frontend tests passed, production build and current typecheck passed.
- No calculation module, coefficients, financial baseline, original failing test, source licence or working frontend component changed. No push/deploy performed.

See `baseline_test_report.md` for exact commands and limitations. Logs are local execution evidence, not a claim of a fresh licensed-source or industrial audit.
