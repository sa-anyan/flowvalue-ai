# FV-P1-UNIT-001 — Formal engineering unit acceptance

Date: **11 November 2026**. Owner: Engineer 1. **Decision: PARTIAL.** The named conversion subset is accepted under its documented conditions. Complete native input/type contracts do **not** meet acceptance because of the confirmed UNIT-C01 Boolean-safety defect. **G1 does not pass.** No production function, alias, parser, equation or coefficient was changed.

## Formal acceptance counts and denominators

| Requested measure | Result |
| --- | --- |
| Supported conversion/derivation pathways independently verified | **148**:146 named pure unit cases and2 explicit physical derivations requiring density or gas-state inputs. |
| Canonical units assessed | **191 inventoried**, of which **143 numerically exercised** by the named references. The other 48 are outside numerical acceptance, not silently passed. |
| Aliases verified in bounded scope | **75 noncanonical spellings**, plus **1 equivalent canonical unit** (kJ/s), giving76 executable spelling/equivalence checks. This does not accept all 495 aliases or 67 word aliases. |
| Methods with fully accepted native unit/type contracts | **0/12 complete contracts**. All12 have verified numeric unit subcontracts, but all 12 have an unsafe NumPy-Boolean assumption case. |
| Complete bounded numeric source-to-native sizing paths | **24 PASS**:two explicit source-unit paths per method, with valid numeric/native-unit assumptions. These are not arbitrary-input, file-to-pricing or full type-safety acceptance. |
| PARTIAL cases in primary acceptance register | **2**, dated FX/source acceptance and historical-price-proxy basis.12 method contract rows and583 model-interface review rows separately remain PARTIAL; those populations must not be added together. |
| BLOCKED cases in primary acceptance register | **26**:6 absent conversion/derivation families,7 missing-context/incompatible-quantity paths and13 unsafe Boolean-boundary cases. Correct negative-test rejection does not mean the blocked conversion was performed. |

The primary register contains201 records:173 PASS,2 PARTIAL and26 BLOCKED. Its173 PASS records comprise148 conversion/derivation cases,24 bounded numeric sizing paths and1 explicit annual-quantity calculation. Do not report173 unique conversion pathways or combine overlapping test totals. Catalogue/role/model registers have their own denominators and do not inflate acceptance percentages.

## Accepted bounded scope

The explicit reference list covers metric/international mass, length, area and volume definitions; mass/volumetric-flow time bases in seconds/minutes/hours/days; US/Imperial gallons; pressure scaling and qualified gauge/absolute conversion; absolute and difference temperatures; energy/power, including an explicit energy-per-time basis; density; compound chart-coordinate scales; and standard-gas volume/time scaling only at explicitly identical qualified reference states. Signed heat duty is preserved.

The shared converter's supported input type contract is finite Python int/float, with NumPy float64 accepted on the tested version through float inheritance. Decimal/Fraction and NumPy int64/float32 are explicitly rejected by that API; they are NOT APPLICABLE to this strict converter contract, even though some native sizing callables support those numerical representations. Numeric strings are not silently parsed. Python/NumPy Booleans are rejected by the shared converter.

Physical derivations are separate: D01 converts2 kg/s to7.2 m³/h using explicitly supplied1000 kg/m³; D02 converts100 actual m³/h to50 reference m³/h using explicit absolute states and Z with unchanged gas composition. Neither guesses density, composition, standard conditions or a stream relationship. Bare kg/h→m³/h and actual→standard volume remain blocked without an appropriate supported physical relationship/context.

The 24 source-to-native paths explicitly normalise kg/s or tonne/h to kg/h; L/s or L/min to m³/h; W or MW to kW, then run the existing selected sizing method with independently specified native parameters. Expected values come from static independent references and linear scaling, not production outputs. The primary data source is a synthetic numeric input, not an uploaded workbook or LLM-generated guess.

## New safety defect — UNIT-C01

