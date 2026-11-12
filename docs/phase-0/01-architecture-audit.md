# Phase 0 · Architecture audit

Baseline: branch codex/local-main-20261105, commit 74f364d2ebdcbc67bd0732937f59ef6a3704dce3, matching the local origin/main tracking ref at inspection. The tracked Next.js generated type file already differed from HEAD. The baseline is the committed tree of 813 tracked files. The root contains backend, frontend, docs, tools and one tracked Actions workflow. Ignored local outputs and environments are outside the architecture evidence. The audit reports no production observations. [Evidence and gate](10-phase-0-completion-report.md).

Read the [repository rules](../../AGENTS.md), [onboarding](../FLOWVALUE_ENGINEER_ONBOARDING.md), [founder specification](../analyst-workflow-specification.md), [A–I roadmap](../product-build-roadmap.md), [stage isolation](../isolated-stages.md), [shared pipeline](../shared-pipeline.md), [stage connections](../stage-connections.md), and [calculation basis](../calculation_basis.md) as context. The A–I roadmap predates this audit's P0–P9 ownership scheme. Current code decides runtime status where these sources disagree.

~~~mermaid
flowchart LR
  U["Analyst browser"] --> N["Next.js pages and API proxy"]
  N --> A["FastAPI workspace API"]
  N -. hosted login .-> S["Supabase Auth"]
  A --> R["Stage runners and execution receipts"]
  A --> V["Local Store or hosted CloudStore"]
  V --> DB[("SQLite or Supabase with owner RLS")]
  R --> I["Bounded Excel worker and engineering report"]
  R --> E["Match, resolve, size and price equipment"]
  R --> C["CAPEX, Revenue, OPEX, financial engines"]
  R -. optional proposals .-> AI["OpenAI Responses adapter"]
  A --> P["HTML, JSON and uncertainty exports"]
  A --> MC["Monte Carlo job runner"]
  MC --> L["Connected calculation adapter"]
  L --> E
  L --> C
~~~

