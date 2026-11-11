# FV-P1-SIZE-001 — Final engineering report

Date: 10 November 2026. Decision: **FAIL**. Verification is complete for this ticket; mandatory safety/numerical checks demonstrably fail. No production repair was authorised or performed. This is not G1 acceptance.

## Findings

| Measure | Result |
| --- | --- |
| Registered sizing methods investigated | 12/12 |
| Native input/output contracts inventoried | 12/12 |
| Independent nominal/low/high numerical comparisons | 36/36 pass across all 12 methods |
| Methods with confirmed numerical defects | 2: gas_compression and pump_duty (auxiliary output) |
| Additional method IDs with input-validation defect | 2: exchanger_area and vaporizer_area, sharing one function |
| Original implementation source provenance verified | 0/12; original citations absent; independent primary-source cross-checks documented separately |
| Fully applicability-approved equipment designs | 0/12; all 12 retain screening/design limitations |
| End-to-end unit-contract acceptance | BLOCKED for all 12 pending accepted FV-P1-UNIT-001 evidence |

A nominal match is a verified numerical example, not a fully verified equipment method. Eight method IDs have no newly detected failure in this suite, but none is thereby certified for arbitrary equipment, units or operating conditions.

Three corrective tickets are required:

1. **SIZE-C01 — compressor numerical stability (HIGH):** at gamma immediately above 1, expected 82.33066174 kW; actual 118.77803740 kW, 44.27% high. This is a declared-domain numerical boundary, not a representative operating error.
2. **SIZE-C02 — heat-duty type validation (MEDIUM):** boolean True is accepted by both area methods and returns 0.1 m². Signed numerical duties remain valid and must continue working.
3. **SIZE-C03 — pump auxiliary overflow (MEDIUM):** extreme positive efficiency produces infinite shaft power while the primary coordinate remains finite. Require a finite output or explicit rejection.

Applicability concerns include unverified resin working capacity/breakthrough, vessel kinetics and working volume, exchanger U/temperature configuration, compressor ideal-gas domain, dryer gas versus particle residence, filter hydraulic versus cake constraints, and actual versus standard gas flow. No universal published sizing range was invented. Original source evidence and UNIT-001 acceptance must be reconciled before approval.

## Sizing-to-costing compatibility

The existing pump coordinate-to-G296-122 regression passes. Independent area/volume conversion examples pass. A dryer-volume input into area-based G277-061 correctly raises a dimensional error. Source lineage is retained through a vessel adapter case and wrong parameter dimensions are rejected. Ion-exchange vessel volume versus packaged water throughput, dryer water-removal rate versus chamber volume, and heat duty versus exchanger area are explicitly different quantities. They need additional engineering steps; matching units alone cannot approve the selected equipment family. Details are in `sizing_to_costing_interface_review.md`.

## Test execution

| Suite | Results |
| --- | --- |
| Existing targeted sizing and R-01 regressions before new tests | 66 passed, 0 failed |
| New independent verification suite | 300 passed, 4 failed, 0 skipped |
| Complete canonical backend suite | 2038 passed, 4 failed, 3 skipped; 367 subtests passed; 1 warning; 175.62 s |

All four final failures are the explicit new defect assertions: two shared boolean cases, compressor stability and pump auxiliary overflow. No xfail, weakened original assertion or production fix hides them. The original backend tests, including the R-01 horizon behaviour, pass. The full run includes the three Nottingham smoke tests outside backend/tests. The 127 pre-existing duplicate untracked files were not deleted or collected; canonical tracked test paths plus the prior R-01/version-protection tests and this new suite are recorded in `evidence/full_files.json`.

Three skips: private Charlie workbook, private Charlie run snapshot and unavailable optional installed OpenPyTEA dependency. Exact test names/reasons are recorded in `evidence/skips.json`; skips are not successes. The warning concerns Starlette/httpx test-client deprecation.

Commands: run the recorded isolated Python interpreter with `-m pytest -q` and the files listed in the corresponding evidence JSON; `evidence/run_verification.py baseline|new|full` reproduces that selection while the recorded temporary interpreter exists. Raw logs and JUnit XML are retained. Tests use synthetic reference cases, an isolated assessment DB, disabled real AI/cloud calls and a socket guard. Test-owned mock/cache behaviour is preserved; no existing project results or real AI response cache is reused as numerical evidence.

## Evidence and change boundary

Baseline commit: `74f364d2ebdcbc67bd0732937f59ef6a3704dce3`. Active checkout: `/Users/user/Documents/ChatGPT/FlowValue-latest`. Existing founder edits were preserved. Hash comparison confirms 529 tracked backend non-test files unchanged from the start of this task, including the pre-existing R-01 work. Existing test files were not edited. Only verification documentation, independent test code and its static reference fixture were added. No commit, push, merge or deployment was performed.

The seven required deliverables are in this directory. Primary DOE/EPA/NASA/NIST and university references, inspected equation pages, limitations and independent hand calculations are linked in `independent_equation_references.md`; PDF hashes/pages are recorded without redistributing complete sources. All original implementation references remain explicitly SOURCE NOT VERIFIED. The official roadmap and P0 inventories are baseline requirements, not proof of validation.

## Recommended next task

Authorise the three corrective tickets, then repeat the same independent checks without changing expected results. Separately establish FV-P1-UNIT-001 acceptance and method-specific provenance/applicability evidence. Do not declare G1 passed or proceed to a new implementation phase on the strength of nominal arithmetic alone. This ticket stops here.
