# B08 · Monetary basis and timeline contracts

**Status: PARTIAL.** The standalone models validate metadata supplied by review fixtures. Production readers, writers, calculations, exports and saved assessments continue to use their existing contracts. Engineer 1 approval is pending at the handoffs below.

## Current-state audit

| Boundary | Current representation and consumers | Basis and risk | Candidate mapping |
|---|---|---|---|
| [Equipment costing](../backend/equipment_costing/total_cost/calculator.py) and [translation](../backend/equipment_costing/cost_to_future/cost_translation.py) | EquipmentCostLine has nullable float amount and quantity, quantity unit, scope, calculation evidence and separate purchase/installation/combined components. Scoped subtotal carries currency, period and index. Manual quotes enter through the existing approved pricing path. CAPEX reads scoped inputs and source evidence. | Raw quote, calculated component, extended price and translated value cannot be inferred from one amount or from a display tag. Native and comparison results can differ. | Use a stable costing record key. Map explicitly identified components, original and translated basis, quantity, source and approval evidence. Keep float-origin amounts outside the precise handoff until an explicit conversion rule is approved. |
| [CAPEX](../backend/capex/models.py) | EquipmentCost and UnitCapitalCost carry different scopes, quantities, period/index, provenance and provisional flags. CostLine contains Decimal or null, a named factor base, status, rationale and source. WorkingCapital distinguishes a supplied override from an exclusion. OPEX and Finance consume selected totals. | Basis is explicit on the result or input but inherited by many factor lines. Applying purchase factors to installed or pre-costed totals can double count. A nullable total can coexist with partial coverage. | Carry scope, extension state and effective basis with each handoff. Preserve base references, exclusion reasons and coverage. |
| [OPEX](../backend/opex/models.py) | Basis/MoneyBase contain currency and year provenance. Decimal line amounts include fixed/variable behavior, cash/noncash accounting, scope, rate and quantity. Result retains nullable fixed/variable/cash totals alongside a resolved subtotal. | Basis usually belongs to the parent result. A resolved subtotal cannot stand for a complete total. Avoided cost offsets belong to a specified eligible line. | Preserve parent basis, behavior, target line ID and coverage when adapting the ledger. |
| [Revenue](../backend/revenue/models.py) and [authority](../backend/revenue/authority.py) | Assumption can carry a missing or Decimal value, units, provenance, uncertainty, status and date. Product and commercial schedules use operating-year numbers. CommercialLine separates quantity/rate/payment, eligibility and exclusions. AvoidedCost names the OPEX target. | Approved schedule, rate price period, accounting year and project basis are different. Zero payment, absent rate and excluded opportunity have different meanings. | Preserve source, authority, rate denominator, temporal coverage and price basis per line. Keep savings separate from sales. |
| [Finance](../backend/financial_modelling/models.py) and [study connector](../backend/financial_modelling/connectors/operating_economics.py) | Money holds Decimal or null, currency, integer price year and source. Study connector extracts the first matching year from CAPEX period and gets calendar start from policy or assumption date. Finance owns dated spending, depreciation, tax and reporting. | Financial price year and calendar year are separate. Inferring the first year from a period string can hide an ambiguous source. | Map explicit source basis and dated ledger periods. Keep ambiguous legacy periods in their original representation until reviewed. |
| [Cashflow editor](../backend/blocks/cashflow/schedule.py) and [view](../backend/blocks/cashflow/view.py) | Project year 0 is displayed separately. With construction count C, the view maps project year C+1 to operating year 1. CAPEX, startup and working capital timing use project-year keys. Ramp uses operating indices. Revenue realization keys are project-year scoped. | Schedule edits currently repeat final commercial/avoided-cost rows for longer horizons and label the repetition provisional. Saved legacy timing can fall back to different weights. | Use explicit period rows plus separately approved timing and commercial coverage. |
| [Monte Carlo](../backend/scenarios_and_uncertainty/monte_carlo/scenarios.py) and [exports](../backend/scenarios_and_uncertainty/monte_carlo/exports.py) | Scenario settings can change operating life and trim long schedules. A short schedule is left incomplete. Exports serialize scenario results and summaries. | Horizon treatment differs from the cashflow editor. Same-tag cost projection collision from B07 is separately open. | Share period coordinates and authority coverage with stages before adopting export fields. Retain current scenario arithmetic. |
| [Assessment API](../backend/api/app.py), [currency view](../backend/currency_conversion/assessment.py) and [store](../backend/orchestration/store.py) | Stage results, receipts and plans live in JSON snapshots. Cashflow and scenario export endpoints project those results. The API also supports a currency presentation view. | A presentation translation is not approval of a new native calculation basis. Reinterpreting older payloads on read can invalidate saved totals or receipts. | Keep legacy reads and saved numerics intact. Add metadata via adapters only when source evidence is explicit. |

