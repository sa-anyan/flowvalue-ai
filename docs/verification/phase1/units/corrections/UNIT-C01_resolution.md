# UNIT-C01 — Shared Boolean safety at native engineering boundaries

Date: **11 November 2026**. Parent: FV-P1-UNIT-001. **UNIT-C01 decision: PASS**, supported by the completed evidence below. All 12 native numerical quantity/unit/type contracts receive **bounded PASS** for the tested real scalar representations and explicitly named units. Wider unit-system/model-basis acceptance remains **PARTIAL**. **G1 is not passed.** No UNIT-EXT or Phase 3 work is implemented.

## Root cause and affected boundaries

The original 13 assertions were reproduced before production changes: twelve NumPy-Boolean sizing assumptions and one NumPy-Boolean pump volume-flow observation were accepted instead of rejected. Exact parameter names, types, inputs, units and unsafe outputs are retained in `UNIT-C01_evidence/before_inputs_and_outputs.json`.

Python bool is a subclass of int, while NumPy bool_ is a distinct scalar with a Boolean dtype. The old shared `common.positive` rejected Python bool but then called float() on other inputs, admitting NumPy bool_ as0/1. `adapter.observation` similarly erased a non-heat NumPy Boolean's type before native sizing saw it. SIZE-C02's guard protected heat-duty values, but not every other assumption or observation.

Examples before correction:

- Exchanger duty100 kW, U=NumPy True, LMTD20 K and F1 produced5000 m².
- Pump efficiency NumPy True was treated as1.
- NumPy True gas residence was treated as1 second.
- NumPy False product moisture became0, a valid numerical moisture fraction derived from an invalid Boolean input.
- NumPy True pump volume flow became1 m³/h and yielded a finite flow-pressure coordinate.

These are data-type admission failures, not faulty sizing equations. Filtering values0/1 would destroy legitimate measurements and would not be an acceptable correction.

## Exact production correction

Only three production files changed:

1. **`backend/engineering_sizing/common.py`** adds one shared `reject_boolean(value, name)` guard. It rejects Python bool and Boolean dtypes exposing `dtype.kind == "b"`, including NumPy bool_ and the tested compatible Boolean-scalar protocol, without importing NumPy. `positive` calls it before float coercion. The existing finite/positive/nonnegative rules and function signature remain unchanged.
2. **`backend/engineering_sizing/heat_exchangers.py`** keeps the existing `validate_heat_duty_type` wrapper for compatibility, but delegates to the shared guard before abs(). There is no separate Boolean-detection implementation left in this module. Signed numerical duty still uses its magnitude.
3. **`backend/engineering_sizing/adapter.py`** calls the shared guard for every selected numerical observation before float(), not just heat duty. It also guards provided ranged-assumption low/high endpoints before comparison or calculation. Selected parameter values are protected by the existing call to the now-corrected shared positive validator.

Every numeric input and consumed assumption in the 12 registered methods reaches the common guard; thermal magnitudes additionally use the wrapper before abs. No equipment equation, coefficient, unit or output structure is changed. Source lineage identifiers are preserved. The shared converter remains untouched and retains its stricter finite int/float-type API. No mandatory numerical dependency or new alias is added.

The correction-specific diff against the exact pre-ticket files is `UNIT-C01_evidence/production_change.patch`; it does not attribute older C01/C02/C03 edits to this ticket. A Python `-S` probe confirms import and signed-area calculation without optional site packages.

## Before-and-after assertion evidence

The initial pre-change execution reported **13 failed in 0.99 seconds**, with all exact unsafe inputs/outputs saved. After correction, the same assertions pass unchanged: **13 passed in 1.04 seconds**. The original `backend/tests/test_unit_acceptance.py` file is byte-identical to the ticket-start snapshot.

Evidence handling note: the first after-check reused a local preliminary before-log filename. Its files were correctly renamed `after_original_assertions.*`. The exact pre-change source was then replayed in a disposable import root, with each of the three baseline source hashes verified against the ticket-start snapshot: **13 failed in 0.91 seconds**. Raw replay logs/XML, baseline source copies and replay metadata are retained. Live production was never rolled back. The original UNIT-001 report and its original failing XML/logs remain unchanged. No after-result is represented as a before-result.

## Valid numerical behaviour and expanded regression tests

Added **455** tests in `backend/tests/test_native_boolean_safety.py`:

- Python True/False, NumPy True/False and a compatible Boolean-scalar test object are rejected before float/abs. The test object raises if coerced, so a passing test proves pre-coercion rejection.
- Primary input coverage across all 12 methods and every consumed parameter position in the independent references.
- Python int/float, Decimal, Fraction, NumPy int64/float32/float64 remain supported at native boundaries. Expected results use the static independent references and the value actually represented, accounting for float32 quantisation rather than changing a source value silently.
- Pressure, temperature, mass/molar/volume flow, density, power, enthalpy flow, thermal duty, area and equipment-capacity observations reject Booleans before conversion. Valid observations preserve value, unit, evidence ID and the source record.
- Boolean interval endpoints are rejected; valid zero and one, signed duties, zero product moisture and zero sensible enthalpy retain existing behaviour.

