# Engineer 2 handover — SIZE-C03 cross-file audit

10 November 2026. No ingestion, schema, orchestration or persistence code was modified by Engineer 1. These findings are separate from the resolved pump finite-output defect. Do not remove or xfail the new integration assertions.

## SIZE-XF01 — HIGH: legacy XLS loses Boolean cell type

Path: `ingestion.balance.workbook.read_book` → XLS branch using xlrd → `Cell` construction → canonical parser/unit conversion → engineering adapter. The reader preserves numeric `v.value` for `XL_CELL_BOOLEAN` instead of retaining a Python bool. A True cell becomes 1; downstream code has no remaining type information with which to reject it.

Reproduction fixtures: `backend/tests/fixtures/sizing_cross_file/rows_bool_true.xls` (ordinary BIFF workbook, no macros/customer data). H-IN heat duty is a genuine Boolean cell at Balance!E7 under Heat duty (W). After reading, evidence has original_value=1 and normalized_value=0.001 kW. Exchanger sizing produces **0.0001 m²**; vaporizer area with its supplied U/LMTD/F produces **0.00005 m²**. Both should reject a Boolean heat duty. XLSX/XLSM equivalents retain/reject the Boolean successfully. False becomes numeric 0; area rejects zero, but that does not establish preservation of the Boolean type.

Failing tests: `test_boolean_heat_from_file_must_not_be_costed[exchanger_area-True-xls]` and `[vaporizer_area-True-xls]` in `backend/tests/test_sizing_cross_file.py`. SIZE-C02's direct/registry/source-adapter guard is still correct when the Boolean type reaches it; an upstream conversion bypasses that contract.

Required interface: preserve BIFF Boolean type through Cell/evidence; unit conversion must leave it unresolved rather than interpreting it as measured power. Retain cell provenance and explicit validation reasons. Check Boolean preservation across other numerical properties as well. Engineer 1 has not applied a guessed downstream numerical filter: legitimate 1 W measurements must remain valid.

## SIZE-XF02 — MEDIUM: L/s volume-flow unit not supported at ingestion boundary

Fixtures: `rows_units.xlsx`, `.xlsm` and `.xls`. P-IN at Balance!D6 is 1 L/s, physically equivalent to 3.6 m³/h. Header is Volumetric flow (L/s). Ingestion's unit table lacks L/s; unit recognition records `l` and normalisation correctly remains unresolved. The dispatcher cannot obtain a supported volume flow and refuses to size the pump. It does not silently substitute a wrong value.

Failing tests: three `test_equivalent_real_workbook_inputs[pump_duty-...-rows_units-<format>]` cases. This is a documented unit capability/interface gap, not a pump equation defect. Native m³/h cases in both row and column layouts pass across all three formats.

Required interface: agree support for L/s, preserve the complete declared unit token (including /s), and independently verify 1 L/s → 3.6 m³/h. Until implemented, keep the quantity unresolved with the full original label visible. Do not weaken the physical-equivalence assertion or pretend an unresolved unit has been validated.

## Documentation drift

The active checkout has no `backend/app/parsers/inputs/README.md` or `frontend/src/lib/import-methods.ts`. `backend/ingestion/inputs/README.md` retains older references to 17 stubs and historical CSV/JSON/DWSIM/BioSTEAM paths. Current UI/API/worker accept only XLSX/XLSM/XLS. Reconcile the documentation with actual routes before claiming those other formats are supported; this audit did not restore or implement them.

## Evidence and ownership

The matrix records source labels, original/normalised observations, units, explicit test assumptions, selected method, results and error messages. Fixtures and a regeneration script are retained; worker parsing is genuine and isolated, with no AI calls. Method selection/engineering parameters in these tests are explicit test inputs, not an evaluation of AI judgement. Existing canonical numerical methods remain the calculation endpoints. Repairing these ingestion issues belongs to Engineer 2, followed by this unchanged integration matrix and the full backend regression suite.
