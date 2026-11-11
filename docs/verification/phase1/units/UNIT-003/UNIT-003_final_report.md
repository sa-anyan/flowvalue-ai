# FV-P1-UNIT-003 — Active workflow conversions and costing interfaces

**Date:** 11 November 2026  
**Decision:** Required active conversions implemented and independently verified;
source-interface investigation complete with explicit unresolved dispositions.
**Wider UNIT-001 remains PARTIAL. G1 remains OPEN.**

## Implemented and connected

The existing finite converter now supports three active families, with **12
additional canonical definitions**:

- Velocity: m/s, m/h, ft/s, ft/min. Hydraulic loading m3/m2/h is a velocity alias,
  not a volumetric flow.
- Heat-transfer coefficient: W/m2/K, kW/m2/K and explicit IT/thermochemical
  Btu/(h*ft2*delta_degF). Fahrenheit is an interval in this coefficient; no
  absolute-temperature offset is applied. Bare Btu requires an explicit basis.
- Standalone time: seconds, minutes, hours and days, with bounded word spellings.

Only these justified families were added. The catalogue now has **203 units,
517 symbol/canonical aliases and 77 word aliases**. The original 191 definitions
and 495+67 bindings remain unchanged; current tests check their exact factors,
offsets, pressure labels, quantities and intended alias targets against retained
UNIT-002 evidence. This is not a repeated universal catalogue certification.

`unit_conversion/sizing_parameters.py` is the shared normalization boundary.
It handles typed value/unit records for hydraulic loading, U, cycle time, EBCT,
hold-up residence time and dryer gas residence time. It converts supplied range
endpoints with the same factor as the selected value, retaining source-cell
references and conversion traces. It never supplies a missing assumption.
The engineering sizing adapter and existing equipment bridge service call it
before the native calculators. Original assumptions stay unchanged; normalized
working values and `parameter_unit_conversions` are separate. Existing bare
native numbers and legitimate native Decimal/Fraction/NumPy representations
retain their prior contract. Alternative-unit records use the shared converter's
finite Python-number input contract.

The twelve established native sizing equations remain unchanged and
dependency-free. Neither registries/costing equations nor cost coefficients were
changed. An integration check runs alternative-unit loading through native area
sizing, then through an actual existing OpenPyTEA model. Its result agrees with
supplying the independently calculated native area directly; this tests the
handoff, not the commercial accuracy of that cost correlation.

Two explicit source-linked helpers were added in `relationships.py`:

- `average_power(energy, duration)`: E/time, requiring a positive duration; signed
  energy gives signed average power. It does not establish peak or driver rating.
- `residence_time(working_volume, actual_volume_flow)`: V/Q, requiring positive
  actual flow. No volume, residence time, phase or working fraction is inferred.

The result is a typed Measurement with original quantities, units, source
references, equation and component conversions retained. These helpers are
available through the shared backend package; no new UI, API endpoint or LLM
recipe was installed. No parser changes were made. Backend callers must supply
typed records for alternate parameter units; arbitrary unit entry in the UI is
not claimed.

## Independent verification

`active_conversion_requirements.csv` maps each family to its active parameter,
physical dimension, native units and scope. `conversion_independent_verification.csv`
contains **38 reference records**: 36 numeric unit cases across the 12 additions
and two explicit physical derivations. The tests also cover reverse/round-trip,
zero/sign behavior, non-finite values, Boolean/type rejection, invalid/ambiguous
units, wrong dimensions, missing assumptions, invalid gas reference states,
range propagation, source lineage and unchanged native types.

Expected values come from independent Decimal arithmetic, not production
conversion outputs. Exact foot 0.3048 m, 60 s/min, 3600 s/h, 86400 s/day and the
Fahrenheit interval 5/9 K establish velocity/time/U factors. The IT coefficient
is independently 1055.05585262/(3600*0.3048²*(5/9)) =
5.678263341113488 W/(m² K). The thermochemical coefficient is checked at the
published Btu factor's precision, with explicitly bounded reference tolerance;
extra production trailing digits are not authenticated. Other new factor cases
use 2e-12 relative tolerance and small absolute floating-point floors. Existing
assertion tolerances were not relaxed.

