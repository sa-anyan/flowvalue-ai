# Phase 0 · Testing, development and security audit

Baseline 74f364d. Test runs used Windows, Python 3.12.14, pytest 9.2.0 and Node 24.22.1. Recorded installed Python versions include FastAPI 0.162.0, uvicorn 0.54.0, Pydantic 2.14.1, python-multipart 0.0.32, openpyxl 3.1.5, xlrd 2.0.2, defusedxml 0.7.1, NumPy 2.5.4 and SciPy 1.18.1. The Python test source came from a Git archive of HEAD, outside the working tree. The assessment DB was in the audit scratch directory. Provider configuration variables were cleared for the full suite, AI and hosted modes were disabled, and no production environment or credentials were used.

## Test inventory

| Layer | Current evidence and limit |
|---|---|
| Numerical units and deterministic engines | [Engineering sizing](../../backend/tests/test_engineering_sizing.py), [unit conversion](../../backend/tests/test_unit_conversion.py), [CAPEX](../../backend/tests/test_capex.py), [OPEX](../../backend/tests/test_opex.py), [revenue](../../backend/tests/test_revenue.py), [finance](../../backend/tests/test_financial_modelling.py). These validate selected expected values, negative inputs and reconciliation. Independence and coverage vary by method. |
| Parser, handoff and persistence | [Workbook fixtures](../../backend/tests/fixtures/equipment_inputs), [isolated stages](../../backend/tests/test_isolated_stages.py), [stage workflow](../../backend/tests/test_stage_workflow.py), [review before calculation](../../backend/tests/test_review_before_calculation.py). Synthetic source and local TestClient tests do not establish production behavior. |
| AI and research | [Engineering review](../../backend/tests/test_engineering_review.py), [specialist batching](../../backend/tests/test_specialist_batching.py), [Revenue MECE review](../../backend/tests/test_revenue_mece_review.py), [pending research](../../backend/tests/test_revenue_pending_research.py). Fixtures and mocks validate contracts. No live provider or prompt quality certification. |
| UI and results | [Node tests](../../frontend/tests) check state transforms, static rendering, charts and navigation. Browser interactions, save/reopen, full exports and production E2E are not automated in the tracked workflow. |
| Security | [Upload limits](../../backend/tests/test_upload_limits.py), [cloud runtime](../../backend/tests/test_cloud_runtime.py), [manual RLS SQL](../../backend/cloud/rls-test.sql). Hosted auth and database checks require a separately provisioned environment. |
| Infrastructure | [Actions](../../.github/workflows/frontend-quality.yml) runs npm ci, TypeScript, tests/*.mjs and production build using Node 22. The README calls for Node 24. The workflow excludes .cjs files and all Python suites. No tracked unified lint or formatting gate or browser runner found. [Frontend lock](../../frontend/package-lock.json) exists. Python has pinned direct runtime and optional Monte Carlo requirements without a full resolved test lock. |

## Commands and results

Run PowerShell from the repository root for environment checks. Use a fresh Git archive for tests that write fixture outputs. Substitute a scratch path and the existing Python executable where shown.

~~~powershell
git status --short --branch
git rev-parse HEAD
git diff --stat
git archive --format=zip -o (Join-Path $audit 'source.zip') HEAD
Expand-Archive -LiteralPath (Join-Path $audit 'source.zip') -DestinationPath $source
Get-ChildItem Env: | Where-Object Name -Match '^(OPENAI_|SUPABASE_|AI_ENABLED$|FLOWVALUE_)' |
  ForEach-Object { [Environment]::SetEnvironmentVariable($_.Name,$null,'Process') }
$env:AI_ENABLED='false'
$env:FLOWVALUE_CLOUD='false'
$env:FLOWVALUE_ASSESSMENT_DB=Join-Path $audit 'test.sqlite3'
$env:PYTHONDONTWRITEBYTECODE='1'
Push-Location $source
& $py -m pytest backend/tests -q -ra --tb=short -p no:cacheprovider
Pop-Location
~~~

- Initial Python collection exited **2**. [test_openpytea_catalogue.py](../../backend/tests/test_openpytea_catalogue.py#L6) imports pandas, which was absent from FlowValue's environment and is absent from both declared backend requirement files. No tests ran in that attempt. The existing environment's **pip check** passed, which checks installed package consistency and does not detect undeclared imports.
- Frontend, from the existing frontend directory, **node --test (Get-ChildItem tests -File | ForEach-Object FullName)** returned **45 passed, 0 failed, 0 skipped**, with a module-type warning. **node node_modules/typescript/bin/tsc --noEmit --incremental false** exited **0**. Type checking uses the existing generated development route types. It is separate from a clean production build.
- Synthetic local TestClient smoke in the archive used a separate smoke.sqlite3. **GET /api/health**, **GET /api/catalogue** and **GET /openapi.json** returned **200**. The catalogue contained equipment and OpenAPI listed **/api/assessments/{key}/revenue-rates**. No mutation was sent. TestClient emitted a Starlette httpx deprecation warning.
- Clean Python dependency resolution attempt **python -m pip --disable-pip-version-check install --dry-run --ignore-installed --no-index -r backend/requirements-orchestration.txt** exited **1** at fastapi==0.162.0. No local offline wheel source was supplied. This is a local artifact availability constraint, not evidence that PyPI lacks the version.
- The documented **uvicorn --env-file** path relies on python-dotenv. **python -c** with importlib.util.find_spec confirmed dotenv and pandas absent, and pytest and httpx present, in the existing FlowValue environment. The pinned orchestration file does not declare dotenv, pytest, httpx or pandas. The Monte Carlo file extends it with NumPy and SciPy. A clean startup with explicitly set environment variables avoids the optional dotenv parser.
- Existing checkout lacked npm on PATH. The isolated frontend attempt used the already installed npm 11.6.2 CLI from the separate OpenPyTEA workspace, with **node <npm-cli.js> ci --offline --no-audit**. **Exit 0**, 27 packages added. **NEXT_TELEMETRY_DISABLED=1; node node_modules/next/dist/bin/next build --webpack** in the same archived frontend exited **0**. Compilation, TypeScript, and 20 prerendered/static-page generation steps completed, and the route manifest includes Revenue and Scenario and Sensitivity. This proves a clean frontend build with locally cached dependencies on Node 24, not registry-backed installation or CI success on Node 22.

