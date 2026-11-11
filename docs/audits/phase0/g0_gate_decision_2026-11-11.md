# G0 gate decision — joint record, 11 November 2026

**Code basis:** `main` at `84800be` (PR #2 merged). **Authority:** the official roadmap's Phase 0 criteria (implementation work ¶57–64, milestones M0.1–M0.5, tests ¶79–84, exit gate ¶85), as used in `g0_acceptance_matrix.md`.

This record supersedes neither earlier report. It re-evaluates every official criterion against today's code and evidence, and it reconciles the two Phase 0 audits:

- Engineer 1: `docs/audits/phase0/` (decision on 10 November: **FAIL**)
- Engineer 2: `docs/phase-0/` on `engineer-2/development` (decision: **PASS** against a G0.1–G0.10 checklist)

## Decision

**G0: technical criteria PASS. Gate passes when the four joint sign-offs below are recorded.**

Every criterion that software or evidence can settle now passes. The criteria still open are agreements between the two engineers, which no test can supply: the reference project, one requirements register, the capability register and the baseline rules. Neither engineer's signature is inferred here.

## What changed since the 10 November FAIL

| Earlier blocker | Resolution | Evidence |
|---|---|---|
| T-02: R-01 integration test failing | Fixed: horizons and commercial years are explicit (Engineer 1); fixture passes the approved 3-year horizon (Engineer 2) | `main` backend CI green; full suite 4,199 passed, 0 failed |
| R-17: CI forced the AI cache off, failing 4 tests | Override removed from `backend-baseline.yml` | Commit `8a2bdee`; 4 cache tests pass under CI settings |
| IW-06 / M0.4: CI never ran on GitHub | Hosted CI ran on PR #2 and on `main` after merge | Backend run 43034082855 and frontend run 43034082943 on `main`, both success |
| M0.3 / IW-05: audit files uncommitted | Committed and merged to `main` | PR #2 |
| T-04: only synthetic reopen tests | Real historical store reopened on a copy: 28 assessments, 2 versions, 0 originals changed | `evidence/g0_decision_2026-11-11/t04_reopen_result.json` |
| 127 duplicate files in the working tree | Removed; `.gitignore` blocks recurrence | Commit `6a59df8` |

## Official criteria — current status

| ID | Criterion (short) | Status | Evidence or remaining action |
|---|---|---|---|
| IW-01 | Audit backend, frontend, API, calculations, ingestion, storage | PASS | `system_architecture.md`; Engineer 2 `01-architecture-audit.md` |
| IW-02 | Capability register | PARTIAL | Two registers exist (E1 19 groups, E2 22 capabilities). **Sign-off S3** |
| IW-03 | Duplicates, inconsistent contracts, unsupported models | PASS | Risk and method registers; Phase 1 legacy route fixed |
| IW-04 | Engineering and financial data flow | PASS | `data_flow_and_dependencies.md`; E2 `04-data-and-dependency-audit.md` |
| IW-05 | Single version-controlled requirements register | PARTIAL | Committed, but two registers exist. **Sign-off S2** |
| IW-06 | CI on every proposed change | PASS | Backend and frontend workflows run on pull requests and `main`; both green |
| IW-07 | Standard rules: precision, units, missing data, provenance, approvals | PARTIAL | B08 decisions (PR #3) and Phase 1 unit and tolerance policy. **Sign-off S4** |
| IW-08 | Independent test-reference policy | PASS | `AGENTS.md`; Phase 1 independent references |
| M0.1 | Architecture map | PASS | As IW-01 |
| M0.2 | Feature implementation and gap register | PARTIAL | As IW-02. **Sign-off S3** |
| M0.3 | Versioned requirements and acceptance criteria | PARTIAL | As IW-05. **Sign-off S2** |
| M0.4 | Automated baseline test pipeline | PASS | As IW-06 |
| M0.5 | Agreed initial industrial reference project | BLOCKED | Still proposed only. **Sign-off S1** |
| T-01 | Reproduce from a clean environment | PASS | Fresh Python 3.12 environment from `requirements-phase0-tests.txt`; GitHub CI builds from scratch |
| T-02 | Every supported module loads and passes its tests | PASS | macOS: 4,199 passed, 0 failed, 3 skipped. `main` merged with `engineer-2/development`: 4,222 passed, 0 failed, 3 skipped. Engineer 2's Windows run on their branch: 1,731 passed, 0 failed, 9 skipped. Skips need private fixtures or optional OpenPyTEA; their disposition is part of **S4** |
| T-03 | Record failures rather than suppress them | PASS | Original logs preserved; every fix landed with tests unchanged or strengthened |
| T-04 | Saved revisions reopen without modifying the baseline | PASS (local) | 28/28 assessments and 2/2 versions reopened on a copy; 0 originals changed. Hosted restore is Phase 8 (R17) |
| T-05 | Test environment discloses no credentials or confidential data | PARTIAL | CI has no credentials; `tools/phase0_baseline_checks.py` reports 0 findings; private data excluded and skipped. Engineer 2 review of log and fixture policy. **Sign-off S4** |
| T-06 | Every planned feature has an owner and measurable criterion | PARTIAL | As IW-05. **Sign-off S2** |
| G0-A | Baseline reproducible | PASS | T-01, T-02 |
| G0-B | Existing failures documented | PASS | T-03 |
| G0-C | Critical security issues triaged | PASS | 17 severity-ranked risks (R-01 to R-17) with owners; no confirmed critical exploit. Live tenant testing is Phase 8 |
| G0-D | Implementation distinguishable from roadmap promises | PASS | Both capability registers separate implemented, partial and planned |

## How the two audits map

Engineer 2's audit used a self-defined G0.1–G0.10 checklist; this record uses the roadmap's own criteria. Engineer 2's evidence is accepted as supporting evidence where it maps:

| Engineer 2 item | Official criteria |
|---|---|
| G0.1 Architecture | IW-01, M0.1 |
| G0.2 Capabilities | IW-02, M0.2 |
| G0.3 Calculation methods and risks | IW-03 |
| G0.4 Data models and dependencies | IW-04 |
| G0.5 Reproducible test results | T-01, T-02, M0.4 |
| G0.6 Security and operations | G0-C, T-05 |
| G0.7 Two-engineer responsibilities | T-06 (owners) |
| G0.8 Requirements | IW-05, M0.3 |
| G0.9 Backlog | T-06 (measurable criteria) |
| G0.10 No unapproved changes | Process control; no official row |

Engineer 2's PASS did not cover M0.5 (reference project), which the roadmap lists as a mandatory milestone. That is why the official decision still waits on S1.

## Proposed single requirements register (for sign-off S2)

Adopt Engineer 2's **R01–R19** as the single forward register: each row already has priority, owner, phase and a measurable acceptance criterion. Add two rows that R01–R19 lack, and keep Engineer 1's REQ-01..26 as a historical mapping.

| Engineer 1 REQ | Maps to | Engineer 1 REQ | Maps to |
|---|---|---|---|
| REQ-01 Immutable baseline | R01 | REQ-14 Six-category Revenue Box | R06 |
| REQ-02 Official roadmap and G0 | This record | REQ-15 Revenue rate-time-quantity | R06 |
| REQ-03 Method and unit inventory | R02 | REQ-16 One financial ledger and timing | R07, R11 |
| REQ-04 Unit aliases and contexts | R03 | REQ-17 NPV, IRR, payback, unit metrics | R07 |
| REQ-05 Source-backed sizing | R03 | REQ-18 AI proposes, Python calculates | R13 |
| REQ-06 Stage and interface integrity | R09, R12 | REQ-19 Simulator input scope | R15, R19 |
| REQ-07 Workbook extraction provenance | R09 | REQ-20 Independent verification inventory | R02, R03 |
| REQ-08 Commercial record compatibility | R06, R10 | REQ-21 Monte Carlo reproducibility | R08 |
| REQ-09 Cost catalogue source verification | R02, R04 | REQ-22 Dashboard, API, export reconciliation | R16 |
| REQ-10 Escalation and FX basis | R10 | REQ-23 Baseline CI and environment | R01 |
| REQ-11 Quantity, installation, scope, duplicates | R04 | REQ-24 Project and tenant protection | R12, R17 |
| REQ-12 Independently verifiable CAPEX | R04 | REQ-25 Reference project and industrial validation | R18, **new R20** |
| REQ-13 OPEX drivers and bases | R05 | REQ-26 R39 opportunity workflow | **new R21** |

**New rows:**

- **R20 · Critical · shared · P0.** Agreed reference project (M0.5). Acceptance: source files with version hash, owner permission and confidentiality class; an independent truth set for balances, equipment identities and economics; both engineers' recorded agreement.
- **R21 · High · shared · P2/P4/P5/P7.** Natural-language commercial opportunity workflow (founder requirement R39 in `AGENTS.md`). Acceptance: the mandatory R39 cases (price given, price missing, research refused, insufficient data, unsupported contract probability, scenario edit, baseline restore) pass end to end.

## Joint sign-offs required to pass G0

| ID | Decision | Proposal | Engineer 1 | Engineer 2 |
|---|---|---|---|---|
| S1 | **Reference project (M0.5)** | **Charlie protein-from-air study** (Engineer 1 decision, 11 November 2026). Its M&E workbook and the human economics study (`Task 2 Charlie Economics 2.xlsx`) are both available; Team 8 has an M&E workbook but no economics file. The economics study is a comparison made *after* independent calculation, never a price source. **Team 8 is the held-out project** for AI matching and assumption evaluation, because Charlie was used to tune them. Source files stay private and local; only page references, hashes and derived checks enter the repository. The four synthetic workbook fixtures stay as parser regression tests. | ☑ 11 Nov 2026 | ☐ |
| S2 | **Single requirements register** (IW-05, M0.3, T-06) | R01–R19 plus R20 and R21 above, with the REQ mapping retained | ☐ | ☐ |
| S3 | **Capability register** (IW-02, M0.2) | Engineer 2's 22-capability register is the maintained one; Engineer 1's 19 groups stay as the baseline snapshot | ☐ | ☐ |
| S4 | **Baseline rules and test disposition** (IW-07, T-02 skips, T-05) | B08 decisions (PR #3) for money, timeline, missing and approval; Phase 1 per-method tolerances; the 3 private-fixture or optional-package skips accepted as documented skips; Engineer 2 confirms the test log and fixture policy for T-05 | ☐ | ☐ |

When all eight boxes are ticked, with the decision and date recorded beside S1, **G0 passes at the commit that records the sign-offs.** Record each sign-off as a pull-request approval or a dated line in this file, made by the engineer themself.

## Update after Engineer 2's PR #9 (11 November 2026)

PR #9 (`engineer-2/development`, head `9bec52d`, CI green) settles several items once merged:

- **CI consolidated (IW-06, M0.4):** one backend job (`backend-baseline.yml`, no cache override) and one test requirements file (`requirements-phase0-tests.txt`). The duplicate backend job and `requirements-test.txt` are gone.
- **Engineer 2's Phase 0 audit and the R01–R19 register arrive on `main`** (`docs/phase-0/`), so the single register proposed for **S2** and the capability register proposed for **S3** both exist in the repository.
- **Commit authorship:** Engineer 2's new commits use their own git identity.
- Combined with every open Engineer 1 PR, the full suite gives 4,285 passed, 0 failed.

The sign-offs below are still required. Merging PR #9 first lets S2 and S3 point at files on `main`.

## Not part of G0

Hosted restore and two-user isolation (Phase 8, R17), the 13-field commercial contract (Phase 4), costing source verification (Phase 3) and industrial validation (Phase 9) stay with their phases. They are not reasons to hold G0.
