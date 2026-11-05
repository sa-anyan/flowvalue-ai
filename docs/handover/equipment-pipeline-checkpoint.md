# Equipment pipeline checkpoint — 5 November 2026

## Start here

This branch contains the **whole current application snapshot**, including the
backend stage architecture, frontend explorer pages, canonical equipment matcher,
conversion equations, automatic assumption resolver, tests and synthetic fixtures.
Check out `codex/stage-isolation`; the default branch may show an older application.
This is a development checkpoint, not a production-ready or independently validated release.

## Current workflow

Entry **Run Engineering & Price Equipment**, with AI enabled:
1. Parse/review the uploaded workbook into the canonical engineering register.
2. Match equipment names/functions to catalogue candidates using one canonical LLM matcher.
3. Select a provisional configuration for known candidate families, where defensible.
4. Use explicit model-compatible equipment dimensions first; otherwise populate
   missing conversion/sizing assumptions with labelled LLM estimates.
5. Python derives supported M&E values from source references and executes the
   allowlisted conversion/sizing equation. Derived bindings recalculate from source.
6. The existing Python equipment cost models price the resulting coordinate.
7. Retain per-item failures, source/graph/extrapolation limitations and user overrides.

The initial Entry API defaults to AI enabled; explicit opt-out remains available.
The Unit conversion assumptions drawer displays editable values, provenance,
selected source measurements, equation/file, preview and save/run actions.
CAPEX, OPEX, Revenue and Financial stages remain explicit separate runs. Reading a
page does not run an engine. Revenue Box authority remains in force. Historical
snapshots are not silently recalculated or reused as fresh price outputs.

## Where to find the implementation

| Area | Location |
|---|---|
| API and Entry execution | `backend/api/app.py`, `backend/blocks/engineering_workflow.py` |
| Stage ownership/receipts | `backend/blocks/` |
| Canonical equipment matcher | `backend/equipment_matching/` |
| Conversion/sizing selection | `backend/equipment_costing/unit_conversion/bridges/automatic.py` |
| M&E-derived inputs | `backend/equipment_costing/unit_conversion/bridges/derivations.py` |
| Liquid/gas/thermal/geometry equations | Other modules in `bridges/` |
| Existing cost models | `backend/equipment_costing/indexes/` |
| Equipment handoff/calculation | `backend/blocks/equipment/` |
| Equipment drawer | `frontend/src/blocks/equipment/` |
| Shared frontend workspace | `frontend/src/blocks/shared/project-workspace.tsx` |
| Detailed pipeline notes | `docs/shared-pipeline.md`, `backend/blocks/README.md` |
| Synthetic workbook fixtures | `backend/tests/fixtures/equipment_inputs/` |

No new thermodynamic or parallel financial engine was introduced. Original
licensing and third-party notices remain unchanged.

## Recorded validation

- Latest focused implementation checks: 80 passing tests before the final initial-run
  regression; the initial-run plus automatic-input subset then passed 25 tests.
- Frontend production build passed after the initial-run changes.
- Full backend suite run for this checkpoint: **551 passed, 6 failed, 2 skipped**,
  with 367 passing subtests; elapsed 83.92 seconds. The full suite is **not green**.
- Four synthetic workbook layouts pass through parsing, post-match input resolution
  and actual Python costing with controlled (fake) provider decisions. That verifies
  integration and arithmetic, not real-model reasoning reliability.
- Live fresh Charlie runs used the configured provider and Python calculations,
  without copying the workbook's equipment prices or previous sizing inputs:

| Recorded run | Register entries | Priced entries | Unpriced |
|---|---:|---:|---:|
| Before broader assumption population | 32 | 1 | 31 |
| After broader assumption population | 32 | 12 | 20 |

Sixteen entries in the latter run had enabled conversion/sizing specifications;
its provenance register contained 31 LLM-estimated inputs and six M&E-derived inputs.
These are register-entry counts; aliases have not been fully reconciled. Preliminary
graph readings, extrapolation and price-escalation proxy warnings remain present.
Original local assessments were preserved.

**Founder update:** the founder subsequently reported approximately **19 matches**.
This is a user-reported matching count, not an independently checked pricing count.
Keep that matching work pinned for later; do not substitute it for the 12/32 recorded
pricing result or automatically claim 19 physical units/prices.

## Outstanding problems

- LLM interpretation/configuration choices remain variable; passing schema checks
  does not certify physical suitability or reproduce a human engineer consistently.
- Some matched items remain unpriced because assumptions, conventions, suitable
  scope, extrapolation justification or model coverage are unresolved.
- Electrolyser package costing is not available merely through a vessel proxy.
- Aliases and duty/standby scope need reconciliation before a trustworthy plant total.
- Generic final error messages can hide deeper input-resolution causes. Inspect the
  matching register, input-resolution audit and per-line cost issues together.
- Execution freshness/ready receipts are distinct from complete pricing coverage;
  some workflow wording still sounds complete when the equipment result needs review.
- The following full-suite failures are recorded for the next engineer. They were
  not hidden, skipped or repaired merely to make the checkpoint appear green:

- `backend/tests/test_commercial_intent.py::IntentTests::test_entry_upload_passes_commercial_context_into_assessment`
- `backend/tests/test_commercial_strategy_agent.py::AgentTests::test_api_creates_separate_scenario`
- `backend/tests/test_equipment_resolution.py::test_manual_price_monte_carlo_reconciles_same_canonical_run`
- `backend/tests/test_monte_carlo.py::test_canonical_financials_and_reproducible_simulation`
- `backend/tests/test_monte_carlo.py::test_api_freezes_baseline_and_rejects_stale_and_wrong_parent`
- `backend/tests/test_monte_carlo.py::test_preflight_uses_reviewed_central_assumptions`

These include commercial API expectations and Monte Carlo integration/reconciliation.
Investigate each against the isolated-stage architecture; do not assume all are
obsolete tests or weaken validation without understanding the failure.

## Reproduce locally

Use Python 3.12 and Node 24. From the repository root, create your own Python virtual
environment and install `backend/requirements-monte-carlo.txt` (which includes the
orchestration requirements). Install your usual test tooling, including pytest and
httpx for API tests. Frontend uses its committed lockfile (`npm ci` in `frontend`).

Configure AI only in the backend environment using the existing `.env.example`.
Never put provider keys into browser variables, source, test fixtures or Git.
The example command below assumes environment variables are already loaded by your
shell/environment manager; optional dotenv loading needs its normal runtime support.

```sh
python -m uvicorn backend.api.app:app --host 127.0.0.1 --port 8001
```

In a separate terminal:

```sh
cd frontend
FLOWVALUE_BACKEND_URL=http://127.0.0.1:8001 npm run dev -- --port 3001
```

Open `http://127.0.0.1:3001/entry`. Upload your own workbook and describe the process.
Saved local assessment IDs and links are not portable to another checkout.

```sh
python -m pytest backend/tests -q
python -m pytest backend/tests/test_automatic_equipment_inputs.py backend/tests/test_unit_conversion_bridges.py backend/tests/test_equipment_matching.py backend/tests/test_engineering_workflow.py -q
npm --prefix frontend run build
```

The repository is public. This checkpoint excludes original private workbooks,
raw live-study assessment exports, provider credentials, local databases and local
outputs. The synthetic fixtures and this aggregate handover describe the current
state without publishing those assets. Production deployment was not requested
as part of saving this checkpoint.
