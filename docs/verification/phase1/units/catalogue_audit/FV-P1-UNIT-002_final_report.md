# FV-P1-UNIT-002 — Complete canonical engineering unit catalogue audit

**Date:** 11 November 2026  
**Decision:** Audit complete; catalogue acceptance is bounded. **UNIT-001 remains PARTIAL. G1 remains open.**  
**Checkout:** `/Users/user/Documents/ChatGPT/FlowValue-latest`  
**HEAD at audit:** `74f364d2ebdcbc67bd0732937f59ef6a3704dce3`

## Acceptance totals

| Requirement | Disposition |
|---|---|
| Canonical definitions | **191/191 accounted for**, exactly one primary disposition each |
| Primary PASS | **190** at documented numerical precision and explicit context |
| Primary PARTIAL | **1 — boiler_hp**; historical identity recognized, source-specific thermal rating not independently established |
| Primary BLOCKED / NOT APPLICABLE | **0 / 0** within the existing 191 entries |
| Independent numerical coverage | **190/191**: previous 143 plus **47 newly verified**; remaining boiler_hp is identity/recognition only |
| New previously unexercised entries | All **48** receive forward, reverse, round-trip, zero/sign, non-finite, Boolean and invalid-unit checks; boiler identity does not count as physical watt verification |
| Symbol aliases | **495/495** accounted for and recognition verified; 494 PASS, 1 PARTIAL (boiler_hp meaning) |
| Word aliases | **67/67** accounted for and recognition verified; 66 PASS, 1 PARTIAL (boiler horsepower meaning) |
| Combined alias recognition | **562/562** correct intended bindings and quantity families; 560 full numeric-meaning PASS, 2 historical-boiler identity PARTIAL |
| Native engineering methods | **12/12 bounded native contracts reconciled**, UNIT-C01 protections retained |
| Costing inventory | **594/594**: 154 Garrett, 421 OpenPyTEA, 15 Nottingham, 4 additional |
| Declared costing coordinates/context records | **1063**, read from current registry contracts; all represented in dependency matrix |
| Costing interface dispositions | **583 PARTIAL, 11 BLOCKED**; unit recognition is not approval of equipment/source meaning |
| Context relationships | **14 explicitly scoped records:** 7 PASS, 6 PARTIAL, 1 BLOCKED |
| Fresh targeted suite | **4,689 passed**, 24.60 seconds; includes 3,637 catalogue/alias/dimension/guard checks |

No unused advertised unit was removed from scope or marked NOT APPLICABLE. No production changes, new aliases or conversion families, equation changes, source-data changes, commits, pushes, merges or deployments were made.

## Evidence and method

The live `unit_aliases.py`, `unit_conversion.py`, context models, engineering sizing registry/parameter contracts, and all four costing registries were inspected. The official roadmap and prior UNIT-001 / UNIT-C01 / sizing closure evidence retain their historical status; this report does not rewrite those acceptances. The exact current code revision and pre-existing file hashes are recorded in `evidence/`.

`evidence/audit_catalogue.py` independently builds definitions and alias meanings using Decimal arithmetic and primary unit definitions. Production conversion results are observations, never the expected-value oracle. `evidence/independent_oracle.json` is the static output of that independent construction. The audit compares all 191 factors, offsets, semantic quantities and pressure labels. It reuses the 143 previously exercised unit records from UNIT-001's unchanged 146 pure conversion fixtures, rather than rerunning that entire numerical fixture suite. Its original two physical derivation references also remain intact. The new-unit list is in `evidence/new_unit_ids.json`.

The new 48 include energy/time units, mol/mol-flow units, normal/standard flow, explicit US MGD, vacuum-capacity and pump compound coordinates, and item/tray/boiler coordinates. Item and tray are independently defined semantic counts; identity checks do not imply that a tray is interchangeable with an arbitrary item. Boiler hp remains partial. Numerical records identify reused versus new evidence, expected results, tolerances and observed results.

A full **21 × 21 = 441 semantic quantity compatibility matrix** checks every quantity-family pair. Power and flow-times-pressure share physical dimensions but have distinct semantic contracts; actual and standard gas volume also remain distinct. Incompatible pairs correctly reject ordinary conversion. This matrix is not a claim that all 191² combinations or every floating-point extreme were tested.

### Precision and reference limits

Exact length/mass/time definitions and independently derived composite factors use 2e-12 relative tolerance with small absolute floors. NIST's published thermochemical Btu precision is handled explicitly: 1054.350 J with half-last-place uncertainty, propagated into its rates. This verifies production at the source's displayed precision; it does not endorse all stored trailing digits. Existing tests and tolerances were not weakened. See `evidence/reference_basis.md` for references, equations and scope.

## Alias, ambiguity and duplication findings

No wrong-unit alias, conflicting symbol binding, wrong physical dimension or unintended case collapse was found among the 562 literal entries. Word aliases are intentionally case-insensitive; SI symbols are case-sensitive. Spacing, caret powers, superscripts and degree variants were exercised. Unicode subscripts such as `m₃` and `barₐ` are unsupported, explicitly rejected, and are not newly advertised capabilities. `MW` and `mW` retain different factors; `Mw`/`mw` are rejected.

Generic gallon, ton and Btu require their documented context; US and Imperial gallons are never silently interchanged. `MGD` is ambiguous and unsupported while `US_MGD` is explicit. Pressure reference roles are not inferred from bare `bar` or `psi`. The finite grammar is not an arbitrary expression evaluator.

