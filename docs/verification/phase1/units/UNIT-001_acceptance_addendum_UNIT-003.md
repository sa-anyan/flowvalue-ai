# UNIT-001 acceptance addendum — UNIT-003, 11 November 2026

**Current overall UNIT-001 decision: PARTIAL. G1 remains OPEN.**

This addendum supersedes only the current unsupported-family decisions for
velocity, heat-transfer coefficient and standalone time. It does not rewrite
UNIT-001, UNIT-C01 or UNIT-002 historical reports, registers, fixtures or logs.

| Previous gap | UNIT-003 decision | Acceptance boundary |
|---|---|---|
| UNIT-EXT01 velocity | PASS | Four finite velocity units and hydraulic-loading alias; typed parameter normalization before native filter sizing |
| UNIT-EXT04 U | PASS | SI/kW and explicitly based IT/thermochemical Btu coefficients; interval temperature; typed parameter normalization before native thermal area sizing |
| UNIT-EXT05 time | PASS | s/min/h/day, native cycle/EBCT/hold-up/dryer parameter normalization; separately typed V/Q helper requires supplied working volume and actual flow |
| UNIT-EXT02 dynamic viscosity | Unsupported, OPTIONAL | No new active requirement or implementation |
| UNIT-EXT03 kinematic viscosity | Unsupported, OPTIONAL | No new active requirement or implementation |
| UNIT-EXT06 SG | Unsupported, OPTIONAL | Explicit density bridge exists; SG still requires a reference density/state |

Newly supported units are not justification to remove missing-physics guards.
Mass/volume still needs density; gauge/absolute still needs the explicit
atmospheric reference; gas-state changes still need supplied positive absolute
T/P/Z and a qualified common-gas basis. Energy->average power requires supplied
energy and duration. No operating time, density or reference state is invented.

All 12 native numerical/type contracts and SIZE-C01/C02/C03 and UNIT-C01
regressions remain passing. Original 191 definitions and all 562 alias bindings
were rechecked unchanged. Twelve justified canonical definitions were added;
UNIT-002's historic 191-unit audit and 4,689-test result are preserved.

The six-case current capability test in `backend/tests/test_unit_acceptance.py`
retains all six cases. Its three now-obsolete active-family absence expectations
are replaced by independent expected-factor and reverse-conversion assertions;
the optional viscosity/SG rejection assertions are unchanged. No tests were
skipped, xfailed or given weaker tolerances. The exact prior test file and update
patch are in UNIT-003/evidence, and the original historical JUnit evidence is
unchanged. All 296 current UNIT-001 tests pass.

The 11 costing source-coordinate contracts remain BLOCKED for the separately
recorded source/coordinate reasons; boiler_hp remains PARTIAL with no W bridge.
Source-specific suitability/rating conventions, opaque gas-reference validation,
current index/FX provenance, Engineer-2 ingestion issues and independent review
are not closed by these conversions. No Phase 3 implementation or release claim.

See [UNIT-003 report](UNIT-003/UNIT-003_final_report.md), the conversion references
and source-coordinate reconciliation for current bounded acceptance.
