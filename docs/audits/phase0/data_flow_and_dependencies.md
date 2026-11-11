# Interface and dependency register

All locations refer to baseline `74f364d`. Field contracts below are observations, not a redesigned schema. Owner E1 = calculations/economics; E2 = schema/orchestration/integration.

| Interface | Producer → consumer | Data / controls | Failure / loss risk | Owner / risk |
|---|---|---|---|---|
| IF-01 | Upload → worker | Bytes, filename; `orchestration/ingest.parse`; `ingestion/limits.py` | Stored formula caches can be missing/stale; source truth is not recalculated. Unsupported format rejected. | E2 / R-06 |
| IF-02 | Workbook reader → parser/register | Workbook/sheet/cell/formula/cache/unit, entity/value IDs | Finite layout heuristics; cross-sheet duplicate values and operating cases need review. No arbitrary external link execution. | E2 / R-06 |
| IF-03 | Register → workbook AI review | Bounded candidate evidence/context; structured proposals | Source-supported vs inferred distinction needs real-file regression acceptance. No live AI correctness evidence here. | E2 / R-07 |
| IF-04 | Equipment register → matching | `equipment_key`, identifier, linked stream context, selected `curve_id` | Textual name equivalence is not proof of service/material/configuration compatibility. | E2 + E1 / R-07 |
| IF-05 | Matching → sizing/conversion | `unit_conversion`, measurement ID, method, input assumptions and source evidence | Metadata and calculator requirements can diverge; direct versus derived dimensions must not be conflated. | E1 / R-05 |
| IF-06 | Sizing → costing | `Measurement`, `ConversionContext`, exact model-specific coordinate(s) | Notebook/native coordinates versus canonical units differ; Nottingham adapter does not expose the same general resolver behaviour as Garrett/OpenPyTEA. | E1 / R-05 |
| IF-07 | Cost → extended equipment result | `CostEstimate`, `CostingResult`, scope, quantity, installation breakdown | Unit capital, per-foot, purchased, installed and bare-module have distinct scopes; purchased-only factors cannot be applied to all. | E1 / R-08 |
| IF-08 | Equipment → escalation → CAPEX | Translation original/target basis, quantity-extended purchase components | CPI proxy is permitted by default. Same-year bypass does not translate months. Mixed bases rejected, not silently merged. | E1 / R-03 |
| IF-09 | CAPEX → OPEX | Named capital money bases; `opex/connectors.py`, `blocks/opex/input_builder.py` | Missing capital bases leave relevant percentages unresolved. CAPEX itself may require OPEX for WC. | E1 + E2 / R-09 |
| IF-10 | Revenue Box → draft → approval | Exact user intent quotations, category IDs, `revenue_authority` fingerprint | Legacy/manual snapshots and current authority path differ; 13-field requested compatibility mapping not located. | E2 + E1 / R-04 |
| IF-11 | Revenue ↔ OPEX | `orchestration/operating_economics.py`, annual revenue bases and avoided-cost application provenance | Circular percentages rejected; unresolved revenue can block dependent OPEX and investment totals while independent cells remain. | E1 + E2 / R-01/R-09 |
| IF-12 | Approved economics → financial inputs | `prepare_study_financials`, typed `FinancialInputs`, operating years, ramp/calendar | Multiple high-level and low-level input builders must preserve annual horizon, year-zero timing, fixed/variable behaviour and price bases. | E1 + E2 / R-01/R-10 |
| IF-13 | Ledger → metrics/UI/export | One ledger; snapshot/report and currency view routes | UI formatting/build does not establish end-to-end parity or stale-result handling in every view. | E2 + E1 / R-10 |
| IF-14 | Changes → stage outputs | `blocks/execution.py` input fingerprints, freshness, preserved previous equipment result | Dependency graph and optional bases must invalidate all consumers without wiping approved assumptions. | E2 / R-09 |
| IF-15 | Assessment → named version/reopen | SQLite optimistic revision and immutable-by-API version insert; reopen forks new ID | Synthetic reopen/stale writer passed; cloud tenant ownership and backup/restore not audited live. | E2 / R-11 |
| IF-16 | Accepted study → Monte Carlo | Parameter target paths, units, marginals, correlations → canonical pipeline | Unsupported models remain missing. Completeness depends on all economic stages; existing fixture is partial. | E1 + E2 / R-01/R-12 |
| IF-17 | Natural-language opportunity → scenario | R39 planned review/research workflow | Complete proposal/history/visual reconciliation not demonstrated. Do not create sales from an outlet or silently approve a baseline. | E2 / R-13 |

