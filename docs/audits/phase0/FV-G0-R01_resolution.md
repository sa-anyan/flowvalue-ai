# FV-G0-R01 resolution

Date2026-11-10. **R-01 CLOSED within the tested scope. G0 is not PASS.** This implements only the supplied corrective ticket. The existing completeness assertion and unsupported-year guard remain intact; no costing equations, coefficients, six-category Revenue schema, approved assessments or historical results were modified.

## Original root cause and reproduction

At `74f364d`, `test_manual_price_monte_carlo_reconciles_same_canonical_run` creates Settings without operating_years. The inherited approved fixture has3 years and commercial rows[1,2,3]. Settings has an integer default20, and `scenarios.prepare` unconditionally used that value, changing copied financial.operating_years to20. The commercial connector correctly refused17 unsupported contract years. Revenue-dependent OPEX then lacked annual_revenue and finance stayed pending, although equipment pricing worked.

Before editing production code in this ticket, the exact original test was rerun: **1 failed**, expected complete, actual partial. See `evidence/FV-G0-R01/before.log`. A Pydantic Settings object already records which fields the caller supplied; the old adapter ignored that metadata. Ordinary JSON containing20 cannot reveal whether an older producer inserted a default; explicit serialized numbers must remain authoritative rather than guessed away.

## Implemented calculation contract

The ticket explicitly authorises the following behaviour; it is not an assertion of independent industrial validation or a human peer-review signature.

- Omitted simulation horizon inherits the current project operating horizon when present and a valid integer1–50. Consequential Revenue inputs still require existing source-bound approval; resolving a horizon does not approve a sale or missing price.
- Explicit horizon, including20, wins. A3-year commercial schedule is not extended, renewed, duplicated, or replaced with zeros; missing years are listed and complete finance remains unavailable.
- Explicitly authorised zero rates/quantities are numerical zeros; absent rows/terms remain unresolved. Changed commercial inputs invalidate prior approval.
- Commercial/avoided-cost rows are validated as unique ascending positive operating-year indices before scenario selection; calendar dates are not silently reinterpreted as operating indices.
- Only an explicit reduction below the project's horizon selects a shorter annual subset. Excluded years are recorded in scenario horizon evidence; original input remains unchanged. An omitted/same-length horizon does not silently hide extra rows.
- Revenue, dependent OPEX and financial ledger consume the same copied financial.operating_years. Simulation and job outputs expose the effective integer. No separate economics engine or new formulas were introduced.

## Files and functions changed

| File/function | Change |
|---|---|
| `backend/scenarios_and_uncertainty/monte_carlo/scenarios.py` — resolve_horizon/resolved_settings | Use supplied-field metadata to distinguish omission from an explicit integer; validate inherited horizon; freeze effective settings without changing the Settings wire schema/default |
| Same file — _annual_rows/prepare | Preserve baseline, apply one selected horizon, validate annual identities/order, disclose only explicit reductions; never invent missing commercial years |
| `backend/scenarios_and_uncertainty/monte_carlo/engine.py` — simulate | Resolve once before sampling/evaluation; report effective horizon and resolution provenance |
| `backend/scenarios_and_uncertainty/monte_carlo/service.py` — start/work | Freeze resolved integer into the new job before serialization; preserve original selection provenance through job execution; old jobs/snapshots not migrated |
| `backend/revenue/connectors/commercial.py` — commercial_inputs | Retain existing comparison/rejection and add missing/supplied operating-year detail to its error message; billing arithmetic unchanged |
| `backend/tests/test_monte_carlo_horizon.py` | New synthetic horizon/authority/schedule/financial reference and version tests |
| Current requirements/risk register and R-01 acceptance addendum | Close only evidence-supported R-01 items; retain historical records and other G0 blockers |

`Settings.operating_years` remains the existing required-on-discovered-output integer contract with its legacy default20. API JSON that **omits** the key is distinguishable through model_fields_set. Existing saved JSON that **contains20** remains explicit20. New jobs created from an omitted horizon first freeze the actual project value3, so serialization/reloading cannot turn omission into a default20. The original request selection is stored in job/audit horizon_resolution. Frozen-settings preparation may subsequently label the effective integer explicit; original request provenance remains in the top-level audit/job record.

Older internal callers using a plain namespace already supply an operating_years attribute; those values remain explicit. No existing namespace authority test was modified. When no project horizon exists at all, the existing20-year fallback is retained and labelled legacy_default_no_project_horizon, not invented approval. Invalid/ambiguous supplied project horizons are rejected instead of guessed. Authorisation and downstream missing-input guards remain necessary.

## Before and after

| Input | Before | After |
|---|---|---|
| Approved3-year project, caller omits horizon | Copied project becomes20; original completeness assertion fails | Inherits3; existing original assertion passes |
| Approved3-year project, explicit3 |3-year study | Same3-year study |
|3 supported contract years, explicit20 | Missing commercial coverage, partial | Still partial; missing operating years4–20 explicitly reported, no complete NPV |
| Missing year2 | Unresolved/stale approval | Still unresolved; with current synthetic approval the missing-year guard identifies2; without reapproval authority blocks calculation |
| Duplicate/out-of-order/calendar year rows | Existing downstream failures; positional slicing could obscure rows | Rejected before any explicit shorter subset is chosen |
| Explicit reduction3→2 | Positional truncation | Select by operating-year identity, validate first, record excluded year3; original unchanged |
| Old saved settings contain20 |20 | Still20; no retrospective reinterpretation |

