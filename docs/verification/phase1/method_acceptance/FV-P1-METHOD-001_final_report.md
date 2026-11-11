# FV-P1-METHOD-001 — Engineering method verification

**Date:** 11 November 2026  
**Engineer-1 readiness: PARTIAL / NOT READY. Combined G1: FAIL / NOT PASSED.**

The remaining independently achievable reference and screening-applicability
review is complete. This is actual method-level evidence: all12 registered native
IDs, three additional active engineering estimators and two reachable legacy
hold-up branches are explicitly covered. The new investigation also establishes
exact legacy invalid-input counterexamples and the missing method-version
lineage rather than issuing an unqualified gate pass from software test counts.

## Scope and classification

`production_calculation_scope.csv` accounts for all248 historical P0 candidates,
then distinguishes17 current engineering method/branch records and three new
UNIT-003 contextual/normalization helpers. The historical candidates were function
and workflow candidates, not248 independent equipment design methods. Duplicate
register entries and shared callables are not counted twice as scientific models.

The principal native set is12 advertised IDs backed by11 callables:
ion_exchange_capacity, vaporizer_area, gas_compression, phase_change_duty,
evaporated_water, ion_exchange_ebct, vessel_hold_up, pump_duty, exchanger_area,
filter_area, gas_volume and dryer_chamber. All remain preliminary screening as
already documented; none was silently downgraded or deprecated to avoid review.
The active bridge estimators vessel_mass, vessel_productivity and mixing_power
are also genuine supplied-input engineering calculations and were not hidden in
the unit-conversion count. Legacy mass_residence and volume_residence remain
reachable separate implementations, with explicit partial acceptance.

Unit scaling, mass/density and gas-reference derivations, numerical helpers,
costing correlations, economic methods and unsupported source coordinates are
separately classified. There is no new203-unit audit or new costing-model audit.
P3/P4 scope is explicitly deferred, not reported as passing P1 verification.

## Accepted references and applicability

`sizing_method_reference_acceptance.csv` identifies equations, callables,
replacement references/derivations, original-source uncertainty, units,
coefficients, numerical evidence, tolerances and source hashes for all17 records.
All17 governing relationships have an identified independent reference or
explicit conservation/definition/geometry derivation. Historical implementation
publication origins remain UNKNOWN. Existing source-history evidence is reused;
no original textbook origin or external review signature is invented.

`method_applicability_acceptance.csv` accepts **15 conditional screening records**
and retains **2 PARTIAL legacy records** because their active validation is not
fully accepted. It separates required qualified properties/design assumptions,
mathematical admission guards, unresolved/missing basis, unsupported conditions
and professional design review. It does not invent universal k, U, residence time,
pressure ratio, loading, reserve, safety margin or manufacturer validity ranges.

For the registered methods, native equations and their supplied-input identities
are acceptable within those explicit conditions. Capacity-based ion exchange is
not a breakthrough model; EBCT is not proof of removal; thermal area is not a
mechanical/boiling-hydraulics design; evaporation assumes conserved dry solids and
wet-basis moisture; hold-up is not kinetics; pump pressure-work is not motor
rating; filter loading is not a cake/cycle model; gas volume requires a qualified
single gas state; dryer gas hold-up is not droplet/particle drying performance.
The omitted sensible term in phase_change_duty currently defaults to zero and
must be treated as a disclosed no-sensible-change assumption, not a verified
plant-wide energy balance.

### Compressor decision

The existing Z multiplier is independently corroborated as a **representative
constant-property preliminary shortcut**. NASA continues to support the ideal
branch. Newly inspected author documentation gives the matching formula and a
published example; an independent pressure-work integral supplies two synthetic
nonideal-Z numerical cases. JM Campbell's property-sensitivity discussion supports
the limited approximation. The thermodynamic derivative argument explains why
this does not establish a general real-gas isentrope.

The equation, constants and verified numerical references were unchanged.
Returned audit warnings now distinguish representative-path Z from an unjustified
inlet-only value and identify variable-property, near-critical, phase-change and
multistage/intercooled conditions requiring EOS/enthalpy-based or specialist work.
No universal safe operating envelope is asserted. The warnings survive the
existing native-to-orchestration adapter; frontend rendering was not modified.

See `evidence/critical_reference_derivations.md` for the actual derivation,
new references and scope, not just a future-work list.

### Three supplemental estimators

Independent cases verify annular-cylinder mass, target production divided by
qualified volumetric productivity and mixing power density times the same volume
basis. The mixing calculation already uses gross/design vessel volume; its prior
“working/design” audit wording was ambiguous. The text now explicitly identifies
gross/design volume and warns that a working-volume P/V cannot be substituted
without basis conversion. No empirical coefficient, sizing arithmetic or design
correlation was added or changed.

## Numerical and reproducibility evidence

- **304 native numerical assertions reused** from retained UNIT-003 evidence;
  their independent fixture and original per-method tolerances are unchanged.
- **99 focused tests passed,0 failed,0 skipped** in the final affected/new suite:
  13 method/reference/annotation checks,75 compressor stability regressions and
  11 affected conversion-bridge regressions. Only newly affected paths were run.
