# Original baseline and Phase0 verification

Date 2026-11-10. Original commit **74f364d2ebdcbc67bd0732937f59ef6a3704dce3**, branch **main**, origin `sa-anyan/flowvalue-ai`. Tracked tree was clean before audit edits. **127 untracked duplicate-suffix files** were present and left untouched; see `evidence/untracked_inventory.txt`. No existing equation, coefficient, production code or failing test was changed.

## Environment and execution conditions

Python **3.12.10**, existing project venv from the local archive. Installed versions inspected: pytest9.1.1, FastAPI0.162.0, uvicorn0.54.0, pydantic2.14.1, python-multipart0.0.32, openpyxl3.1.5, xlrd2.0.2, defusedxml0.7.1, NumPy2.5.4, SciPy1.18.1, pandas3.1.0, httpx0.28.1, OpenPyTEA3.2.1, xlwt1.3.0. This is an installed-environment observation, not a transitive lock/SBOM certification. Root notices cite a removed backend pyproject/uv lock; current runtime requirements files are the actual deployment inputs.

Committed source was unpacked with `git archive HEAD` into a temporary clean directory. Frontend reused installed `node_modules` through a symlink; Python reused its existing venv. Provider credential-like environment keys were removed, `AI_ENABLED=false`, `FLOWVALUE_CLOUD=false`, and a temporary SQLite path were set. A temporary Python socket guard rejected nonlocal network connections. No live AI/market research or cloud API was invoked. The parser subprocess strips most environment variables itself, so this guard is not represented as an OS-wide network sandbox.

The user worktree was not cleaned or reset. Initial `pytest --collect-only -q backend/tests` in that worktree found **2,877 tests**, including duplicate untracked files. Clean tracked baseline collected/executed **1,720 tests**; 367 unittest subtests are reported separately. Counts from dirty discovery must not be used as committed coverage.

## Original results — before code/CI additions

| Command / scope | Actual result | Evidence |
|---|---|---|
| `python -m unittest discover -s backend/tests -v` (documented) | **336 passed**, exit0 | `evidence/unittest.log` |
| `python -m pytest backend -q --tb=short` | **1,717 passed, 1 failed, 2 skipped**, **367 subtests passed**, 7 warnings; exit1; 189.16s pytest time | `evidence/pytest.log` |
| `node --test tests/*.mjs` (existing CI command) | **4 passed**, exit0 | `evidence/frontend_documented.log` |
| `node --test` with explicit committed `.mjs` and `.cjs` files | **45 passed**, exit0 | `evidence/frontend_all.log` |
| `npm run build` | Passed; Next production routes built, exit0 | `evidence/build.log` |
| `python -m pip check` | Passed, no broken requirements found | `evidence/pip_check.log` |
| Fresh Python3.12 venv; `pip install --no-index -r backend/requirements-monte-carlo.txt` | **BLOCKED**: no local FastAPI0.162.0 distribution available; no network install attempted | `evidence/clean_environment.log` |

Unittest does not discover the full pytest function/parameterized suite. Build success is not browser interaction or independent numerical verification. The optional installed OpenPyTEA reference test did execute in this environment; the two skips are the private real Charlie workbook and private Charlie simulation snapshot, unavailable in the committed fixture set. Matplotlib/scienceplots deprecation warnings came from the optional OpenPyTEA reference dependency.

### Original failure, preserved

`backend/tests/test_equipment_resolution.py::test_manual_price_monte_carlo_reconciles_same_canonical_run`, assertion at line375: expected `complete`, got `partial`.

A separate in-memory reproduction used the existing synthetic fixture and existing sampling functions, no application edits or stored project changes. It reproduced:

- Equipment price present and equal to sampled manual price; no unpriced equipment in this case.
- Revenue/operating economics: **Commercial annual schedule must match operating years in order**.
- OPEX: missing `annual_revenue` bases for administration, packaging/storage, research/development and royalties.
- Finance: pending dependencies, so complete investment metrics unavailable.

This identifies a schedule/adapter problem for triage (R-01), not an incorrect equipment-cost equation. Root-cause repair was intentionally not performed in Phase0. The original failure was not marked xfail, skipped, or weakened.

