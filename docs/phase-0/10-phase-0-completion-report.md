# Phase 0 · Completion report

| Audit scope | Evidence |
|---|---|
| Baseline | FlowValue AI, codex/local-main-20261105, HEAD 74f364d2ebdcbc67bd0732937f59ef6a3704dce3. Working tree already had an unstaged Next.js generated type reference change. No staged or untracked changes existed at start. |
| Inspected | Tracked tree, AGENTS, onboarding, founder specification, A–I roadmap and current stage, calculation and ingestion documentation. Followed code paths through Next.js, API, persistence, stage execution, calculators, AI/research, scenarios, reports, tests and deployment definitions. |
| Executed | Git baseline and static inspection, isolated Python collection/test attempts and API smoke, frontend tests and TypeScript, dependency consistency and offline setup checks. [Exact commands and results](06-testing-and-security-audit.md). |
| Initial audit scope limits | Live OpenAI, external research, hosted Supabase/RLS and deployments, GitHub settings, independent industrial correlations, unauthorised/private datasets and full browser E2E were not verified. A registry-backed Python install was verified during remediation. |
| Repository writes | The initial audit created ten Markdown documents. Remediation changed the test manifest, CI workflow, README and two audit reports. The pre-existing generated Next.js diff was preserved. |

**Revised decision: PASS for the Phase 0 documentation and reproducibility gate.** G0.5 moved from BLOCKED to PASS on codex/p0-g05-test-reproducibility. A fresh Python 3.12.14 venv installed the declared manifest and ran the full backend suite. The Windows default-locale run reproduced 1,693 passed, 15 failed and 9 skipped. The documented UTF-8 run produced 1,707 passed, 1 failed and 9 skipped. Both recorded 367 passing subtests. A clean cached frontend install, 45 tests, TypeScript and the production build passed.

The three-year versus twenty-year test fixture keeps the backend check red. The Garrett catalogue decoding defect remains open for CP1252 runtimes. Hosted Actions has not run. This gate is separate from release readiness or permission to start a later phase. [Remediation evidence](06-testing-and-security-audit.md).

## Technical assessment

FlowValue is a functioning preliminary TEA system with a workbook-led workflow, canonical Python engines and an editable Next.js workspace. It has source-aware cost and revenue logic, conditional OPEX inputs, one financial ledger for the standard assessment, plus a separate connected calculation adapter for scenarios. Existing automated evidence demonstrates bounded behavior. The remaining work concerns independent numerical correctness, uniform input/review contracts, route and scenario parity, and operational assurance.

The [capability register](02-capability-register.md) distinguishes executed evidence from code-only evidence. Missing or incomplete areas include general document/CSV/native simulator ingestion, source-complete topology and industrial process geometry, independent numerical calibration across catalogue methods, a fully reviewed AI-to-baseline boundary, governed collaboration, and reproducible deployment and recovery.

## Ten highest-priority risks

| Rank | Risk | Evidence and disposition |
|---|---|---|
| 1 | A reproducible local baseline still needs hosted CI validation. | The new test manifest and all-test workflow are implemented locally. One known test failure keeps the backend check red. B01 local evidence complete, B10 hosted evidence pending. |
| 2 | Catalogue decoding can prevent valid equipment inputs from reaching pricing on a CP1252 host. | All 14 pricing and handoff failures share the Garrett loader's implicit encoding. The explicit UTF-8 test command clears them. Engineer 1 owns the application correction under B04. |
| 3 | Stage and scenario parity still requires independent fixtures with aligned inputs. | The manual-price failure is a test defect. The fixture requests 20 years against three approved commercial years. The three-year replay completed. Engineer 2 owns the fixture under B06 with Engineer 1 review. |
| 4 | Provisional AI-origin CAPEX/OPEX assumptions may reach financial results. | Stage proposals can be consumed in the same run. Completion is a coverage gate. B11. |
| 5 | Scope, missing inputs and unlike monetary bases can yield misleading comparisons. | Purchase/installed/unit-capital scopes and priced subsets require discipline. Provisional subtotals and translated price bases must remain explicit. B02/B05/B08. |
| 6 | Project year and operating year may diverge at adapter boundaries. | Shared schedule fields and legacy fallbacks can produce inconsistent phasing or metric labels. B06/B08. |
| 7 | Evidence, physical equipment and revision identities are not unified. | Extracted IDs, aliases, asset IDs and tag-keyed projections coexist. Most stage receipts do not stamp the code/method implementation. B07/B09. |
| 8 | Hosted ownership and recovery controls are unverified. | Owner policies and caller-token paths are present. Two-user hosted access checks and restore drill have no executed evidence. B17. |
| 9 | Uploaded content can exceed review or processing envelopes or distort AI interpretation. | Workbook bounds and constrained prompts exist. Windows worker resource controls differ from Linux, and accepted structured responses still need grounding. B11/B14/B17. |
| 10 | Background jobs, release controls and dependency security are not operationally validated. | Process-local queue coordination, registry advisory status, branch protection and deploy rollback are unverified. B10/B17. |

The next review should verify hosted CI, address the assigned fixture and catalogue issues, and agree source identity, monetary basis and calendar contracts before later phases begin. See the [first five tasks per engineer](09-development-backlog.md) and [GitHub controls](07-two-engineer-development-plan.md).

## Acceptance gate

| Gate | Status | Evidence |
|---|---|---|
| G0.1 Architecture documented | PASS | [Module inventory and diagram](01-architecture-audit.md). |
| G0.2 Major features classified with implementation evidence | PASS | [22-capability register](02-capability-register.md), with bounded status and unknowns. |
| G0.3 Calculation methods and risks inventoried | PASS | [Calculation methods and independent validation scope](03-calculation-integrity-audit.md). |
| G0.4 Data models and dependencies mapped | PASS | [Model, propagation, contracts and diagram](04-data-and-dependency-audit.md). |
| G0.5 Existing test results recorded reproducibly | PASS | [Clean install, both backend runs and frontend results](06-testing-and-security-audit.md) are recorded. The 15 original failures are classified and assigned. Hosted CI and a green backend baseline remain open. |
| G0.6 Security and operations risks documented | PASS | [Preliminary non-destructive review](06-testing-and-security-audit.md). Hosted controls remain unverified. |
| G0.7 Two-engineer responsibilities and shared interfaces | PASS | [Ownership and GitHub workflow](07-two-engineer-development-plan.md) and [data contracts](04-data-and-dependency-audit.md). |
| G0.8 Requirements and acceptance criteria | PASS | [Requirements R01–R19](08-requirements-register.md). |
| G0.9 Prioritised backlog | PASS | [B01–B18 with dependencies and issue titles](09-development-backlog.md). |
| G0.10 No unapproved application or production changes | PASS | The initial audit added documents. Remediation changed the test manifest, CI, setup instructions and two audit reports. Initial and final Git state were checked. No commit, push, deployment, production mutation or feature implementation. |
