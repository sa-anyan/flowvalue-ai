# FV-P1-EVIDENCE-001 — Consolidated engineering verification and G1 readiness

Date: **11 November 2026**. Owner: Engineer 1. Scope: the 12 registered preliminary sizing methods and their unit/source/applicability/cost-interface evidence. **Overall decision: PARTIAL; G1 is not ready to pass.** No production or test code changes were made.

## Required counts

| Measure | Result and exact meaning |
| --- | --- |
| Methods with verified original engineering-publication sources | **0/12**. Repository code lineage is recovered for 12; publication-of-origin is not. |
| Independently corroborated equations/relationships | **11/12 screening identities or explicit conservation rearrangements**; **1 partial**: compressor ideal Z=1 branch. This is not11 independently validated equipment designs. |
| Accepted unit contracts | **12 native input/output contracts confirmed and documented**; **0/12 complete arbitrary-source-unit→sizing→costing chains formally accepted**. FV-P1-UNIT-001 acceptance is not established. |
| Methods with documented applicability | **12/12**, individually assessed; conditional preliminary screening, not detailed design. |
| Methods requiring additional project-qualified inputs/evidence | **12/12** beyond an equipment name/tag or generic stream flow. This does not mean every such input is missing in every project. |
| Sizing-to-costing interface records | **12**, all conditional or requiring an explicit intermediate relationship; no universal pairing approved. |

## Separate decisions

- **Unit verification — PARTIAL.** The 36 named reconciliation records have30 passing bounded checks (including negative/basis-rejection checks), one PARTIAL historical-price-proxy arithmetic record and five BLOCKED unsupported conversions. This is not exhaustive acceptance of the 191 canonical unit definitions,495 aliases or 67 word aliases. No standalone UNIT-001 execution/acceptance report was found in this checkout, the inspected documentation/local Git history or the supplied sizing reports. Existing references to the ticket do not prove completion. An external report may exist; its acceptance must be supplied/reconciled rather than assumed.
- **Original-source provenance — BLOCKED.** All12 IDs are registered in the earliest located addition at `50e5bf4720a6cc4857ddb2ae9cefcca181dbe75f`. Source history/comments and candidate design documentation do not identify the publication used by the implementer. Independent references support physical relationships, but cannot prove historical intent.
- **Native numerical verification — PASS within tested domain.** The existing independently expected304 native checks pass after C01/C02/C03. Original expected values and before-fix failures remain intact.
- **Engineering applicability — PARTIAL.** Assumptions, exclusions, missing inputs and supported additional checks are now documented for all 12. Those assessments are not approved process-specific designs or universal vendor operating envelopes. No unsupported percentage margin is invented.
- **Sizing-to-costing compatibility — PARTIAL.** Matching units is insufficient. The review distinguishes gross/working volume, actual/standard gas flow, thermal area conventions, removal rate versus chamber size, water throughput versus IX vessel volume and power/rating conventions. Technology, materials, package scope and source limits still need selected-model acceptance.

## Source and applicability reconciliation

The source register separates code-origin commits, unknown original publication lineage, independently inspected references and differences from the code. Corroboration includes DOE first-law/heat-transfer identities, EPA capacity/contact-time/loading definitions, NASA ideal compression, a state-qualified Z definition, residence-time definitions and independent moisture/pressure-work conservation derivations. See [the source ledger](evidence/sources_and_scope.md) for checked URLs/sections, access limitations and exactly what each source does and does not support.

The compressor's multiplicative Z term is not established by the ideal NASA model as a rigorous real-gas compression method. Source total-state assumptions also require consistent treatment. Dryer gas residence is not particle drying time; hydraulic filter loading is not a complete cake/cycle design. Selected U/F, resin working capacity, vessel residence/working fraction and gas properties require qualified project evidence. These limits are explicit in `sizing_applicability_register.csv`; no textbook edition/page, source lineage or universal design range was invented.

## Unit and model-native reconciliation

`unit_verification_acceptance_matrix.csv` records source/destination units, relationship, independent expected value, current result, tolerance, evidence and bounded acceptance. The five unsupported conversion cases cover velocity, dynamic/kinematic viscosity, heat-transfer coefficient and standalone residence time. Fixed native parameters and internal time factors remain separately numerically checked. Annual quantity uses an explicitly stated rate×hours×utilization example;314 days is an assumption, not a universal plant maximum. FX arithmetic uses a stored dated snapshot and does not change price year. Historical cost-index/CPI-proxy arithmetic does not establish a real current CEPCI observation or industrial escalation accuracy.

