# Equipment resolution, user costing and uncertainty

## Gap assessment and reuse

The current checkout already has source-linked workbook registers, an Equipment Specialist and Chemical Engineer handoff, canonical unit conversions, preliminary sizing, a Garrett catalogue with factors/ranges, comparable-price scaling, incremental CAPEX/OPEX/revenue/finance, editable equipment drawers, and a two-page Monte Carlo module. Names of other methodologies in product requirements do not establish executable Turton/Guthrie/Seider models: the current equipment registry explicitly supports Garrett.

This change extends those paths. It does not add a second financial engine, parser, property database, universal equipment classifier or parallel assumption store.

## New and extended components

- `backend/equipment_resolution/scope.py`: explicit confirmed aliases and separately specified physical assets under one source tag. A split replaces its parent, retains source lineage and cannot create new stream connections. Tags ending in AB never establish duty/standby quantities by themselves. Duplicate keys, invalid alias targets and cycles are rejected.
- `knowledge.py`: cached live metadata over the existing sizing registry and costing catalogue, with required inputs and failure-resolution guidance. No project-specific assumptions become universal default ranges.
- `review.py`: a common resolution register separating scope, sizing, model, source, quantity, cost status and exceptions. Published statuses distinguish model, benchmark, analogy, user price and unresolved records. Confirmed aliases are accounted for separately.
- `comparison.py`: previous versus updated values read from the canonical outputs. Saved edits retain the preceding plan/results and publish changes after Python reruns.
- `backend/equipment_costing/manual.py`: approved per-unit prices, purchased/installed scope, optional installation allowance or explicit purchased split, currency/year/source/notes, source-preserving shared FX conversion. No equipment size, public URL or fabricated CEPCI is required for a private quotation. PRICE_BASIS=1 is a monetary numeraire, not a published cost index.
- `backend/engineering_sizing/thermal.py`, `compression.py`, and the extended ion-exchange function: deterministic phase-change duty, evaporated water, single-stage constant-property gas compression and equivalent-capacity resin sizing. Existing exchanger, gas-volume, pump, filter, vessel and dryer functions remain canonical.
- The existing adapter supports `vaporizer_area`. An explicitly selected phase-change assumption basis is not silently replaced by contradictory workbook enthalpy. Alternative source duties and their differences are retained. Sensible heat alone cannot establish vaporisation duty. Property values and applicability must be supplied or explicitly assumed; no thermodynamic database or external research is implied.
- The existing specialist handoff sees the new methods, keeps locked manual prices, proposes project-specific editable assumptions and retains unsupported exceptions. Its pre-run calls are cached/bounded; there are no per-iteration LLM calls.

The API exposes `/api/catalogue/equipment-knowledge` and owner-scoped `/api/assessments/{id}/equipment-resolution`. The existing equipment drawer now exposes physical interpretation, aliases, arrangement, user prices/installation scope, approval/lock and explicit split definitions. Split children retain independently editable sizing and prices. Advanced asset splitting uses a structured editor; it is not an automatic PFD drawing interpretation tool.

## Cost and installation boundaries

An approved manual price takes precedence over model/benchmark proposals until explicitly changed or removed. Purchased and installed amounts are distinct. An installed-only quote is visible but cannot feed factorial CAPEX without an explicit purchase split. Quantities extend unit prices exactly once. Unknown installation is not zero.

Garrett's plant installation is embedded in its direct-cost factors. Equipment-level installation breakdowns are retained and shown separately; they are not added again to Garrett CAPEX. A manual package allowance does not automatically replace the whole-plant Garrett factor structure. A project needing exact installation take-offs must use an explicitly reviewed capital-scope methodology rather than claim both charges.

Native-year escalation remains the existing policy. After native escalation, an explicitly selected calculation currency uses the shared pinned FX snapshot and keeps original quote metadata. Unsupported currency-year inflation observations remain unresolved. Mixed periods/currencies cannot silently aggregate. The UI exposes calculation currency separately from quotation currency.

## Monte Carlo integration

Exactly the existing Setup and Overview routes remain. Discovery now includes manual prices and independently specified split-asset parameters in the same saved ledger. Confirmed aliases do not count as missing physical assets. New physical bounds cover phase fractions/moisture and compression inputs. Each draw calls the same canonical sizing, equipment, CAPEX, OPEX and financial paths. Invalid calculations and unresolved equipment are retained; they do not manufacture financial-risk denominators. Calculation-source fingerprints include the resolution package.

Optional AI preparation is a distinct pre-run draft; user edits/approvals are not silently applied to an approved baseline. No external price research was performed in this implementation. Electrolyser/vendor benchmarks were not invented to fill catalogue gaps.

## Real Charlie acceptance evidence

Baseline `1cab46f380404928adce1514bfeb7326` remains unchanged. A separate draft (`f904e064142444a8950d6c74036d70ce`) was rerun with the actual saved M&E register and a live, four-batch Chemical Engineer review. No external research tools were invoked. The live review took approximately 94 seconds and increased preliminary priced records from 19 to 22 of 32.

There are **32 registered equipment records and a nominal quantity sum of 44 units** before alias/scope review. This is not a verified count of unique physical plant assets: two aliases remain proposals, T-104 may need splitting, and package boundaries remain open. The system does not claim an exact unique-asset count where source interpretation is unresolved.

