# Phase 1 sizing — consolidated status after SIZE-C01/C02/C03

Date: 10 November 2026. **Native correction tickets C01/C02/C03: PASS within their scopes. Cross-file acceptance: FAIL/PARTIAL; G1 remains OPEN.** This is a dated addendum, not a rewrite of FV-P1-SIZE-001's historical FAIL report.

All 12 registered methods have explicit native input/output contracts inventoried. The unchanged independent suite now reports **304 passed**, including the three corrected defects' four original assertions and all 36 low/nominal/high numerical examples. This does not convert preliminary screening methods into industrially validated designs. Original implementation references remain SOURCE NOT VERIFIED; primary-source physical-identity cross-checks are separately documented. Accepted FV-P1-UNIT-001 evidence remains unconfirmed.

| Method | Native output | Current numerical/input status | Applicability status |
| --- | --- | --- | --- |
| ion_exchange_capacity | m3 | Independent sample/boundary suite passes | Conditional screening only; not full equipment design acceptance |
| vaporizer_area | m2 | SIZE-C02 corrected at native/adapter boundary; XLS Boolean ingestion gap remains | Conditional screening only; not full equipment design acceptance |
| gas_compression | kW | SIZE-C01 corrected; near-gamma and pressure tests pass | Conditional screening only; not full equipment design acceptance |
| phase_change_duty | kW | Independent sample/boundary suite passes | Conditional screening only; not full equipment design acceptance |
| evaporated_water | kg/h | Independent sample/boundary suite passes | Conditional screening only; not full equipment design acceptance |
| ion_exchange_ebct | m3 | Independent sample/boundary suite passes | Conditional screening only; not full equipment design acceptance |
| vessel_hold_up | m3 | Independent sample/boundary suite passes | Conditional screening only; not full equipment design acceptance |
| pump_duty | 1000 US_gpm_psi | SIZE-C03 corrected; finite outputs/rejection pass; L/s ingestion gap remains | Conditional screening only; not full equipment design acceptance |
| exchanger_area | m2 | SIZE-C02 corrected at native/adapter boundary; XLS Boolean ingestion gap remains | Conditional screening only; not full equipment design acceptance |
| filter_area | m2 | Independent sample/boundary suite passes | Conditional screening only; not full equipment design acceptance |
| gas_volume | m3/h | Independent sample/boundary suite passes | Conditional screening only; not full equipment design acceptance |
| dryer_chamber | m3 | Independent sample/boundary suite passes | Conditional screening only; not full equipment design acceptance |

## Preserved limitations

Ion-exchange contact time/capacity requires resin/species/breakthrough evidence; vessel hold-up requires appropriate process residence/working volume; exchanger/vaporizer area requires phase-appropriate U, driving force and configuration; gas volume/compression requires justified composition/state/property assumptions; filter area is hydraulic screening, not universal cake design; dryer chamber is gas hold-up, not complete particle-drying design; water removal conserves dry solids on a stated moisture basis. Compatible output units alone do not validate a cost-model family or design margin.

## Integration and regression evidence

The active public upload path accepts XLSX/XLSM/XLS only. Actual isolated-worker fixtures feed existing normalisation, engineering registers and the canonical sizing dispatcher. Native row/column cases pass across all three formats. Five failures in the broader matrix expose two separate ingestion gaps: BIFF Boolean type loss (two cases) and unsupported L/s (three cases). Seven other formats are BLOCKED as engineering pathways, with explicit rejection asserted by tests. Model selection and assumption values are explicit test inputs; live AI interpretation is not certified.

Final complete canonical backend: **2305 passed, 5 failed, 3 skipped**, plus **367 passing subtests** and one existing test-client deprecation warning (200.51 seconds). All five failures are new cross-file acceptance assertions; the 2184 previously passing tests remain passing and the original pump failure now passes. The three skips are private Charlie workbook, private Charlie snapshot and optional installed OpenPyTEA reference unavailable. Full logs, file selection and exact failure/skip names are retained under `corrections/SIZE-C03_evidence/`. Native verification is 304/304; this does not hide integration failures or imply industrial design acceptance.

See the three correction reports, the detailed compatibility matrix/report and Engineer 2 handover. No existing project records, original expected results, historical reports or duplicate files were modified/deleted. No push or deployment was performed.

## Recommended next work

Engineer 2 should resolve SIZE-XF01 and SIZE-XF02, reconcile obsolete parser-support documentation, and rerun the unchanged integration tests. Obtain accepted unit-contract evidence and original equation/applicability review before G1 consideration. Do not automatically begin Phase 3 costing implementation; this assignment stops here.
