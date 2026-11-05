# Isolated stage execution
## Entry engineering workflow (current behaviour)

Entry now has one **Run Engineering & Price Equipment** action. It loads a selected workbook (or reuses the current one), then explicitly runs Engineering data followed by Equipment. Both existing runners remain canonical. The shared register feeds Engineering data and Equipment pages; equipment output includes sizing and available purchase/installation costs. Failed extraction stops this handoff; unpriced items remain visible. The AI checkbox applies to this two-stage workflow. No CAPEX, OPEX, Revenue or Financial runner is invoked.

`POST /api/assessments/{id}/engineering/run` queues this explicit workflow. The individual-stage API remains available for focused reruns. Entry no longer shows separate Engineering data and Equipment run buttons. Other stages still require an explicit run, and ordinary page views do not execute engines. Older descriptions below of a source-only Entry button describe the previous isolated configuration; they are superseded by this section.


The application runs stages only when the user presses that stage's button. A missing prerequisite returns `data_required`; it never triggers another runner. Uploading a workbook loads a source record and runs nothing. The older /run HTTP endpoint now aliases the same explicit Engineering data → Equipment workflow.

| Block | Owns | Required saved output |
| --- | --- | --- |
| `engineering_data` | Workbook extraction, source review, streams and equipment register | Uploaded workbook |
| `equipment` | Equipment sizing, unit conversion, model selection and equipment purchase/installation costs | Engineering data |
| `capex` | Capital estimation | Equipment |
| `revenue` | Revenue Box interpretation, approved prices, quantities and income | Engineering data; explicit schedule, price basis and user approval |
| `opex` | Material consumption, energy, staffing and operating costs | Engineering data; CAPEX/revenue only when selected factors or avoided costs use them |
| `financial` | Cash-flow ledger and investment metrics | Current saved CAPEX, Revenue and OPEX |

Every folder owns its `runner.py`. `equipment/calculation.py`, `capex/calculation.py`, `revenue/input_builder.py` and `opex/input_builder.py` contain the existing canonical adapters moved out of the connected coordinator. Core engineering/economic packages still own the equations. No second ledger or replacement costing engine was introduced.

`registry.py` declares stage ownership and prerequisites. `execution.py` validates input/output fingerprints, records stage results and marks changed downstream results stale. It never runs a prerequisite. `models.py` defines execution envelopes only; numerical payloads use the existing canonical result models through `orchestration.codec`.

`run_stage(store, assessment_id, block_id, use_ai=False)` is the Python interface. The API is `POST /api/assessments/{id}/stages/{block}/run` with `{ "use_ai": false }`. Only this stage may request AI when explicitly enabled. Its proposals cannot replace another stage's assumptions or execute another stage's calculations.

Inputs may be shared, but execution is disconnected. Editing equipment invalidates its dependent results; CAPEX/OPEX/finance stay uncalculated until explicitly run again. A view/price/currency request never runs an engine. Stage output currencies retain the explicit basis used for that run; the previous automatic financial currency recalculation is disabled in isolated mode.

The initial transition preserves a previously connected assessment as a saved version before writing any isolated stage results. Original uploaded workbooks and named versions remain intact. The legacy coordinator is retained for backwards-compatible Python/reference tests, not exposed as an automatic application action.

Monte Carlo retains its own setup/results interface and private simulation jobs. It consumes an explicitly completed financial baseline, not implicit stage reruns that update the project. Reports read saved results.

All public execution entry points now use the same stage coordinator. See [shared-pipeline.md](../../docs/shared-pipeline.md) for routing, historical snapshots and verification.