## Implemented validation schema

[Contract models](../backend/orchestration/monetary_timeline_contracts.py) accept Decimal, integer or decimal text for amounts and serialize amounts as decimal strings. Binary float inputs are rejected. An explicit native basis includes currency, year, optional exact date and an optional index series/value pair. A comparison amount and basis require a translation reference and retain the native values. A unit price has an explicit denominator and any supplied quantity unit must match it literally. Scope names are supplied by the caller. Scope vocabulary and eligible subtotal membership remain shared decisions.

Present values may be zero or signed. Missing, unresolved, excluded and not applicable values carry null. Authority is separate from availability. An approved line requires an approval reference. Legacy rows with insufficient metadata stay on their existing read path and are not forced into this stricter schema.

Compatibility checking reports differences in amount availability, effective currency, price period, index, scope, representation and denominator. An empty list only means these metadata agree. The caller still needs inclusion, authority, quantity-extension and duplicate checks before summing. No conversion or aggregation is performed.

Timeline rows explicitly carry project year, calendar year, phase and nullable operating year. Project and calendar coordinates advance together. Operating years, where present, start at 1 and are contiguous. Startup can be before operation or in an operating period when specified explicitly. Commercial coverage reporting lists uncovered operating indices without creating new payment terms.

Legacy-shaped input and explicit review examples:

~~~json
{"tag":"P-101","amount":0,"period":"2024","currency":"USD"}
~~~

~~~json
{"record_key":"equipment:abc","amount":"0","status":"present","authority":"provisional","representation":"extended_total","scope":"purchased_equipment","native_basis":{"currency":"USD","price_year":2024},"source_ref":"quote:17"}
~~~

~~~json
{"periods":[{"project_year":2,"calendar_year":2032,"phase":"startup"},{"project_year":3,"calendar_year":2033,"phase":"operation","operating_year":1}]}
~~~

## Engineer 1 decision record

All eight decisions are pending. The examples are review fixtures and do not establish economic policy.