A separate genuine **1 W** measurement normalises to0.001 kW and gives the independent **0.0001 m²** area for U500 W/(m² K), LMTD20 K, F1. Boolean True is rejected instead. This receipt is retained in `one_watt_numeric_probe.json`.

Method-specific numerical tolerances and expected values are unchanged. This verifies a bounded set of supported real numerical representations, not arbitrary Python objects, arrays, complex inputs, every source file or every equipment design.

## Executed tests

| Suite | Exact outcome |
| --- | --- |
| Original 13 before correction |13 failed (initial0.99 s; hash-verified baseline replay0.91 s) |
| Original 13 unchanged after correction |**13 passed**,1.04 s |
| New shared/native Boolean and numeric-type tests |**455 passed** |
| Original 12-method independent sizing suite |**304 passed** |
| Combined targeted run, including C01/C02/C03 and R-01 |**1335 passed**,0 failed,0 skipped;16.47 s |
| Complete canonical backend |**3056 passed,5 failed,3 skipped**,367 passing subtests;1 warning;304.90 s |

All five full-suite failures remain in `test_sizing_cross_file.py`:two XLS Boolean preservation assertions and three L/s normalisation assertions. They are unchanged upstream integration findings, not native guard failures. The three skips remain the private Charlie workbook, private Charlie snapshot and unavailable optional installed OpenPyTEA reference. They are not successes. The warning is the existing Starlette/httpx test-client deprecation. The full suite transparently exits nonzero for those five cases; they are not skipped or xfailed.

Targeted file selection, raw output and JUnit XML are retained. The targeted run includes the original thirteen assertions,455 new shared/type-boundary tests, the original304 native cases, C01/C02/C03 regressions, the shared converter/bridges, source-observation checks and R-01 horizon tests. Suites overlap; do not add their counts as unique tests.

The full canonical selection includes existing tracked tests (including Nottingham smoke tests outside backend/tests) plus the legitimate prior untracked verification suites and new tests. Pre-existing duplicate files were preserved and not collected as canonical tests. Real AI/cloud calls and external sockets were disabled and assessment storage was isolated. No existing assertion was weakened, skipped or xfailed.

## Updated acceptance records and historical preservation

Updated the current `unit_conversion_acceptance_register.csv` TYPE-* rows to PASS as **validation rejections**, not as numerical conversion pathways. Before-register snapshots and actual unsafe outputs are retained. The173 previous PASS records remain unchanged in meaning; thirteen corrected rejection records bring the current primary register to **186 PASS,2 PARTIAL,13 BLOCKED**. Those counts include validation records and must not be reported as186 supported conversions.

Updated all 12 `sizing_native_unit_contract_acceptance.csv` rows to **PASS for the bounded native quantity/unit/type contract**. The24 numeric source-to-native paths,143 numerically exercised canonical units,148 verified conversion/derivation paths and75 noncanonical spellings plus one equivalent canonical unit retain their original scope. No additional unit or alias is accepted by this correction.

The Boolean data-type risk entry in `unit_alias_and_semantics_register.csv` is updated, and the original risk ticket receives a dated resolution addendum without rewriting its historical OPEN finding. The original FV-P1-UNIT-001 report remains unchanged as a historical acceptance decision. Its evidence-generation scripts describe that earlier state; use this correction's logs and register update for the current state.

## Remaining limitations and decisions

**UNIT-C01: PASS.** All original assertions and expanded native/type regressions pass, legitimate numerical types and signed/zero semantics are retained, and shared validation is dependency-free. **Bounded native input/type acceptance:12/12 PASS** within the documented method/unit/representation scope.

**Updated wider UNIT-001 decision: PARTIAL**, with a now-passing bounded native quantity/unit/type subset. The five UNIT-EXT conversion families and specific-gravity derivation are unchanged and unsupported; other missing-context cases remain blocked. Published index observation authenticity, FX source/basis acceptance and full model-native physical/rating semantics remain partial. This does not accept all 191 unit definitions,495 aliases, every native parameter-unit conversion or arbitrary file inputs.

Engineer 2's **SIZE-XF01** (two XLS Boolean-type-loss cases) and **SIZE-XF02** (three L/s normalisation cases) remain open and separate. A native guard cannot reconstruct a Boolean type already erased to an ordinary integer by a reader; genuine numeric1 must stay valid. The current parser was not modified. No universal upload compatibility is claimed.

G1 still requires the outstanding scoped integration, unit/context/model-basis, source/applicability and independent-review evidence under the official roadmap. No Phase 3 or UNIT-EXT implementation is started. No costing/economic/financial calculation, approved project record, historical report or duplicate file was modified or deleted. No push, merge or deployment was performed. Stop after UNIT-C01.