Thirteen new assertions fail because a NumPy bool_ can enter a sizing assumption or source observation without being rejected before float coercion. The shared converter rejects it, but `engineering_sizing.common.positive` and non-heat `adapter.observation` do not reliably preserve that distinction. Examples include True interpreted as a heat-transfer coefficient, efficiency or residence time. Invalid types can produce finite, plausible-looking sizes.

One failing assumption case affects each of 12 methods; a thirteenth covers a direct pump volume-flow observation. `evidence/UNIT-C01_numpy_boolean_guard.md` records the owner, exact boundaries, examples and proposed separately authorised correction scope. This task adds no production fix. A numeric0/1 filter is inappropriate because genuine0/1 values must remain distinguishable from Booleans.

This is separate from SIZE-C02's corrected heat-duty-value guard and Engineer 2's XLS Boolean cell-type loss. Existing C01/C02/C03 calculations are unchanged and their original tested arithmetic remains passing. Formal validation has exposed an additional unsupported admission path, not introduced a new production regression.

## Five previously blocked conversions and specific gravity

The independent dimensions/factors are established, but the implementation does not support the requested standalone conversions:

| Case | Relationship | Required extra physics | Decision |
| --- | --- | --- | --- |
| Velocity |m/s→ft/s:divide by.3048 |None for like-for-like speed units |BLOCKED; UNIT-EXT01 |
| Dynamic viscosity |cP→Pa·s:multiply.001 |None for dynamic-to-dynamic; density only for dynamic/kinematic relation |BLOCKED; UNIT-EXT02 |
| Kinematic viscosity |cSt→m²/s:multiply1e-6 |None for kinematic-to-kinematic |BLOCKED; UNIT-EXT03 |
| Heat-transfer coefficient |Btu_IT/(h ft² delta°F)→W/(m² K):defined energy/time/area/interval factor |Retain same physical surface/U convention; does not estimate U |BLOCKED; UNIT-EXT04 |
| Standalone residence time |min→h:divide by60 |None to convert time; deriving time from V/Q is a separate problem |BLOCKED; UNIT-EXT05 |
| Specific gravity→density |rho=SG×rho_reference |Reference substance/density at defined T/P; no hidden water density |BLOCKED; UNIT-EXT06 |

The first five are genuinely absent standalone quantity/unit interfaces in the shared converter. Embedded native EBCT/seconds/hour arithmetic and fixed native U inputs do not implement a general converter. Specific gravity additionally needs a physical reference and a supported derivation interface. These are recommendations only; no aliases or multipliers were added to production. See `unsupported_unit_conversion_register.csv` for exact observed errors and ticket recommendations.

## Roles, gas states and economics

Pressure symbols alone do not establish operating/design/differential roles. Bare pressure scaling leaves an unspecified basis unspecified. Gauge/absolute changes require an explicit positive atmospheric reference; conflict and dimension checks remain active. Differential pressure stays a named engineering field; the converter's basis enum is not a universal differential-role validator.

Absolute temperatures and intervals remain separate. A heat-transfer area is not thermal duty, gas holdup is not particle drying, gross volume is not working volume, and actual flow is not standard/normal flow without qualified states. Standard/normal labels do not define universal temperatures/compositions. Supplied reference strings are identity assertions, not a thermodynamic or composition validator. The explicit-state gas bridge is a separately bounded physical derivation.

Currency conversion, price-year escalation, index-ratio arithmetic and published index observations are distinct. Targeted tests confirm deterministic FX/proxy arithmetic; the present report does not independently authenticate the stored external observations. Both source/basis records remain PARTIAL. The prior historical proxy is not relabelled as real CEPCI. Annual quantities use explicit hours/utilisation once;314/365 days are not universal plant availability assumptions.

## Costing interface assessment

All **594 models** were reviewed through native metadata:154 Garrett,421 OpenPyTEA,15 Nottingham and4 additional. The register records required coordinates, quantity kinds, source units, year/currency, and a same-unit syntax/context probe. A same-unit identity is explicitly **not** independent verification of the source factor or physical basis.583 interface rows remain PARTIAL;11 are BLOCKED by unresolved/manual source coordinates.