## Actual numerical handoff

`blocks/equipment/calculation.py` maps chosen plan rows to register keys, resolves exact tag aliases, applies conversion/sizing, and calls total costing. `blocks/capex/calculation.py` prepares typed equipment costs and explicit factor configuration. `orchestration/pipeline.py` remains another orchestration entry to the same engines; a second orchestration route is not a second numerical engine, but parity needs verification.

`revenue/authority.py` fingerprints commercial assumptions, stream source records, production/calendar inputs and Revenue Box text. `financial_modelling/connectors/operating_economics.py` translates the saved economic policy to a typed dated ledger. It currently constructs explicit unlevered planning tax/depreciation/financing policies; these are not jurisdictional determinations.

## Missing versus zero and approved baselines

Core types use `None`/issues for unsupported values and preserve explicit zero overrides. Equipment, OPEX and Revenue expose known subtotals alongside unresolved items. Full investment metrics can correctly remain unavailable when dependent annual schedules fail. Never relabel a known subtotal as a complete project total.

No original assessment, workbook, approved assumption or saved version was edited for this audit. New version tests use temporary synthetic SQLite stores only. Existing local databases and cloud data were not opened for mutation. Complete live reopen/approval/tenant testing remains BLOCKED pending a designated nonproduction project and Engineer2 agreement.

## Dimensional consistency review (B2/B3)

| Boundary | Existing safeguard | Residual risk / reference |
|---|---|---|
| Mass flow ↔ liquid volumetric flow | Canonical converter/bridges require density and compatible flow units; conversion evidence retained | Density must match composition, phase, temperature and pressure; arithmetic alone cannot validate it (R-05/R-07) |
| Gas standard ↔ actual volume | Explicit MW, absolute pressure, absolute temperature, compressibility and condition context | A standard flow is not an actual flow at compressor/sizing conditions; no universal standard state (R-05) |
| Gauge ↔ absolute ↔ differential pressure | Conversion context and pressure-role metadata; pump uses differential pressure | Operating/inlet pressure cannot substitute for pump ΔP or mechanical design pressure; model-required basis can still be selected wrongly (R-05/R-07) |
| Absolute temperature ↔ temperature difference | Converter distinguishes temperature and delta-temperature roles | Celsius offsets must never enter LMTD differences or already absolute K inputs (R-05) |
| Duty ↔ electrical/shaft/hydraulic power | Energy cost methods and bridge roles distinguish bases and efficiency | Thermal duty is not measured electrical demand; load/efficiency can be an assumed scenario, not a fact (R-05/R-02) |
| kg/h ↔ vessel volume/area | Sizing methods require residence time/density or duty/U/LMTD/loading | No generic unit conversion can create a missing engineering design basis; parameters remain explicit assumptions (R-02/R-07) |
| Hourly ↔ annual | Operating hours, ramp and saleable/sold fractions stored in annual adapters | Year numbers, construction offsets and calendar/horizon edits can misalign schedules; reproduced R-01 |
| Currency ↔ price year | Decimal FX and same-series index ratio are separate mechanisms | Consumer CPI is a purchasing-power proxy; pinned FX does not imply a live price; source observations need verification (R-03) |
| Count ↔ physical length/area/volume | Cost scope and quantity-extension handling distinguish per-item and unit-price models | AB/duty/standby semantic identity, per-foot quantities and package auxiliary scope still need review (R-08) |

Hard-coded numerical constants include `8.31446261815324` in gas/compression calculations, psi/US-gallon definitions in `unit_aliases.py`, and 3600/1000/100000 unit factors. These are explicit conversion/model constants, not automatically defects. Their exact definitions, precision and consistent use across parser/bridge/engine paths require independent reference checks. Assumed U, residence time, density, efficiencies, tariffs, selected factors and ramp profiles are much larger model risks than extra display precision.

Graph regression, equipment estimates and IRR root isolation use floating point; finance/FX/factor arithmetic predominantly uses Decimal precision40. Nonfinite/positive guards exist but no global numerical-error budget or signed per-method tolerance register was found. Exponent/fit extrapolation, missing published ranges, duplicate formula implementations (parser versus canonical units; registry aliases) and finite bounded IRR searches remain review items. AI selects assumptions and methods; no audited path authorises replacing engine arithmetic with an arbitrary LLM numerical answer. This audit did not exhaustively prove that property across every live execution route.