## Independent tests and numerical evidence

All inputs are synthetic, with no production credentials, live AI, paid services or customer assessments. Expected numerical values are not generated by the tested production calculator.

| Ticket case | Test/evidence |
|---|---|
|1. Unspecified horizon | test_three_authorised_years_default_or_explicit: omitted Settings inherits3 |
|2. Explicit3 | Same parameterised test, explicit3 completes |
|3. Explicit20 with3 contract years | test_explicit_twenty_does_not_invent_seventeen_contract_years:20 retained, rows[1,2,3] unchanged, missing4–20, NPV unavailable |
|4. Missing year | test_missing_year_stays_unresolved_not_zero plus stale-approval test |
|5. Duplicate year | parameterised annual-identity rejection |
|6. Ordering/date basis | out-of-order and calendar-date rejection; no conversion of2027 into an operating-year claim |
|7. Approved zero-revenue year | Explicit zero fee in year2; complete three-year reference with zero revenue/admin OPEX that year |
|8. Revenue-dependent OPEX | Independently specified10% administration allowance matches each year's actual fee, including zero |
|9. Financial/Monte Carlo reconciliation | Independent cash-flow/NPV reference and separate1000-run deterministic representative-run integration |
|10. Existing saved-study behaviour | Inherited value frozen/reloaded as3, named-version reopen preserves original plan, legacy serialized20 remains explicit |
|Additional safeguards | Implicit horizon does not hide extra rows; invalid inherited horizon rejected; original input unchanged; existing Revenue authority suite passes |

The independent three-year reference supplies **capital100 and WC10 as upstream inputs**,100 billable units/year at fee2/unit, administration10%, tax0, construction0, terminal WC recovery10 and discount10%. Other expense categories are explicitly zero scenario assumptions, not missing data silently defaulted to zero. It is a numerical integration reference, not a Garrett cost/source-validation benchmark.

- Constant fee: revenue[200,200,200], cash OPEX[20,20,20], cash flows **[-110,180,180,190]**. Independent discounted-sum NPV = **345.1465063861758076634109691960931630353**.
- Explicit zero fee year2: revenue[200,0,200], OPEX[20,0,20], cash flows **[-110,180,0,190]**. Independent NPV = **196.3861758076634109691960931630353117956**.

The tests assert the actual ledger cash series and metric against those independent expectations at Decimal tolerance1e-30. The separate Monte Carlo integration compares its full representative result with the canonical deterministic ledger and an independently summed discounted ledger at relative1e-12 for the float reporting boundary. This is not a claim that every underlying CAPEX/tax/cost model has been independently verified. Reference definitions are saved in `independent_reference_values.json`.

## Actual test record

| Run | Result |
|---|---|
| Exact original failing test before correction |1 failed, expected complete versus partial |
| First expanded targeted run |141 passed,2 failed,2 skipped;6 subtests passed. One new missing-year fixture still carried stale approval; one older namespace caller needed compatibility handling. Preserved as targeted_initial.log; existing tests were not weakened |
| Exact unchanged original assertion after correction |1 passed; original_assertion_after.log |
| Final targeted suite |144 passed, 2 skipped, 1 warning, 6 subtests passed in 19.05s |
| Complete canonical backend suite, baseline cache policy |1738 passed, 3 skipped, 1 warning, 367 subtests passed in 157.79s (0:02:37) |

An earlier green backend run omitted one local Nottingham smoke module (3 cases); its1735-pass result is retained as full_initial_scope.log. The corrected full-discovery run includes it. The complete command uses every tracked backend test file plus the two Phase0 version tests and the new R-01 tests, deliberately excluding127 untracked duplicate-suffix files. No duplicates were deleted/reset. The fresh minimal Python3.12 test environment uses baseline cache policy (no global cache-off override), synthetic test-owned stores and blocked external Python sockets. Three skips, if present in the logged full result, are the private Charlie workbook/snapshot and optional installed OpenPyTEA3.2.1 reference; skips are not passes. Other pinned upstream/functional tests continue to run. The Starlette/httpx deprecation warning is recorded, not fixed in this ticket.

No frontend or equipment-costing module changed. The pre-existing frontend-CI edit and draft backend CI remain outside this ticket. Test commands, exits and exact paths are in the JSON evidence manifests; no cloud run or hosted CI success is claimed.

## Ownership, limitations and closure

**Engineer1:** the ticket-defined horizon/billing/operating-year contract is implemented and the independent specified cash/fee/OPEX/NPV reference passes. Method/source validation beyond these reference cases remains future work, not implied by this closure.

**Engineer2:** supplied-field selection and copied-plan preparation now preserve intent; service persistence freezes the resolved horizon and retains provenance. Review the scoped patch in the normal code-review process. Legacy stored20 is intentionally not migrated. Historical production/cloud assessments were not modified or recovered for this ticket.

**R-01 can be closed** for the specified and regression-tested contract: original complete assertion passes, explicit unsupported years remain unresolved, approved zero is distinct, all executed backend tests pass, and baseline data remains unchanged.

**G0 remains not passed.** The separate R-17/FV-G0-M04 draft-CI cache conflict, formal reference-project agreement, controlled publication/owner acceptance and historical/cloud recovery evidence remain open. This ticket does not implement or close those items. See `g0_acceptance_matrix_R01_addendum.md`; original gate/reconciliation reports remain historical. No next ticket, commit, push or deployment was started.