| Decision | Current behavior and recommended contract | Alternative and numerical consequence | Exact approval and acceptance fixture |
|---|---|---|---|
| A. Precision | Equipment uses float in places. OPEX, Revenue and Finance use Decimal. Pass decimal strings at new boundaries and preserve full available precision. | Round each line versus round the final ledger/display. Per-line rounding can change accumulated cash and NPV. | Approve the float-to-decimal bridge, rounding mode and stage. Compare independent sum of fractional cents and final reporting reconciliation. |
| B. Currency and escalation | Equipment translation retains native and target basis. Finance parses CAPEX period and uses one year. Keep native and comparison amounts, date/index basis and conversion evidence. | Reject unmatched basis versus translate using a reviewed policy. Guessing an index or rate changes CAPEX and finance basis. | Approve FX date and order relative to escalation, index series applicability, and historical date-to-year handling. Test mixed currencies/years, incompatible indices and untranslatable lines. |
| C. Capital scope | Purchase, installed and source-defined unit capital have different factor eligibility. Carry component and scope explicitly. | Group all equipment totals versus partition by approved scope and bridge once. Mixing creates duplicated installation costs. | Approve the scope vocabulary, component inclusion matrix and applicable factor bases. Test purchase + installed + unit capital and reconcile each inclusion once. |
| D. Missing and approval | Existing nullable totals, exclusions and provisional flags vary by engine. Represent availability separately from approval. | Use a single status field or zero-fill missing lines. Zero filling hides missing coverage and can change feasibility metrics. | Approve when provisional values enter previews or totals, and how closure/working-capital true zero differs from unavailable or excluded. Test explicit zero, positive closure, missing closure, excluded and provisional cases. |
| E. Quantity extension | Some quotations are per unit of length/area/etc.; components may already be extended. Separate unit price, denominator, quantity and extended amount. | Extend at each consumer versus once at the approved boundary. Re-extension multiplies costs incorrectly. | Approve conversion and extension ownership and acceptable denominator mappings. Test two units, zero quantity, mismatched units and no second extension. |
| F. Timeline | Existing stage/view conventions derive operating indices from construction and report dates independently. Carry explicit project, calendar and operating coordinates. | Keep offset-only timeline versus explicit rows. Offset-only can misplace startup or closure where timing differs. | Approve index origin, first operation, startup/commissioning and final reporting period. Test zero, one and two construction years and a distinct startup period. |
| G. Stage/scenario coverage | Cashflow can repeat provisional last terms; Monte Carlo leaves shorter schedules incomplete. Track approved years and each ramp/realization owner. | Refuse extension, expose pending, or allow a separately reviewed provisional extension. Repeating fixed fees and double applying ramp change income and NPV. | Approve shorter schedule handling and whether each fixed or variable line receives a factor. Reconcile stage, scenario and export on a fixed fee, variable sales, ramp, and both aligned and short horizons. |
| H. Legacy | Store reopens saved JSON and results. Keep original snapshots and project only documented metadata when evidence is sufficient. | Backfill inferred fields or retain explicit missing metadata. Backfill could change receipts and historical meaning. | Approve which legacy basis facts are safe to project, then compare snapshot bytes, quantities and all four economics totals before and after reopen. |

## Remaining work

Production adapters, accepted scope vocabulary, policy enforcement at aggregation, schedule extension and a combined independent CAPEX/OPEX/Revenue/Finance oracle remain open. The standalone timeline validator does not encode construction spending weights or enforce contractual approval. The existing B07 reopen and Monte Carlo regressions are compatibility checks, and do not resolve the B08 stage/scenario semantics above. No B09 changes.



## Test evidence

Windows Python 3.12 using the Phase 0 test environment, a temporary SQLite database, and AI and cloud disabled.

~~~powershell
python -X utf8 -m pytest backend/tests -q -ra --tb=short -p no:cacheprovider
python -X utf8 -m pytest backend/tests/test_monetary_timeline_contracts.py backend/tests/test_cashflow_schedule.py backend/tests/test_equipment_resolution.py::test_manual_price_monte_carlo_reconciles_same_canonical_run backend/tests/test_equipment_resolution.py::test_user_price_propagates_equipment_capex_and_finance backend/tests/test_engineering_identity.py::test_legacy_api_reopen_projects_identity_without_rewriting_history -q -ra --tb=short -p no:cacheprovider
~~~

- Full backend: **1,731 passed, 0 failed, 9 skipped, 367 subtests passed, 1 warning** in 697.47 seconds. Eight skips require private fixtures and one requires the optional pinned OpenPyTEA reference.
- Focused backend: **22 passed, 0 failed, 0 skipped, 1 warning** in 48.14 seconds.
- Both backend runs emitted the existing Starlette TestClient/httpx deprecation warning. The frontend was outside the changed surface.

Existing price-to-CAPEX and finance, legacy reopen, and sampled manual-price scenario regressions pass. The new fixtures validate metadata only. A shared independent four-stage numerical oracle and aligned stage/scenario coverage remain pending Engineer 1 review.
