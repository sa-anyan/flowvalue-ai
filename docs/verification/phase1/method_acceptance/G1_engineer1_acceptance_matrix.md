# G1 Engineer-1 acceptance matrix — METHOD-001

Date: 11 November 2026. Authority: official development roadmap paragraphs117–122,
retained in `evidence/official_G1_criteria.json`; the original roadmap is unchanged.

**Engineer-1 readiness: PARTIAL / NOT READY. Combined G1: FAIL / NOT PASSED.**
The shared gate cannot pass while runtime method-version lineage and the active
legacy validity counterexamples remain unresolved. Deferred P3/P4 validation is
not being counted as either passed P1 evidence or an automatic P1 blocker.

| Official requirement | Engineer-1 scoped evidence | Shared/remaining outcome | Decision |
|---|---|---|---|
| 117:100% production-supported calculation methods have a verification reference and applicability statement | All12 registered sizing IDs plus3 active preliminary estimators have accepted replacement references/derivations and bounded applicability records. Two reachable legacy hold-up implementations are additionally inventoried, with the same physical derivations but incomplete implementation acceptance. | All17 are accounted for; 15 conditional applicability records accepted,2 legacy records PARTIAL. No active route is silently deprecated or removed to reach100%. | PARTIAL overall; PASS for the canonical15 bounded relationships |
| 118:100% critical numerical tests pass | Native304 reused; SIZE-C01/C02/C03, UNIT-C01 and R-01 retained through UNIT-003 evidence.99 affected/new tests pass;20 independently specified valid examples reproduce. | Two new negative-flow legacy sizing checks FAIL; five earlier Engineer-2 XLS/L/s cases remain open and were not rerun or presumed fixed. | PASS for Engineer-1 registered/native arithmetic; FAIL for shared critical-path readiness |
| 119:unsupported calculations are never silently treated as valid | Native unit/type/domain guards and explicit screening limits remain. Compressor approximation and mixing-volume basis now emit clearer audit warnings. | volume_residence accepts -10m3/h and returns -25m3; mass_residence accepts -1000kg/h and returns -3.125m3. This is an invalid sizing-stage result; no claim is made that downstream costing accepts it. Physical applicability of supplied properties is not independently enforced by scalar guards. | FAIL at the active legacy sizing boundary; broader context enforcement PARTIAL |
| 120:critical reported results trace to inputs and method versions | Method IDs, source IDs/rows, original assumptions, equations, unit conversions and units are largely retained. External verification packet pins current source and reference hashes. | Production native/bridge audits do not bind an immutable engineering implementation version. Compact source IDs also need their matching immutable report snapshot through save/export. A test-side hash does not retroactively fix production lineage. | FAIL — METHOD-TRACE01; shared snapshot integration PARTIAL |
| 121:method-specific independently defined numerical tolerances | Twelve retained native tolerances are justified by exact products, division, gas constants, compressor exponentials and independently reconstructed pump units. Supplemental identities have separately specified tolerances. | These are rounding tolerances, not engineering uncertainty or a universal design margin. | PASS within the documented method/reference cases |
| 122:independent reviewer can reproduce every designated critical reference and identify validity limits | Source-pinned reproduce.py verifies all20 designated valid cases and records scope/limits; reference fixtures are independently supplied. Original historical publications remain UNKNOWN rather than invented. | The matching dirty working tree is required; HEAD alone is insufficient. External review execution is not asserted. Invalid legacy cases and shared ingestion/versioning gaps prevent representing the complete supported workflow as independently accepted. | PARTIAL for the combined exit gate; technical reference packet reproducibility PASS |

## A — Engineer-1 numerical acceptance

**PASS:** twelve native method IDs (eleven underlying callables), three additional
active estimators, and independent nominal valid examples for the two legacy
hold-up branches. No equation or coefficient changed. New compressor references
support only the documented fixed-property screening approximation. The shared
legacy branches' invalid-input acceptance is a separate FAIL, not hidden by
successful nominal arithmetic.

## B — Remaining Engineer-1 engineering/source/applicability work

The previously missing replacement-reference decisions are completed for the
fifteen principal methods; no original publication lineage is fabricated.
The two legacy implementations still need their correct shared acceptance
contract. METHOD-TRACE01 requires an explicit immutable method/software version
at the calculation boundary and preservation through the owned integration
contracts. A corrective design must be coordinated with Engineer2 rather than
silently changing their schemas/persistence here. Project-level physical
assumptions still need qualified source basis and professional review where
applicable; a conditional identity is not a plant design certificate.

## C — Engineer-2/shared integration dependencies

- **METHOD-LEGACY01:** two active legacy hold-up branches fail negative-flow
  rejection. Exact standalone inputs, returns and expected rejection are in
  `evidence/legacy_boundary_results.json`; test entry point returns nonzero.
- **METHOD-TRACE02:** pin source-report versions wherever compact source IDs are
  copied, saved or exported; verify preservation of engineering method versions.
- **METHOD-APP01:** expose the native compressor and volume-basis warnings in
  applicable views/exports; nested audit propagation was tested, UI rendering was
  not changed or accepted.
- **SIZE-XF01:** two previously recorded XLS Boolean-type-loss failures.
- **SIZE-XF02:** three previously recorded L/s normalization failures.

The last five retain their existing ownership and evidence. No extraction,
schema, API, frontend or persistence code was modified; no false closure is
claimed from not rerunning those tests.

## D — Future P3/P4 validation

All594 costing configurations remain inventoried, not independently cost-model
validated here. Eleven source-coordinate contracts and boiler-hp thermal rating
retain their UNIT-003 dispositions as source/model-validation dependencies.
Automatic incompatible conversions remain guarded in existing UNIT-003 evidence;
there is no new evidence that a canonical P1 method itself accepts those blocked
cost coordinates. Economic model/source validation, index observations, FX
provenance, CAPEX/OPEX/revenue and financial policies remain their own phase work.
Nothing in this ticket declares those later phases complete or initiates P3.