The review preserves distinctions between hydraulic, efficiency-adjusted/shaft-proxy and motor-rated power; actual/standard gas flow; capacity/throughput; gross/working volume; and active thermal area. Nottingham's native-only path is not accepted as a universal conversion adapter. Source ambiguity, equipment technology, selected correlation basis and cost scope must be reviewed before per-model approval. Costing equations/coefficients were not recalculated or changed, and matching hp/kW/m³/ft² does not by itself prove suitability.

## Exact test evidence

New bounded suite initially reported283 passes and12 Boolean-assumption failures; the final suite adds the source-observation assertion. The **final targeted execution** reports **728 passed,13 failed,0 skipped** in 2.65 seconds. All 13 failures are the new UNIT-C01 assertions. All 146 conversion cases,76 spelling/equivalence checks and 24 numeric source-to-native paths pass. The original304 native sizing checks also pass in this targeted run.

The targeted file list includes existing converter/bridge, gas-compression bridge, heat-duty validation, independent native, FX and cost-translation tests. No original test was modified, skipped, xfailed or weakened. Expected fixtures were constructed independently from unit definitions and parent reference calculations. Numerical tolerances and substitutions are documented in `independent_unit_reference_calculations.md`.

The complete backend suite was **not rerun**: production is unchanged and this task explicitly requests targeted verification. The latest historical complete run remains 2305 passed, 5 failed, 3 skipped, 367 passing subtests and one test-client warning. It is not claimed as a new execution, and no combined/full-suite count is inferred by adding the 13 new failures. Historical skips were private Charlie workbook, private Charlie snapshot and unavailable optional installed OpenPyTEA reference. Exact new failure names/messages, logs/XML, file lists and code-scope hashes are retained under `evidence/`.

## Engineer 2 integration dependencies

- **SIZE-XF01:** two XLS Boolean preservation failures remain upstream of conversion; the reader loses the Boolean type. Native guards cannot recover a type already erased to an ordinary number.
- **SIZE-XF02:** the shared converter verifies **1 L/s=3.6 m³/h**, but three parser-normalisation cases remain unresolved. Shared conversion PASS is not file-ingestion PASS.

Those five cases are preserved in the prior cross-file evidence/handover. This ticket makes no ingestion changes and does not claim arbitrary-source-unit or universal file-format compatibility.

## Acceptance and G1 decision

**FV-P1-UNIT-001 achieves bounded numerical conversion acceptance for the named subset, but does not meet all requested complete native-contract criteria. Overall: PARTIAL.** Full native unit/type acceptance is blocked by UNIT-C01; unsupported/context-dependent paths remain explicit. The native numeric unit subcontracts are verified for 12 methods, but zero complete native contracts are accepted while their required Boolean rejection checks fail.

**G1 cannot pass.** In addition to the new safety defect, the existing ingestion failures, unaccepted physical model-basis/applicability contracts and broader method/reference/reviewer evidence remain open under the official roadmap. The prior original-publication-lineage gap is not erased by independent unit tests. Do not turn unsupported cases into PASS to improve percentages.

Recommended next engineering task: separately authorise **UNIT-C01** to correct pre-coercion Boolean validation at native assumption/observation boundaries while preserving legitimate numerical types and C01–C03 behaviour. Then rerun these unchanged assertions and the agreed affected regressions. Engineer 2 retains ownership of its existing ingestion issues; optional UNIT-EXT functionality requires separate scope approval. No Phase3 implementation is started.

## Change boundary

Added only this unit evidence package, a new verification test file and its independent static fixtures. Production conversion functions, aliases, sizing/costing/economic equations, ingestion, historical evidence and approved projects remain unchanged. No push, merge or deployment was performed. Stop after FV-P1-UNIT-001.
