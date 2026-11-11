# SIZE-C03 — Pump numerical safety correction

Date: 10 November 2026. Parent: FV-P1-SIZE-001. **SIZE-C03 numerical correction: PASS**, supported by the completed evidence below. **Cross-file compatibility: PARTIAL with five failing integration cases**, handed to Engineer 2. G1 is not passed. No Phase 3 implementation is started.

## Reproduced failure and cause

The unchanged `test_required_finite_pump_auxiliary_outputs` failed before production changes. Exact inputs: volume flow 3.6 m³/h, differential pressure 1 bar, efficiency 1e-320. The historical flow-pressure coordinate is finite (approximately 0.22988950107343342 in 1000 US_gpm_psi), and hydraulic power is 0.1 kW. Shaft power `0.1/1e-320` exceeds floating-point range and becomes infinity. Inputs and efficiency passed the existing positive/finite checks. Only the primary sizing result had a registry-level output guard; auxiliary metadata had no equivalent check.

This is division overflow in an extreme mathematical case, not evidence that a real pump can operate at that efficiency. No faulty gallon/psi factor or new pump performance equation was found.

## Minimum correction

Only `backend/engineering_sizing/pumps.py` changes production behaviour in this ticket. Existing equations remain:

- `coordinate = Q_US_gpm * differential_pressure_psi / 1000`.
- `hydraulic_power_kw = Q_m3_h / 3600 * deltaP_bar * 100000 / 1000`.
- `shaft_power_kw = hydraulic_power_kw / efficiency`, when efficiency is supplied.

The existing `common.positive` guard now checks the calculated primary coordinate, hydraulic power and optional shaft power before return. Nonfinite or unrepresentable nonpositive results are explicitly rejected, including through direct invocation. The original overflow case now raises `ValueError: calculated shaft power kW must be finite and positive` rather than returning infinite auxiliary power.

No efficiency floor or empirical factor is added. Supported efficiencies remain finite 0<eta<=1; omitted/None efficiency retains the existing optional shaft-power behaviour. A numerical stress case eta=1e-300 still returns a finite approximately 1e299 kW shaft-power result, without claiming that efficiency is physically realistic. Existing units, output names, function signature, source constants and costing correlations are unchanged. At eta=0.5, the reference returns the same 0.1 kW hydraulic and 0.2 kW shaft power.

## Independent verification and scope

`backend/tests/test_pump_numerical_safety.py` adds 58 cases. A 60-digit Decimal pressure-work oracle derives hydraulic power in SI, reconstructs the historical coordinate from exact gallon/psi definitions, and divides by the explicit efficiency for shaft power. It does not obtain expected values from the production function. The grid varies four flows, three differential pressures and optional/0.1/0.5/1 efficiencies. Additional cases test invalid efficiency, overflow, underflow and absence of an arbitrary efficiency cutoff. Coordinate tolerance 1e-11 and power tolerance 1e-13 reflect independent unit reconstruction and simple arithmetic, respectively; these are not engineering uncertainty allowances.

The original independent assertion, SIZE-C01/C02 production corrections and their historical reports are unchanged. No ingestion, schema, orchestration, CAPEX/OPEX/Revenue, financial or costing production file was modified. Scope hashes and the exact production patch are retained in `SIZE-C03_evidence`.

## Test outcomes

| Verification | Exact result |
| --- | --- |
| Original unchanged pump assertion before correction | 1 failed, reproduced |
| Pump-focused suite (58 new cases plus existing sizing tests and original assertion) | **68 passed**, 0 failed |
| All 12 independent sizing methods | **304 passed**, 0 failed |
| SIZE-C01 compressor-focused suite | **78 passed**, 0 failed |
| SIZE-C02 heat-duty-focused suite | **90 passed**, 0 failed |
| Targeted sizing/interfaces/unit bridges and R-01 regressions | **66 passed**, 0 failed |
| Cross-file pytest matrix | **62 passed, 5 failed**, 0 skipped |
| Complete canonical backend | **2305 passed, 5 failed, 3 skipped**, 367 subtests passed; 1 warning; 200.51 seconds |

Against the prior baseline (2184 passed, 1 failed, 3 skipped), the original pump failure now passes, all 58 new pump cases pass, and 62 new cross-file cases pass. Five new cross-file failures are the Engineer 2 findings described below. No previously passing original test fails. The full suite exits nonzero transparently for those five integration failures. The three skips remain the private Charlie workbook, private Charlie snapshot and unavailable optional installed OpenPyTEA reference; they do not count as successes. The warning is the existing Starlette/httpx test-client deprecation.

Before/after logs, final JUnit XML and canonical file lists are retained. `SIZE-C03_evidence/run_verification.py before|pump|cross|new|compressor|heat|baseline|full` records the selections using the existing isolated verification interpreter. The retained before log reproduces the failure; rerunning it after correction passes. No original assertion was skipped, xfailed or weakened. Real AI/cloud calls and external sockets were disabled; only isolated synthetic assessment storage and synthetic fixtures were used.

## Cross-file audit and Engineer 2 ownership

The active upload formats are XLSX/XLSM/XLS. All use the existing canonical worker/report/engineering dispatcher/registry, with different readers for OOXML and BIFF. Twenty-one synthetic workbooks exercise row and column layouts, multiple sheets, merged titles, units, signs, booleans and missing information. No customer workbook was changed or retained as a test fixture. The new tests use explicit method/parameter proposals; they do not claim to validate live AI extraction or matching.

The matrix has 55 PASS, 5 FAIL and 7 BLOCKED engineering rows. Pytest cross-file checks report 62 passed and 5 failed because explicit rejection of seven unsupported upload formats is a passing negative test, not a supported engineering pathway. Two XLS Boolean heat-duty assertions fail upstream of SIZE-C02; three L/s pump equivalence assertions fail because ingestion lacks that unit. These failures remain visible in the full suite and are not repaired by filtering legitimate numerical values downstream.

See `../cross_file_compatibility_report.md`, `../cross_file_compatibility_matrix.csv` and `../cross_file_engineer2_handover.md`. PDF/Word/CSV/JSON/DWSIM-native/images/XLSB are not active upload pathways here. Historical scaffold documentation is not proof of implemented support.

## Acceptance and next work

SIZE-C03 passes its numerical acceptance: the original assertion passes, ordinary pump calculations match independent references, outputs are finite or explicitly rejected, SIZE-C01/C02 remain passing, and no unrelated existing regression is introduced. Newly exposed ingestion failures remain a separate unresolved integration gate. All 12 methods retain their original applicability/provenance limitations and unconfirmed UNIT-001 acceptance. The consolidated status does not supersede historical reports or declare G1 passed.

Recommend Engineer 2 resolve SIZE-XF01/XF02 and rerun these unchanged matrix assertions, then obtain independent unit/provenance/applicability acceptance. No automatic follow-on implementation, commit, push, merge or deployment was performed. Existing duplicate files and historical project records were preserved. Stop after this assignment.