| Component and code | Purpose and I/O | Dependencies and maturity limits |
|---|---|---|
| [App routes](../../frontend/src/app), [workspace](../../frontend/src/blocks/shared/project-workspace.tsx), [Revenue workspace](../../frontend/src/blocks/revenue/rate-workspace.tsx) | Entry, Engineering Data, Equipment, CAPEX, OPEX, Revenue, Cashflow, Finance, Scenario/Sensitivity and Monte Carlo. Reads an assessment ID, results and revision, submits edits and renders saved outputs. | Next.js App Router, React, local browser selection, same-origin API proxy. Component/SSR tests exist. Full interactive journey and browser coverage are unverified. |
| [API](../../backend/api/app.py#L284) and [proxy](../../frontend/src/app/api/%5B...path%5D/route.ts) | Multipart create, review, stage runs, reports, versions and uncertainty jobs. The API also exposes catalogue and health. | FastAPI/Pydantic, thread executor, process-local submission lock. Per-stage route names for CAPEX/OPEX/Revenue also trigger a coordinated economics group. |
| [Execution](../../backend/blocks/execution.py#L125), [registry](../../backend/blocks/registry.py), [stage workflow](../../backend/blocks/stage_workflow.py#L32) | Map state and upstream hashes into a runner context, persist payload, status, evidence and receipt. Group starts after engineering approval. | Python calculators and stores. “Ready” means a usable payload exists, and a separate complete flag distinguishes provisional coverage. |
| [Ingestion](../../backend/orchestration/ingest.py#L18), [workbook pipeline](../../backend/ingestion/workbook_pipeline.py#L119), [report types](../../backend/ingestion/balance/models.py#L84) | Workbook bytes and name become tables, original observations, material and energy entities, topology, checks, source IDs and parser diagnostics. | Isolated worker, openpyxl, xlrd and defusedxml. Excel path is present. The CSV/DWSIM/BioSTEAM paths cited by some docs were not found on the current Entry/API path. |
| [Equipment matching](../../backend/equipment_matching), [resolution](../../backend/equipment_resolution), [sizing registry](../../backend/engineering_sizing/registry.py#L127), [costing registry](../../backend/equipment_costing/registry.py#L231) | From equipment identity and measured/reviewed physical inputs to model choice, size, unit conversions, quantity-extended cost and scope. | Garrett, Nottingham and OpenPyTEA equipment families. Source availability, compatible inputs, applicability, chart uncertainty and duplicate identity limit coverage. |
| [CAPEX](../../backend/capex/engine.py#L480), [OPEX](../../backend/opex/engine.py#L45), [Revenue](../../backend/revenue/engine.py#L448) | Purchase/scoped capital to installed investment, annual expenses, income and savings. Ledgers carry assumptions and monetary basis. | CAPEX scope/exclusions, physical schedules and source prices. Stage-level completeness and source data vary. |
| [Finance](../../backend/financial_modelling/engine.py#L24), [Cashflow](../../backend/blocks/cashflow/view.py) | Combine annual upstream economics into one project/equity ledger and metrics. Cashflow is a view over the ledger and revenue fallback. | Typed financial inputs, matching price basis and complete costs. Generic engine has a broader surface than the standard assessment connector. |
| [Uncertainty](../../backend/scenarios_and_uncertainty/monte_carlo/engine.py#L365), [scenario UI](../../frontend/src/blocks/scenarios/workspace.tsx) | Discover inputs, freeze a scenario, sample deterministic reruns, retain outcome states and export distributions. | NumPy/SciPy, connected pipeline, user-supplied uncertainty bounds. Stage versus scenario parity and industrial distribution calibration are open. |
| [AI](../../backend/orchestration/provider.py), [orchestration](../../backend/orchestration), [Revenue prompts](../../backend/revenue/llm) | Interpret source cells/context, propose structured assumptions, rank or select methods, optionally research sources. | Environment-selected OpenAI model, provider cache, bounded context. Live provider and research accuracy unverified. |
| [Local Store](../../backend/orchestration/store.py#L16), [CloudStore](../../backend/cloud/store.py#L16), [RLS schema](../../backend/cloud/schema.sql#L29) | Store workbook and assessment JSON, named versions and AI cache. Hosted reads use verified session context. | SQLite revision compare-and-swap versus Supabase/PostgREST with owner RLS. Live schema, role sharing, backup and recovery remain unverified. |
| [Reporting](../../backend/dashboard_reporting/study_report.py#L128), [export routes](../../backend/api/app.py#L919) | Render HTML study, JSON snapshot, register CSV and Monte Carlo CSV/XLSX. | Saved stage and currency views, output gating. Cross-format numerical reconciliation has no comprehensive executed browser acceptance. |
| [Workflow](../../.github/workflows/frontend-quality.yml), [Dockerfile](../../backend/Dockerfile), [Vercel config](../../frontend/vercel.json), [notices](../../THIRD_PARTY_NOTICES.md) | CI frontend checks, deployment definitions and third-party attribution. | Only one tracked Actions workflow. No Python or security gates in it. Hosted deployment, partner services and runtime policy are unverified. |

### Boundary findings

- A connected calculation path and stage runners share core engines, but independently assemble inputs and authority. Monte Carlo imports [pipeline.run](../../backend/scenarios_and_uncertainty/monte_carlo/engine.py#L17), whereas normal saved finance uses [its stage runner](../../backend/blocks/financial/runner.py#L14). Parity is a contract risk, especially after Revenue or calendar changes.
- UI routes span [assessment-workspace](../../frontend/src/components/assessment-workspace.tsx) and [project-workspace](../../frontend/src/blocks/shared/project-workspace.tsx). Register CSV formatting appears in both. Confirm consumers before deduplicating. The current Revenue route uses its dedicated rate workspace alongside retained review components.
- [Shared operating state](../../backend/blocks/execution.py#L55) combines inputs with different authorities and price periods. Multiple report views and calculation receipts coexist. Their distinction belongs in the [data audit](04-data-and-dependency-audit.md).
- A static AST scan of 456 tracked non-test Python modules found package re-export loops involving [engineering sizing and its registry](../../backend/engineering_sizing/__init__.py) and [finance and its snapshots](../../backend/financial_modelling/__init__.py). The submodules import siblings via their package. The scan does not establish a failing runtime cycle. API smoke loaded successfully. The declared stage graph is acyclic. [Freshness](../../backend/blocks/execution.py#L137) has a recursion guard. Revenue to OPEX is a conditional data dependency. Revenue schemes that refer to a cost target need an explicitly frozen prior-year or external basis if future models introduce a true feedback loop.
- The [Entry input index](../../backend/ingestion/inputs/README.md) and AGENTS reference historical parser paths absent from the tracked active tree. Backlog B12 requires a route-based support matrix.

[Capabilities](02-capability-register.md) · [Calculation inventory](03-calculation-integrity-audit.md) · [Testing and security](06-testing-and-security-audit.md)