- **20 designated valid reference examples reproduced:**12 native nominals,
  three supplemental estimators, three additional compressor examples and two
  legacy nominal examples. These reproduce arithmetic, not process performance.
- **Two new shared legacy invalid-input checks FAIL**, documented below. They
  are not hidden in the99 passing focused tests or marked xfail.

`independent_reproducibility_matrix.csv` records actual versus independently
expected values, typed inputs/units, assumptions, source hashes, validity limits
and justified tolerances. Exact products use approximately1e-13 relative
rounding tolerance, general divisions approximately1e-12, gas volume2e-13,
compressor5e-12 and independently reconstructed pump coordinates1e-11, with the
existing absolute floors. Supplemental annular geometry uses2e-12 relative and
1e-12 absolute. These are arithmetic tolerances, not property/model uncertainty,
engineering accuracy guarantees or universal safety margins.

The reviewer can run `evidence/reproduce.py` from the repository root. It checks
the exact source/reference hashes before reproducing the20 specified cases. The
matching working tree, not just commit HEAD, is required because existing local
changes predate this task. The packet is usable reproducibility evidence; an
external reviewer run or signed engineering approval is not claimed.

The prior temporary Python environment has expired. Fresh focused tests used
available Python3.12.10, NumPy2.5.3 and pytest9.1.1, recorded in runtime.json.
Historical tests remain historical environment evidence rather than falsely
labelled new runs. No dependencies were installed and no real AI/cloud calls
were made. The focused runner blocks external sockets and isolates assessment
storage. Heat-duty, pump, Boolean, unit-family and R-01 results were reused from
UNIT-003 because their code/behaviour was not changed. No complete backend suite
was rerun. Source hashes and reused JUnit evidence are linked in evidence_reuse.json.

## Actual remaining defects

**METHOD-TRACE01: runtime engineering implementation version missing.**
The native calculation/adapter audits retain a method ID, formula, assumptions
and source references but no immutable method/software version or code hash.
The fuller bridge audit has the same engineering-version gap. Saving a hash in
this verification packet does not repair production assessment lineage. This
fails the exact G1 requirement that critical reported results trace to method
versions. `calculation_traceability_review.md` locates the missing fields and
separates native, bridge, equipment-handoff and source-snapshot responsibilities.
No Engineer-2 schema/persistence changes were made.

**METHOD-LEGACY01: active legacy hold-up validation fails.**
Two exact independent counterexamples were executed through the existing
`orchestration.sizing.derive_size` route:

| Branch | Input | Actual return | Required outcome |
|---|---|---:|---|
| volume_residence | -10m3/h;2h;working fraction0.8 | **-25m3** | Reject invalid negative sizing flow |
| mass_residence | -1000kg/h;density800kg/m3;2h;working fraction0.8 | **-3.125m3** | Reject invalid negative sizing flow |

They remain reachable and were not labelled deprecated to hide the failure.
Native vessel_hold_up rejects negative primary flow; these separate legacy
branches do not share that complete contract. The standalone boundary verifier
returns failure and retains exact inputs/results. This is an invalid sizing-stage
acceptance; it is not evidence that downstream costing accepts a negative price.
The integration route is Engineer2/shared work and was deliberately not modified.

Additional shared limits: compact source IDs require their immutable report
snapshot through save/export; user-facing warning presentation was not verified;
qualified physical context is not established by scalar validation alone. The
five previously recorded Engineer-2 XLS Boolean/L/s failures retain their evidence
and ownership, without a repeated run or an unsupported claim that they are fixed.

## Gate decision and ownership

The exact six official criteria are assessed separately in
`G1_engineer1_acceptance_matrix.md`:

- **A—Engineer1 arithmetic:** PASS for bounded native/reference results and the
  supplemental numerical definitions. No new numerical defect was found in
  those canonical equations.
- **B—Engineer1/shared closure:** replacement-reference/applicability work is
  completed for the15 principal methods. Runtime method-version binding remains
  a concrete G1 failure requiring a coordinated correction.
- **C—Engineer2/shared integration:** two new legacy validation failures,
  source-snapshot/version/warning propagation acceptance and the five earlier
  XLS/L/s findings remain open.
- **D—P3/P4:**11 blocked source-coordinate contracts, boiler_hp's source-specific
  thermal rating,594 costing-model validation, index/FX provenance and economic
  validation retain their separate decisions. They are not forced into PASS and
  do not alone block accepting a bounded P1 physical identity.

**Formal Engineer1 G1 readiness is PARTIAL / NOT READY. Combined G1 is FAIL / NOT
PASSED**, based on actual runtime-version and critical legacy acceptance defects,
not solely on future costing work. The production scope/current sizing register
is reconciled with new evidence; original reports, fixtures, failed-test logs and
other engineers' files are preserved. Changes are limited to two audit annotations,
new focused tests and acceptance evidence. No push, merge, deployment, costing
equation change, economic change or P3 implementation occurred. Stop after METHOD-001.