### Reproduce setup after obtaining dependencies

On a clean checkout, create a Python 3.12 venv. Install [requirements-monte-carlo.txt](../../backend/requirements-monte-carlo.txt), which includes the basic orchestration requirements. For reproducing the audit tests, provide pytest 9.2.0, pandas 3.1.1 and httpx 0.28.1 as explicit test dependencies, or use the recorded environment below. Set AI_ENABLED=false, FLOWVALUE_CLOUD=false and FLOWVALUE_ASSESSMENT_DB to a new scratch path. Run **python -m uvicorn backend.api.app:app --host 127.0.0.1 --port 8000** from the root. To use **--env-file**, provide python-dotenv and a local env file. For frontend use Node 24 and npm, then **npm ci**, **npm run dev**, and **npm run build** from frontend as separate steps. Registry-backed fresh installation was outside this offline audit. Confirm dependency versions, localhost health, catalogue and one synthetic approval-to-finance flow before marking a clean environment accepted.

## Security and operations findings

| Finding | Baseline evidence | Required follow-up |
|---|---|---|
| Secret handling and environment split | [Server-only provider](../../backend/orchestration/provider.py#L11), [sample env](../../backend/orchestration/.env.example), and ignore rules. git check-ignore confirmed local backend/.env, database and .venv are ignored. No credential values were inspected. | E2 verify secret scanning and rotation in an authorised environment. An ignore rule does not prove history, logs or deployment are secret-free. |
| Hosted authentication and tenant isolation | [Cookie settings](../../frontend/src/lib/cloud-auth.ts#L11) are HttpOnly, SameSite Lax and Secure in production. [Backend guard](../../backend/api/app.py#L842) verifies bearer-backed workspace and [CloudStore](../../backend/cloud/store.py#L16) uses caller token. [RLS policies](../../backend/cloud/schema.sql#L29) apply owner checks to assessment/version/cache. | Before production reliance, run two-user tests for reads, writes, comparison, report/export, cache, jobs and versions against approved staging. Branch rules, actual hosted configuration and tenant isolation are unverified. |
| Local exposure and request limits | Loopback-oriented README, host/origin checks, [proxy](../../frontend/src/app/api/%5B...path%5D/route.ts), 20 MiB workbook/21 MiB upload request/5 MiB other mutation caps and timeouts. Local mode uses one workspace without hosted identity. | Keep local binding private. Test controlled workloads and identity-specific quotas before hosted scale. Verify reverse proxy origin behavior and log correlation safely in staging. |
| Untrusted upload and resource bounds | [Workbook reader](../../backend/ingestion/balance/workbook.py#L66), [worker](../../backend/ingestion/worker.py), and [parent](../../backend/orchestration/ingest.py#L18) cap input, rows, cells, output and time. Linux gets address-space/CPU limits. Windows skips the resource module. Worker environment is restricted. Formulas/links/macros are treated as data or ignored. | Run controlled local resource-limit tests, and document platform limits. Parent captures output before measuring bytes. Verify maximum memory consumption and redaction of worker diagnostics. |
| Model data exposure and prompt injection | [AI audit](05-ai-systems-audit.md). Workbook cells and process text can enter provider context. Explicit consent gates research, which can make outbound provider tool requests. Provisional AI-origin costs may reach Finance. | Treat authority as an immediate numerical integrity control. Validate payload minimisation, consent, source binding and retention in P5/P8. No live red-team, research or provider request was run. |
| Job reliability and backups | [API](../../backend/api/app.py#L25) has a single worker executor and process-local lock. [Monte Carlo service](../../backend/scenarios_and_uncertainty/monte_carlo/service.py#L83) persists job state and cooperatively cancels. Named versions are application snapshots. No durable distributed queue, restart reaper or backup/restore runbook verified. | Test worker interruption, concurrent revisions, stuck jobs, restore objectives and observability before scaling. Never count local or DB versions as a demonstrated offsite backup. |
| Export and dependency exposure | [Report renderer](../../backend/dashboard_reporting/study_report.py), [HTML/JSON routes](../../backend/api/app.py#L919), [Monte Carlo exports](../../backend/scenarios_and_uncertainty/monte_carlo/exports.py), tracked third-party notices. The JSON snapshot serializes the assessment view rather than a minimal summary. | Classify snapshot data and verify escaping/redaction/formula safety for every export in synthetic tests. Dependency vulnerability scan was not run against external advisory services. No statement of absence of vulnerabilities. |
| Deployment and logging | [Backend Dockerfile](../../backend/Dockerfile) installs the Monte Carlo requirements and runs as a non-root user. [Vercel config](../../frontend/vercel.json) sets proxy execution duration. Workbook decoding logs a bounded stderr excerpt. | Stage a clean container/production build and check deployment configuration, log retention, alerts and rollback without changing production. |

The audit did not use live penetration testing, hosted credentials, active research, registry-backed dependency installation, production data or external deployment services. Code and locally executed fixture results are the evidence.

## Final execution ledger

The isolated rerun used the same archive and interpreter with a scratch DB named test-with-pandas.sqlite3. The OpenPyTEA venv's site-packages directory was appended after importing FlowValue's FastAPI, Pydantic, NumPy, SciPy and pytest, so those versions stayed unchanged. This diagnostic used pandas 3.1.1 without installing packages into FlowValue.

With the cleared environment above, set FLOWVALUE_ASSESSMENT_DB to the second scratch DB. From the archived source, pipe the following driver to **& $py - $extra**, where $extra is the sibling venv's Lib/site-packages path.

~~~python
import sys
import fastapi, pydantic, numpy, scipy, pytest
sys.path.append(sys.argv[1])
import pandas
print(f"FastAPI {fastapi.__version__}, Pydantic {pydantic.__version__}, NumPy {numpy.__version__}, SciPy {scipy.__version__}, pandas {pandas.__version__}", flush=True)
raise SystemExit(pytest.main(["backend/tests","-q","-ra","--tb=short","-p","no:cacheprovider"]))
~~~

**Exit 1.** Pytest reported **1,693 passed, 15 failed, 9 skipped, 367 subtests passed and 3 warnings in 808.39 s**. The nine skips were one private equipment workbook, one private Charlie snapshot, six tests requiring a private Team 8 workbook and one optional pinned OpenPyTEA 3.2.1 comparison. The sibling installation was OpenPyTEA 3.2.2. Warnings were two already-imported anyio assertion-rewrite notices and the Starlette TestClient/httpx deprecation.

| Failure group | Exact cases and observed result | Audit disposition |
|---|---|---|
| Missing conversion specification (3) | [test_canonical_resolver_completes_one_parameter_without_reselecting_sources](../../backend/tests/test_assumption_completion.py#L206), [test_thermal_adapter_owns_lmtd_and_retains_redundant_ai_binding_audit](../../backend/tests/test_automatic_equipment_inputs.py#L1059), [test_canonical_model_unit_handoff_and_automatic_resolver](../../backend/tests/test_heat_exchanger_basis.py#L241) raised KeyError on unit_conversion. | E1 validates inputs and model requirements. E2 reviews absent-field and review contract. B03/B04/B08. |
| Chart interpretation gate (3) | [test_pump_sizing_flows_into_canonical_cost_model](../../backend/tests/test_engineering_sizing.py#L121), [test_parsed_adapter_optional_pressure_and_ambiguity](../../backend/tests/test_unit_conversion.py#L203), [test_refrigeration_and_area_chart_scaling](../../backend/tests/test_unit_conversion.py#L192) raised UnitResolutionError for chart-coordinate interpretation. | Determine whether fixtures expect unsupported chart inputs or current policy rejects a legitimate source coordinate. B02/B03/B04. |
| Dated translation and installation (3) | [test_equipment_installation_and_capex_are_scaled_once](../../backend/tests/test_cost_translation.py#L126) had a null prior amount. [test_unsupported_source_is_retained_as_unpriced_not_fake_2026](../../backend/tests/test_cost_translation.py#L165) expected a missing-source message and got chart-coordinate rejection. [test_different_native_indices_aggregate_on_one_dated_currency_basis](../../backend/tests/test_cost_translation.py#L221) found no baseline estimate. | Diagnose pricing coverage before inferring an error in translation arithmetic. B04/B08. |
| CAPEX connector and total aggregation (5) | [CAPEX connector quantity/price handoff](../../backend/tests/test_capex.py#L431) raised an unresolved purchase component for HX-1. [EquipmentTotalTests](../../backend/tests/test_total_equipment_cost.py) failed test_distinct_cost_bases_and_scopes_not_added (0 subtotals vs 2), test_routing_counts_and_source_evidence (null total), test_unit_prices_require_physical_quantities (null total), and test_unresolved_equipment_is_never_silently_dropped (missing subtotal). | Trace units, basis, scope and expected priced rows before changing aggregation. B04. |
| Monte Carlo central case (1) | [test_manual_price_monte_carlo_reconciles_same_canonical_run](../../backend/tests/test_equipment_resolution.py#L375) returned partial where complete was expected. | Confirmed fixture-level parity failure. Downstream cause remains unisolated. B06. |

The full run listed no failures in the financial modelling, OPEX, MECE revenue review, upload limits, local cloud-runtime mock, stage-workflow or Monte Carlo discovery suites. Representative passing cases include [unlevered ledger reconciliation](../../backend/tests/test_financial_modelling.py#L226), [undefined and multiple IRR roots](../../backend/tests/test_financial_modelling.py#L557), [stage group preserving Revenue approval](../../backend/tests/test_stage_workflow.py#L42), [literal rate handoff](../../backend/tests/test_revenue_rates.py#L79) and [uncertainty cannot replace saved central values](../../backend/tests/test_monte_carlo_uncertainty_discovery.py#L80). This is bounded fixture evidence. Independent engineering validation and stage/scenario parity across the catalogue remain open.

## G0.5 remediation · clean test environment and failure triage

This section supersedes the initial setup conclusions for the local remediation branch, codex/p0-g05-test-reproducibility, based on 74f364d. The initial execution record remains above for comparison.

### Setup correction

- [requirements-test.txt](../../backend/requirements-test.txt) extends the pinned [Monte Carlo requirements](../../backend/requirements-monte-carlo.txt), which include the orchestration requirements. It declares **pytest 9.2.0**, **httpx 0.28.1** and **pandas 3.1.1** as test-only dependencies. The original README specified only orchestration dependencies. That omits pytest, the TestClient transport, pandas required by [the pinned catalogue tests](../../backend/tests/test_openpytea_catalogue.py#L6), and NumPy/SciPy for the Monte Carlo suite. The original offline missing-wheel result was a separate registry/artifact limitation.
- [README](../../README.md) documents separate runtime and test installations, a test DB, and explicit UTF-8 test mode. It removes the default startup dependence on uvicorn's optional --env-file flag, which requires separately installed python-dotenv. No runtime dependency versions changed.
- [GitHub Actions](../../.github/workflows/frontend-quality.yml) now runs all Node tests on Node 24 and adds a Python 3.12 job with dependency checks and a scratch assessment DB. Hosted/AI modes are disabled. Failures surface normally. The workflow was parsed locally with PyYAML BaseLoader and its jobs, versions, commands, trigger and isolation settings were asserted. GitHub-hosted execution was not triggered.

### How the 15 failures were isolated

The prior 15 node IDs were run on archived predecessor **feb37c8** in the existing FlowValue interpreter with the default Windows locale, using **python -m pytest @ids -q -ra --tb=line -p no:cacheprovider**. Result **15 failed, 0 passed, 0 skipped** in 69.80 seconds. These failures predate the remediation and the latest scenario workspace commit. This comparison does not identify the first failing historical revision.

The same 15 node IDs were run on archived **74f364d** using **python -X utf8 -m pytest @ids -q -ra --tb=line -p no:cacheprovider**. Result **14 passed, 1 failed, 0 skipped** in 27.80 seconds.

**Fourteen failures have one confirmed application root cause with an environment trigger.** The host default is CP1252 and UTF-8 mode was off. [Garrett integrated._read](../../backend/equipment_costing/indexes/garrett/integrated.py#L30) reads UTF-8 JSON with the platform default encoding. Direct reads produced different chart labels. The U+00B2 square-foot suffix became U+00C2 followed by U+00B2. The G296-122 flow–pressure label was also garbled. [input_requirements](../../backend/equipment_costing/indexes/garrett/input_requirements.py#L70) uses exact catalogue keys, so the normal parsed pricing path rejects the coordinate. Supplying the corrupted native label reached the explicit native-coordinate path in a diagnostic, confirming the mismatch. That label is unsuitable as a user workaround. Explicit UTF-8 in the test runner stabilizes the baseline while preserving the defect for Engineer 1. Production/source-loader correction belongs to B04 with an encoding regression test and Engineer 2 review.

**One failure is a confirmed test defect.** The manual-price fixture constructs [Settings](../../backend/scenarios_and_uncertainty/monte_carlo/models.py#L95) with its default 20 operating years despite having three approved commercial years. [prepare](../../backend/scenarios_and_uncertainty/monte_carlo/scenarios.py#L26) does not extend the shorter schedule. [The connector](../../backend/revenue/connectors/commercial.py#L32) correctly rejects the mismatch. In an in-memory replay at a fixed equipment draw of $10,250, 20 years yielded partial with no NPV, while explicitly using the approved three-year horizon yielded complete, retained the same equipment cost, produced NPV and had no stage issues. Assign the fixture correction to Engineer 2 under B06, reviewed by Engineer 1. Keep the separate stage/scenario parity requirement open. No application or existing test source was changed during this remediation.

The exact selector list for both targeted runs is each node ID below prefixed by backend/tests/. Classifications identify the primary root cause. No failure was established as a regression introduced by this branch.

| # | Pytest node ID | Classification | Evidence | Owner |
|---|---|---|---|---|
| 1 | test_assumption_completion.py::test_canonical_resolver_completes_one_parameter_without_reselecting_sources | Existing application defect · locale-sensitive | Thermal draft lacks unit_conversion after the chart input is rejected. | E1 · B04 |
| 2 | test_automatic_equipment_inputs.py::test_thermal_adapter_owns_lmtd_and_retains_redundant_ai_binding_audit | Existing application defect · locale-sensitive | LMTD ownership assertion cannot reach its conversion record. | E1 · B04 |
| 3 | test_capex.py::CapexTests::test_connector_uses_quantity_extended_purchase_component_and_is_inactive | Existing application defect · locale-sensitive | HX-1 purchase line is unpriced before the CAPEX connector runs. | E1 · B04 |
| 4 | test_cost_translation.py::test_equipment_installation_and_capex_are_scaled_once | Existing application defect · locale-sensitive | Historical amount is null before testing one-time escalation. | E1 · B04 |
| 5 | test_cost_translation.py::test_unsupported_source_is_retained_as_unpriced_not_fake_2026 | Existing application defect · locale-sensitive | Chart rejection happens before the missing-index check. | E1 · B04 |
| 6 | test_cost_translation.py::test_different_native_indices_aggregate_on_one_dated_currency_basis | Existing application defect · locale-sensitive | Baseline estimate is absent before the synthetic index substitution. | E1 · B04 |
| 7 | test_engineering_sizing.py::test_pump_sizing_flows_into_canonical_cost_model | Existing application defect · locale-sensitive | The flow–pressure axis label fails exact chart-coordinate lookup. | E1 · B04 |
| 8 | test_equipment_resolution.py::test_manual_price_monte_carlo_reconciles_same_canonical_run | Test defect | The 20-year default conflicts with three saved commercial years. | E2 · B06 fixture |
| 9 | test_heat_exchanger_basis.py::test_canonical_model_unit_handoff_and_automatic_resolver | Existing application defect · locale-sensitive | Thermal sizing cannot attach the rejected area chart basis. | E1 · B04 |
| 10 | test_total_equipment_cost.py::EquipmentTotalTests::test_distinct_cost_bases_and_scopes_not_added | Existing application defect · locale-sensitive | Both exchanger prices fail, so mixed-basis subtotals are empty. | E1 · B04 |
| 11 | test_total_equipment_cost.py::EquipmentTotalTests::test_routing_counts_and_source_evidence | Existing application defect · locale-sensitive | The exchanger rows are unpriced, so no combined amount is available. | E1 · B04 |
| 12 | test_total_equipment_cost.py::EquipmentTotalTests::test_unit_prices_require_physical_quantities | Existing application defect · locale-sensitive | The exchanger row prevents the duct-plus-exchanger total. | E1 · B04 |
| 13 | test_total_equipment_cost.py::EquipmentTotalTests::test_unresolved_equipment_is_never_silently_dropped | Existing application defect · locale-sensitive | The priced subtotal expected beside the unresolved equipment is absent. | E1 · B04 |
| 14 | test_unit_conversion.py::UnitConversionTests::test_parsed_adapter_optional_pressure_and_ambiguity | Existing application defect · locale-sensitive | The exchanger area mapping fails before the pressure assertions. | E1 · B04 |
| 15 | test_unit_conversion.py::UnitConversionTests::test_refrigeration_and_area_chart_scaling | Existing application defect · locale-sensitive | The two scaled-area fixtures use misdecoded catalogue labels. | E1 · B04 |

### Clean execution results

On Windows with Python 3.12.14 and pip 25.0.1, a Git archive of HEAD plus the new test manifest was extracted into scratch space. A fresh venv was created with **python -m venv <scratch>/venv**. It had include-system-site-packages=false. The exact install command was **python -m pip install --no-compile --requirement backend/requirements-test.txt** with the archived manifest supplied as an absolute path. It completed against the registry and package cache. **python -m pip check** passed. Direct imports confirmed pytest 9.2.0, httpx 0.28.1, pandas 3.1.1, NumPy 2.5.4 and SciPy 1.18.1. pandas loaded from the fresh venv. The optional OpenPyTEA package was absent. This is a fresh installation of the declared direct dependencies, not a transitive lock or an offline wheelhouse.

Both full pytest commands used the fresh interpreter, separate copies of the archived source, separate scratch SQLite files, no provider credentials, AI_ENABLED=false, FLOWVALUE_CLOUD=false, and PYTHONDONTWRITEBYTECODE=1. One run uses the system default locale to compare directly against the initial audit. The other uses the README/CI UTF-8 mode.

~~~text
python -m pytest backend/tests -q -ra --tb=short -p no:cacheprovider
python -X utf8 -m pytest backend/tests -q -ra --tb=short -p no:cacheprovider
~~~

Existing frontend environment on Node 24.22.1: **node --test** reported **45 passed, 0 failed, 0 skipped**. **node node_modules/typescript/bin/tsc --noEmit --incremental false** exited 0. These were run before the clean frontend check below.


| Clean run | Exit | Pass | Fail | Skip | Subtests passed | Time |
|---|---:|---:|---:|---:|---:|---:|
| Python, Windows default CP1252 | 1 | 1,693 | 15 | 9 | 367 | 817.59 s |
| Python, explicit UTF-8 | 1 | 1,707 | 1 | 9 | 367 | 729.44 s |
| Frontend, Node 24.22.1 | 0 | 45 | 0 | 0 | — | 4.41 s for tests |

Both Python suites collected 1,717 cases and emitted one Starlette TestClient/httpx deprecation warning. The nine skips in each run were one private equipment workbook, one private Charlie snapshot, six private Team 8 workbook cases and the optional OpenPyTEA 3.2.1 comparison. The default run reproduced the same 15 failing node IDs from the initial audit. The UTF-8 run reproduced the targeted result at suite scale. The exact remaining failure was **backend/tests/test_equipment_resolution.py::test_manual_price_monte_carlo_reconciles_same_canonical_run**.

From a separate archived frontend, npm 11.6.2 ran **npm ci --offline --no-audit --no-fund**, then **node --test**, **npm run typecheck**, and **npm run build**, with CI=true and NEXT_TELEMETRY_DISABLED=1. All four commands exited 0. The build included the Scenario and Sensitivity route. The Node test runner emitted the existing module-type warning. No GitHub-hosted job ran. Linux/Ubuntu execution of the amended workflow remains to be verified.

**G0.5 PASS for reproducibility.** A clean checkout can install its declared test dependencies and run both suites. The remaining failure is a known test defect and will keep the backend job red until corrected. UTF-8 mode in the test command does not fix catalogue decoding in ordinary CP1252 application runs. See the [completion report](10-phase-0-completion-report.md).