| Reference entry | Root cause and resolution outcome | Costing status / remaining action |
|---|---|---|
| T-104 | One source tag covers acid and caustic services; distinct-asset support added, but no unilateral split or compatibility approval | Unresolved; confirm segregated assets and their configurations |
| T-101 | Possible alias of T-101AB | Unresolved pending confirmation; confirmed-alias path tested to avoid duplicate charges |
| R-101 | Electrolyser package has no supported catalogue model/boundary or sourced benchmark | Unresolved; scoped specialist/vendor benchmark or approved user quote required |
| T-105 | Liquid CO2 storage duration, pressure-boundary configuration and applicable density are insufficient | Unresolved; generic low-pressure storage shell not substituted |
| HE-101 | Phase-change duty/area missing; workbook energy terms not reconciled | Preliminary G286-091 shell-and-tube model, explicit latent/U/LMTD assumptions; unverified graph/boundary extrapolation flagged |
| HE-102 | Ammonia phase-change duty conflicts with energy records | Preliminary G286-091 using explicit phase-change scenario; conflicting enthalpy retained, unverified extrapolation flagged |
| S-201 | Supplied throughput below current centrifuge range; no defensible replacement/scale basis | Unresolved; no clamping or invented small-machine benchmark |
| FT-201 | Waste component does not establish filter feed/hydraulic duty or full configuration | Unresolved; confirm feed, filtration service and possible alias |
| PD-201AB | Wet-food stream does not uniquely identify machine function | Unresolved; press/dryer alternatives are not interchangeable facts |
| PD-201 | Possible duplicate of PD-201AB | Unresolved pending physical-scope confirmation |
| C-201 | Gas-pressure/balance contradiction prevents defensible chamber sizing | Unresolved; no silent atmospheric-pressure substitution |
| T-301 | Storage versus packaging boundary ambiguous; hold-up absent | Preliminary G303-144 storage-shell proxy with explicit bulk-density/storage/fill assumptions; packaging line excluded and still a scope issue |
| R-201 | Oxygen feed is not liquid broth throughput or kinetic residence time; full bioreactor package missing | Unresolved; do not size a broth vessel from gas feed |

All 13 were evaluated against the real register. The three new prices are **uncalibrated preliminary engineering scenarios**, not independently verified equipment designs or vendor prices. Ten records still require clarification or sourced models. All existing priced selections were retained. Source/data contradictions and model/extrapolation warnings remain inspectable.

Private reproducibility evidence, before/after snapshots, specialist audit, run scripts, Monte Carlo job and browser checks are under `outputs/equipment-resolution/`. The separate UI test snapshot uses an explicitly synthetic quote solely to test manual edit/save/rerun/lock/reload; its price is not Charlie evidence.

## Verification and remaining limits

Automated tests cover independent physical equations, unit handling, manual/installed splits, FX provenance, invalid prices, aliases/cycles/conflicting tags, explicit splits, source-stream integrity, downstream cost/financial changes, seeded manual-price sampling and source-duty contradictions. Full-suite and browser results are recorded with the private report.

Remaining work includes independently sourced specialist package correlations/benchmarks, thermophysical applicability review, calibrated uncertainty, explicit confirmation of ambiguous assets and missing auxiliaries, and broader unfamiliar-workbook/PFD acceptance cases. This is not universal industrial validation. Automatic drawing extraction was not added. The source catalogue remains Garrett plus user-supplied reviewed comparables/manual estimates; no fictitious alternative-method library was added. The live specialist does not independently establish safety, material suitability, food-contact approval or plant completeness.

The existing 5,000/10,000 Monte Carlo options remain; only the 1,000-run reference was exercised here. Distributed durable workers, automatic resume, calibrated probability of model correctness and fully automatic package-boundary resolution remain outside the delivered implementation. No deployment was performed.

### Final run and changed-file register

The actual Charlie uncertainty study (`01ecd9fc7022403d9ec0c6bfa26671af`) completed 1,000 draws in 292 seconds locally. Every draw priced 22/32 registered records (68.75%). There were 1,000 partial draws, zero failed draws and zero invalid calculations; complete-scope financial runs remained zero. Consequently negative-NPV and target-IRR probabilities are not estimable from this study. Existing operating-cost dependencies also remain disclosed. Five recorded draws were independently replayed through the canonical engines and matched equipment costs, CAPEX/OPEX components, metrics, coverage and cash flows exactly. The original baseline was unchanged; no LLM ran per iteration.

The full suite passed **462 tests and 367 subtests**. Frontend production build/type checking passed. Browser acceptance exercised a separate synthetic manual-price scenario through the actual drawer, API save, Python rerun, updated CAPEX, before/after view, lock preservation and reload, at 390/768/1440px. That synthetic quotation was not used in the real Charlie study.

Files added: `backend/equipment_resolution/{__init__,scope,knowledge,review,comparison}.py` and its README; `backend/equipment_costing/manual.py`; `backend/engineering_sizing/{thermal,compression}.py`; `backend/orchestration/approved_equipment.py`; `backend/tests/test_equipment_resolution.py`; `frontend/src/components/equipment-price-editor.tsx`; this report.

Files extended: `backend/engineering_sizing/{adapter,registry,ion_exchange}.py`; `backend/equipment_costing/total_cost/calculator.py`; `backend/orchestration/{pipeline,service,design_handoff,pricing_status}.py`; `backend/api/app.py`; `backend/scenarios_and_uncertainty/monte_carlo/{discovery,scenarios,engine,service}.py`; `frontend/src/components/assessment-workspace.tsx`.

No new dependencies, frontend pages or alternative financial engines were introduced. The task does not establish that all requirements of a universal industrial equipment resolver are complete: ten real reference records and independent engineering validation remain open.

Split-asset source assignment is explicit: children receive only selected existing `source_value_ids` and selected existing `stream_keys`. Unassigned parent connections are retained as unresolved, not duplicated onto each child. This has a dedicated regression test.