## Phase0-only changes and checks

| Change | Local verification | Result |
|---|---|---|
| `backend/tests/test_phase0_version_protection.py` | `python -m pytest backend/tests/test_phase0_version_protection.py -q` | **2 passed**; synthetic named-version reopen/fork and optimistic stale-write protection |
| `tools/phase0_baseline_checks.py` | `python tools/phase0_baseline_checks.py` | **545 tracked Python files parsed; 0 narrow secret-pattern findings** before adding new files to Git |
| Frontend CI test glob | Full committed frontend suite already executed above | 45 passed; command now includes both `.mjs` and `.cjs`; no frontend component changes |
| Frontend typecheck | `npm run typecheck` in current frontend | Passed, exit0 |
| Backend CI + test dependency manifest | Static workflow inspection and existing-version metadata | New job defined; **hosted GitHub execution not run**; will expose existing failure rather than hide it |
| Audit artefacts | CSV parsing, row counts, required files, source-path and production-diff review | See final report; not an engineering validity certificate |

The narrow secret guard suppresses values and checks tracked text for selected provider-token/private-key patterns plus Python AST syntax. It is not a complete secret scanner, runtime log sanitizer, dependency audit, auth audit or proof that no credential exists. No secrets or full environment dumps were included in evidence. Existing logs were reviewed before copying; machine-specific environment paths were redacted.

New test dependencies are existing test libraries pinned to observed versions in `backend/requirements-phase0-tests.txt`; optional installed OpenPyTEA parity can skip in CI unless separately installed. The pinned upstream reference implementation already present in tests still exercises catalogue parity. No third-party source was incorporated during Phase0. Installed runtime/transitive licence verification remains Engineer2 work.

## Reproduction

Use a clean checkout of recorded commit for original results. Preserve the duplicate files separately; do not remove them implicitly. Python3.12 plus `backend/requirements-phase0-tests.txt` describes the new CI environment; original optional OpenPyTEA parity additionally needs the exact3.2.1 reference installed. Use an isolated temporary `FLOWVALUE_ASSESSMENT_DB`, no cloud/provider credentials, and no production data. Run full pytest, both frontend test extensions, typecheck and build. `.github/workflows/backend-baseline.yml` does not supply provider secrets or a production database.

Fresh dependency installation and the new hosted job remain unverified. No test outcome is inferred from a prior deployment or historical acceptance document.

## Numerical verification inventory

`engineering_methods_register.csv` contains 236 static numerical-function candidates (helpers/delegates included) plus12 explicit reviewed sizing-registry contracts. 112 of the236 candidates have a static direct module test reference;124 have no discovered direct reference. This is **not** execution coverage: indirect tests can exercise methods and direct imports can still lack an independent oracle. No line/branch percentage is claimed.

`evidence/test_classification.csv` indexes719 test functions by initial purpose (regression, dimensional, boundary, integration, smoke). Name-based classification is marked provisional; it does not certify independent references. Explicitly reviewed examples:

| Example | Evidence classification | Limit |
|---|---|---|
| `test_financial_modelling.py:226` | Independent synthetic arithmetic: specified annual FCFF, direct discounted-sum NPV, zero IRR and payback | Validates this synthetic case, not all financing/tax policies |
| `test_financial_modelling.py:575` | Source-reference numeric constants (Garrett table6-3) plus timing comparison | Original table transcription not independently rechecked: SOURCE NOT VERIFIED |
| `test_openpytea_catalogue.py:41` | Independent software implementation parity against pinned upstream evaluator | Shared source dataset; not independent textbook or industrial truth |
| `test_unit_conversion.py` | Unit/dimensional and invalid-context tests | Complete parser-to-cost dimensional equivalence not demonstrated |
| `test_capex.py`, `test_opex.py` | Synthetic totals, factor/base, boundary, overlap and integration checks | Some expected values derive from source definitions; not all independently sourced |
| `test_engineering_workflow.py` | Integration with mocked AI | Not proof of real model conceptual correctness |
| `test_phase0_version_protection.py` | Synthetic storage integration/invariance | No cloud or production history restore was exercised |

Full per-method independent oracle review remains PARTIAL and must precede blanket numerical-verification or industrial-validation claims.