There are legitimate equivalent-factor definitions (e.g. J/s and W, kJ/s and kW, US_gpm and US_gal/min). `evidence/equivalent_definition_groups.json` records these; equivalent named units are not conflicting definitions. No corrective deletion is proposed. **140 entries** are not direct native sizing/model targets; they remain advertised source-unit alternatives and were audited rather than labelled unnecessary.

## Native engineering contracts and six gaps

All 12 named method contracts match the current registry and parameter-unit allowlists; `evidence/native_contract_reconciliation.csv` records each. The native numerical and Boolean safety regressions pass, including compressor, heat-duty and pump corrections. They establish bounded native contracts, not universal ingestion or arbitrary source-parameter unit support.

| Known family | Current workflow classification | What remains missing |
|---|---|---|
| Velocity | REQUIRED FOR ACTIVE WORKFLOW | Filter hydraulic loading is velocity; fixed native m/h works, general velocity-unit normalization does not |
| Dynamic viscosity | OPTIONAL | No required input in the 12 native methods or declared costing coordinates; generic cP↔Pa*s absent |
| Kinematic viscosity | OPTIONAL | No current native input requires it; generic cSt↔m²/s absent |
| Heat-transfer coefficient | REQUIRED FOR ACTIVE WORKFLOW | Native W/m²/K accepted; alternate U-unit conversion absent |
| Standalone time/residence time | REQUIRED FOR ACTIVE WORKFLOW | Native hours/minutes/seconds arithmetic works; general standalone time conversion absent |
| Specific gravity | OPTIONAL | Explicit density bridge works; SG-to-density needs a reference substance/state and is absent |

The three active classifications identify missing general source-input normalization, **not failure of equations using their already-normalized native inputs**. The other fixed native compound parameters (enthalpy per mass, molecular weight, chemical equivalents and fractions) also are not a universal compound-unit catalogue. Future arbitrary parameter normalization is separately ticketed. Each corrective ticket in `unsupported_unit_requirements.csv` and `evidence/corrective_tickets.md` states its physical basis, units, equation, assumptions and independent acceptance requirements. Nothing is implemented under this audit.

## Costing dependency reconciliation

The dependency matrix reads actual `list_equipment_models('all')` contracts and resolves explicit units or lists conditional candidates for ambiguous source bases. It does not choose a gallon/ton convention on behalf of a source. Source-sized units with bounded scale prefixes retain their canonical dependencies. Shaft/fluid/driver/motor-rating power, heat-transfer surface basis, gross/working volume, throughput and actual/standard gas state still require engineering meaning. Nottingham's native-only resolver path is not misrepresented as a generic unit-validated sizing adapter.

The **11 blocked contracts** are four Garrett chemical-injection/vacuum source-coordinate discrepancies and seven OpenPyTEA manual compounds: screw geometry, three mass-flow/suction-pressure variants, another jet vacuum convention, RDC geometry, and nonlinear annual-feed coordinate. See exact model IDs and issues in the matrix. Some compounds could be derived from known dimensions after source semantics are established, but existing source spellings/manual-coordinate contracts do not establish automatic support. They remain blocked, not invented aliases. All other 583 models are PARTIAL because unit compatibility alone is not source-specific suitability approval. No costing equation was revalidated or altered.

The boiler-hp historical coordinate is recognized by the active catalogue; a generic NIST standardized boiler-hp rating cannot be attached to a historical chart without source confirmation. It is a separate partial basis, even where its identity coordinate can be supplied.

## Context-dependent scope

Fourteen relationships distinguish unit scaling from physical derivation. Qualified density supports mass-to-liquid-volume conversion; supplied gas states support actual-to-reference flow through a separate physical bridge; explicit atmosphere supports gauge-to-absolute pressure. Native exchanger/pump/vessel calculations retain their input assumptions and traceability. Missing density, atmosphere or gas reference data is not invented.

Standard-gas reference strings are opaque declarations: equality prevents a declared reference change but cannot scientifically validate the declared state. Residence-time inversion is not a universal bridge just because forward vessel sizing exists. Energy/time compound units are supported; a bare energy cannot become power without a time basis. Currency exchange and historical cost escalation remain separate dated economic services with their existing provenance limitations.

## Testing, integrity and remaining tickets

The fresh suite passed **4,689 tests** with AI/cloud disabled, a temporary assessment database and outbound socket connections blocked. `evidence/targeted_files.json`, `targeted.txt` and `targeted.xml` record the exact scope/results. It covered catalogue/alias/dimensional checks, native Boolean safety, bounded independent sizing, shared conversion bridges, compression/heat-duty/pump safety, R-01 horizon and separate currency/cost-translation regressions. The complete backend suite was deliberately not rerun. Known Engineer-2 XLS Boolean/L/s ingestion failures remain outside this ticket; this passing targeted suite does not close them.

All **1,054 pre-existing source/test/evidence files** in the captured scope retained their hashes. Historical reports, fixtures, corrections and duplicate files were preserved. Only the new audit directory was written. `evidence/scope_integrity.json` records the comparison; existing dirty working-tree changes predate this task.

Remaining proposed tickets: **UNIT-EXT01–06**, **UNIT-002-C01** boiler source basis, **C02** 11 source-coordinate contracts, **C03** future alternate native-parameter normalization, **C04** stronger semantic reference/context assurance. Optional tickets are not asserted to block current native numerical operation.

**Updated decision:** all catalogue/alias entries now have explicit dispositions; bounded native contracts remain accepted. Wider UNIT-001 stays **PARTIAL** because missing source-input families, context/source semantics and costing/economic provenance are still unresolved. **G1 is not passed. Stop after UNIT-002; no Phase 3 implementation.**