The shared converter handles1 L/s→3.6 m³/h in the bounded check; the current file parser fails to normalise that same unit. Therefore converter acceptance cannot substitute for source-ingestion acceptance. Gauge/absolute pressure needs a stated atmosphere; differential-pressure meaning is a caller/input-role contract, not a number inferred from a pressure unit.

The metadata inventory contains **594 models** (154 Garrett,421 OpenPyTEA,15 Nottingham and4 additional), with 1063 coordinate/context records. Garrett has 4 unresolved required-coordinate records; OpenPyTEA has 7 manual source-coordinate requirements. Nottingham's native-only handling is not universal conversion acceptance. The supplemental inventory contains units/scope metadata, not reproduced costing coefficients or approval of all models.

The compressor result is efficiency-adjusted compression power. A source may require isentropic/fluid/shaft/driver-rated power; source definitions and loss conventions must be checked rather than universally renaming kW as one of them. Algebraically `Pisentropic = Preturned*eta` within this model; mapping to a source's fluid/shaft term needs that source's exact definition. Similarly Nottingham motor-rated pump power cannot automatically be the 0.1 kW hydraulic quantity. These are physical compatibility requirements, not new pricing calculations.

## Reconciled test evidence

No full suite was repeated because this ticket changes no production or test behaviour. The completed SIZE-C03 evidence is reused with log/XML hashes and scope checks in `evidence/evidence_reuse_assessment.json`:

| Existing completed suite | Exact result |
| --- | --- |
| All12 independent native methods |304 passed |
| Compressor-focused |78 passed |
| Heat-duty-focused |90 passed |
| Pump-focused |68 passed |
| Targeted unit/interface and R-01 regressions |66 passed |
| Cross-file tests |62 passed, 5 failed |
| Complete canonical backend |**2305 passed, 5 failed, 3 skipped**,367 passing subtests; one existing test-client warning;200.51 seconds |

These overlapping suites must not be added together as unique-test counts. The full run is a historical completed execution, not represented as a fresh run. The only fresh numerical work here is the small deterministic36-record conversion/quantity evidence supplement. Expected values are independently defined constants/dimensional relations or explicit synthetic assumptions, not outputs of the production function being checked. Numerical tolerances are floating-point evidence tolerances, not engineering uncertainty.

The five integration failures remain Engineer 2's two XLS Boolean-type failures and three L/s-normalisation failures. The three skips remain private Charlie workbook, private Charlie snapshot and unavailable optional installed OpenPyTEA reference. No skip is a pass, and no failure was weakened/hidden. Native C02 validation remains correct when the Boolean type reaches it; the XLS reader erases that type upstream.

## Exact remaining G1 blockers

1. Establish/complete formal UNIT-001 acceptance with explicit unit, alias, role/reference-state and boundary scope; retain unsupported conversions as unavailable until verified.
2. Designate independently reviewed method references/derivations and applicability boundaries. Recover original sources if available; otherwise transparently distinguish an accepted independent verification reference from an unknown historical origin. Unknown origin alone is not a substitute for evaluating the official gate's reference requirement.
3. Qualify case-dependent inputs and limits for all 12 methods, including the compressor nonideal term and detailed design exclusions; native numerical agreement alone is insufficient.
4. Review the selected sizing-to-costing physical coordinate, equipment service, rating and cost-scope contracts, including explicit intermediate relations where quantities differ.
5. Resolve the five existing supported-file integration acceptance failures through Engineer 2; this task makes no ingestion changes.
6. Reconcile the broader production calculation inventory and obtain the independent reproducibility/review required by the official roadmap. The12 methods do not establish100% coverage of every costing/economics/financial function.

The official G1 criteria require identified references/applicability for all production-supported methods, passing critical numerical checks, explicit unsupported outcomes, traceable results/versions, justified tolerances and independent reproducibility. These requirements are not all evidenced. See `phase1_remaining_engineering_gaps.md` for ownership and closure actions. The original FV-P1-SIZE-001 FAIL report and C01–C03 historical reports are preserved; this dossier does not rewrite past decisions.

## Recommended next engineering task and change boundary

Reconcile/complete **FV-P1-UNIT-001** as a bounded independent unit-contract acceptance package, while Engineer 2 addresses the already documented ingestion issues under their own ownership. Then accept the source/applicability and selected model-basis contracts. Re-run tests only when changes or evidence gaps justify it. This is not authorisation to start Phase3 implementation.

Only new files under `docs/verification/phase1/closure/` were created. Current hashes of all tracked backend files and historical sizing evidence were captured and checked unchanged. No sizing equation, cost coefficient, escalation, CAPEX/OPEX/Revenue, parser, test or approved project was modified. No push, merge or deployment was performed. Stop after FV-P1-EVIDENCE-001.
