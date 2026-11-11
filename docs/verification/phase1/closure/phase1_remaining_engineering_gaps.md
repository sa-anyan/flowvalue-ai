# Remaining Phase1 engineering evidence and G1 requirements

11 November 2026. Scope: twelve registered preliminary sizing methods and their interfaces. This is a reconciliation, not a production release or a Phase3 implementation.

## Separate decisions

| Area | Decision | Evidence and unresolved scope |
| --- | --- | --- |
| Unit verification | **PARTIAL** | Existing tests plus36 named reconciliation records;30 bounded PASS checks, one historical-price-proxy arithmetic PARTIAL, five unsupported conversions BLOCKED. No FV-P1-UNIT-001 acceptance report found. |
| Original scientific-source provenance | **BLOCKED** | Git code origin recovered for 12 IDs, but actual publication-of-origin established for 0. Independent sources are recorded separately. |
| Native numerical verification | **PASS within tested domain** |304 independent native checks pass after C01/C02/C03; expected results and historical failures preserved. |
| Engineering applicability | **PARTIAL** |12 individual assessments documented; all need case-specific data/qualification. Conditional preliminary screening, not detailed design acceptance. |
| Sizing-to-costing compatibility | **PARTIAL** |12 interface reviews and594-model metadata inventory; no unconditional technology/rating/scope approval from matching units. |
| Supported-file integration | **FAIL on five acceptance cases** |Two XLS Boolean preservation failures and three L/s normalisation failures; Engineer 2 owns them. No ingestion fix made. |

## Precisely what is missing

**E1 — Formal UNIT-001 evidence and bounded acceptance.** Supply the actual report/reviewer sign-off if work exists elsewhere; no standalone execution/acceptance artefact was found in this checkout or inspected local history. Otherwise complete an explicitly scoped independent verification of required units and aliases. The191-unit/495-alias catalogue is not itself verified. The five named unsupported conversion families are velocity, dynamic viscosity, kinematic viscosity, heat-transfer coefficient and standalone residence-time conversion. Native methods accept fixed U/time units and contain checked time factors; that is not arbitrary-unit conversion support. Record each supported versus unavailable pathway rather than promising all units. Explicit pressure role, reference state, gallon/ton and temperature-difference semantics must survive the whole chain. The new L/s shared-converter probe passes while the ingestion path fails, so acceptance must name the boundary.

**E2 — Source traceability and reviewed reference designation.** Recover original author/design notes where possible. Code entry at 50e5bf47 proves repository lineage, not a scientific origin. Eleven screening identities/conservation rearrangements have independent corroboration; compressor Z=1 has support, but the full nonideal multiplier remains only partial. G1 requires identified verification references, not necessarily recovery of an unknowable historical author intention. If origin cannot be recovered, obtain an independent review accepting a clearly identified replacement reference/derivation and disclose that original lineage remains unknown. Do not relabel independent support as original-source proof.

**E3 — Intended applicability and missing project inputs.** The new applicability register specifies what each method requires and excludes. All12 require project-qualified inputs beyond a name/tag or generic M&E flow: resin working capacity/targets, kinetic or storage time, terminal temperatures/U/F, gas state/properties/efficiency, moisture basis, differential head and pump curves, filter/cake duty, or gas versus particle drying. No universal range or percentage margin is invented. Native mathematical guards are not published equipment operating ranges. No detailed-design certification is established.

**E4 — Cost-model semantic acceptance.** Establish per-selected-source coordinate meaning, not just hp/kW/m3/ft2 dimensions. Particularly: isentropic/efficiency-adjusted/fluid/shaft/motor-rated power, actual versus standard gas flow, active versus total thermal area, gross versus working vessel volume, and purchased versus installed/package scope. The compressor code's efficiency-adjusted power is not universally the same quantity as a source-labelled fluid-power cost input. Nottingham motor rating cannot automatically equal hydraulic power. Volume→throughput, duty→area and water-removal→dryer-volume require explicit physical relations and supported assumptions. Garrett has 4 unresolved required-coordinate records; OpenPyTEA has 7 manual source-coordinate requirements. Nottingham's native-only path is not an accepted universal-conversion adapter. Source-native years/currencies and independent indexing provenance remain separate from physical units.

**E5 — Existing ingestion failures (Engineer 2).** Resolve SIZE-XF01 and SIZE-XF02 using the unchanged synthetic assertions. Preserve Boolean cell type and full flow-unit identity through normalisation. The five failures violate acceptance of those upload cases even though native calculations are correct. See `../sizing/cross_file_engineer2_handover.md`; this evidence ticket does not rewrite that architecture.

**E6 — Gate-level independent review and broader coverage.** The official roadmap G1 requires all production-supported methods to have verification references/applicability, critical numerical tests to pass, unsupported calculations to remain explicit, traceable outputs/method versions, justified tolerances, and independent reproducibility. These twelve methods are only a subset of the broader production calculation inventory identified at P0. This ticket does not reverify every costing/CAPEX/OPEX/revenue/finance method or constitute an independent reviewer sign-off. Resolve the scoped evidence and critical integration gaps, and reconcile the wider inventory before asserting 100% gate coverage.

## Existing test evidence — reused, not rerun unnecessarily

C03 recorded 304 native checks passing; compressor 78, heat 90, pump 68 and targeted R-01/interface66 checks passed. These suites overlap and must not be added as unique-test totals. Complete canonical backend: 2305 passed, 5 failed, 3 skipped, 367 passing subtests and one warning. The skips are private Charlie workbook, private Charlie snapshot and unavailable optional installed OpenPyTEA reference; they are not successes. The warning is the existing Starlette/httpx test-client deprecation. Historical before-fix red tests/reports remain intact.

No production or test changes are made here. Closure evidence stores current hashes and confirms the existing C03 pump patch and unchanged other baseline files. Reused test evidence is identified and hashed rather than represented as a new test execution.

## Recommended next engineering task

Complete/reconcile **FV-P1-UNIT-001 formal acceptance** with an explicit unit/role/reference-state scope and independent review. In parallel ownership terms, Engineer 2 should resolve the two already documented ingestion issues; this document is a handover, not automatic delegation. Then review/designate source references and the conditional applicability/model-basis contracts for the 12 methods. Re-run only tests affected by actual changes, followed by the agreed gate regression. Do not start Phase3 implementation or claim G1 passes from this dossier alone.