Reference: [NIST SP811 B.8](https://www.nist.gov/pml/special-publication-811/nist-guide-si-appendix-b-conversion-factors/nist-guide-si-appendix-b8)
and [B.9](https://www.nist.gov/pml/special-publication-811/nist-guide-si-appendix-b-conversion-factors/nist-guide-si-appendix-b9),
checked 11 November 2026. No third-party code or new dependency was incorporated.

The affected suites passed in scoped batches:

| Batch | Passing tests | Scope |
|---|---:|---|
| Targeted | 2,932 | New conversions; shared bridges; thermal basis; native 12-method references; UNIT-C01 and SIZE-C01/C02/C03; OpenPyTEA; R-01 |
| UNIT-001 current capability regression | 296 | Original independent conversion/derivation and native-input tests, with three capability expectations strengthened |
| Final handoff | 1,059 | Final new unit/helper tests plus Garrett, total equipment and Nottingham smoke checks |
| Added alias-only checks | 32 | Every new alias/word binding against explicit expected meaning |

**3,293 distinct test IDs passed** across these overlapping batches (4,319 test
executions); do not add overlapping suites as unique coverage. The final new
module contains 1,065 cases. Raw logs, JUnit XML, exact selections and duplicate
reconciliation are in `evidence/`. AI/cloud and outbound sockets were disabled,
and assessment storage isolated. No complete backend rerun was performed.

The current six-family UNIT-001 test keeps all six cases. The three newly
implemented families now require independent numeric and reverse-conversion
results instead of obsolete “unsupported” outcomes. The three optional-family
rejection assertions remain unchanged. The exact prior test source and the
update patch are retained; historical fixtures/reports/JUnit evidence were not
rewritten. No assertion was skipped or xfailed.

Initial development checks exposed one incorrect field name in the new costing
test and one existing error-message compatibility expectation; both were
corrected before the passing runs. The latter preserves the existing “unit
mismatch” wording while retaining detailed conversion issues. No engineering
coefficient or physical equation was adjusted to make a test pass.

## Context-dependent decisions

The 14 original relationships now have **9 PASS, 4 PARTIAL, 1 BLOCKED** bounded
dispositions in `context_conversion_acceptance.csv`.

Mass-to-liquid-volume flow continues to require an explicitly supplied qualified
density; no water-density default is inserted. Actual/reference gas conversion
continues to require positive absolute T/P/Z and qualified unchanged gas basis.
Gauge/absolute conversion retains pressure roles and needs the explicit local
atmosphere; a bare bar symbol cannot establish an absolute role. Energy->power
and inverse residence-time derivation are now explicit helpers with supplied
durations or V/Q, rather than guessed multipliers.

Remaining partial context cases: opaque standard-gas reference descriptors,
historical cost escalation provenance, dated currency-rate provenance, and
source-specific boiler thermal rating. Specific gravity remains unsupported
and optional. Signed velocity is preserved by the converter, while hydraulic
loading for actual filter sizing must remain positive under the native method.
Zero time/U is valid as a unit value but cannot become a valid positive sizing
assumption. No changes were made to currency or historical-price services.

## Eleven source-coordinate dispositions

**All 11 remain BLOCKED for automatic source-compatible costing.** This is a
source-basis finding, not an absence of general arithmetic or basic unit factors.
`costing_source_coordinate_reconciliation.csv` records each exact ID, original
publication, source coordinate, inputs, native-output gap, physical dimension,
conditional relationship, assumptions, evidence and remaining blocker.

- **G297-125 / G297-126:** the actual Garrett page 297 distinguishes scaled
  chemical-injection flow and individual other-pump flow/power conventions.
  Their grouped imported coordinate/readings cannot be repaired by one Q×ΔP
  conversion. Separate curve and axis reconciliation is required.
- **G306-153 / G306-154:** actual page 306 divides equivalent-air mass flow by
  vacuum pressure; the imported chart interpretation conflicts with that basis.
  Division and pressure scaling are mathematically established, but equivalent
  air load and source pressure convention must be confirmed and the affected
  chart coordinate data reconciled. No refit was performed.
- **OpenPyTEA screw geometry:** candidate mixed-unit length×diameter is
  dimensionally expressible; original Perry Table 9-50 geometry definitions
  were not recovered.
- **OpenPyTEA multistage, single-stage 100-psig steam and two-stage Perry ejectors;
  Seider one-stage jet:** mass-flow/suction-pressure components are convertible,
  but original table gas/load/reference and service conventions remain
  unverified. A manual native-coordinate route is not source validation.
- **OpenPyTEA RDC:** height×diameter^1.5 requires defined actual geometry;
  upstream label alone is insufficient to establish the original source basis.
- **OpenPyTEA distillation annual feed:** annual operating time, normalization,
  bounds and exponent placement require original-source confirmation; applying
  an exponent twice or assuming 8760 hours is not an acceptable conversion.

Pinned OpenPyTEA metadata/CSV, source commit and references were inspected.
Original Perry/Seider tables were not present locally; attempted official
publisher access returned 403. An upstream MIT licence does not independently
validate its underlying textbook transcription. No new third-party code was
copied. None of these records changes Garrett, OpenPyTEA or Nottingham equations,
coefficients or model-enable decisions. The scope of this task does not authorize
repairing/rebuilding cost curves to clear those source discrepancies.

## Boiler horsepower

**boiler_hp stays PARTIAL.** The actual Garrett small-boiler axis/footnote was
visually inspected on printed page 262 / PDF page 12. The scan does not establish
a sufficiently unambiguous thermal time/rating convention. Identity is sufficient
for an explicitly supplied source-native G262-018 chart coordinate, but not for
thermal watts, mechanical hp or fuel consumption. See `boiler_hp_source_review.md`
for the exact missing evidence. NIST's standardized thermal boiler hp was not
silently substituted.

## Scope, remaining blockers and acceptance

Only the shared conversion package, sizing adapter boundary, relevant tests,
documentation and new evidence were written. The native equation modules,
costing source registries/data/equations, CAPEX/OPEX/Revenue, Engineer-2
parser/ingestion/API/frontend and approved project data were left unchanged.
Pre-existing work and duplicate files were preserved; `scope_integrity.json`
compares existing files against the pre-task hashes. The historic UNIT-002
4,689-test evidence is unchanged. No push, merge or deployment occurred.

Active conversion tickets UNIT-EXT01/04/05 are accepted for their finite declared
units and native handoffs. Optional viscosity/SG families remain out of scope.
Remaining source-coordinate and boiler tickets, deeper gas-reference/context
assurance, original method/source provenance and applicability, independent
review and Engineer-2 ingestion findings still prevent a blanket G1 claim.

**Current wider UNIT-001: PARTIAL. G1: OPEN.**
The [dated UNIT-001 addendum](../UNIT-001_acceptance_addendum_UNIT-003.md) states
what this task supersedes without rewriting historical decisions. Stop after
UNIT-003; no Phase 3 implementation was started.
