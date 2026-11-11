# Cross-file equipment-sizing compatibility — SIZE-C03

Date: 10 November 2026. **Decision: PARTIAL compatibility; FAIL on five integration acceptance cases.** This decision is separate from the pump numerical correction. Universal upload compatibility is not established.

## Active pathways inspected

Current Entry controls (`frontend/src/blocks/shared/project-workspace.tsx`, plus the revenue upload view) accept `.xlsx,.xls,.xlsm`. `api.app.upload` enforces those extensions and a 20 MiB bound. Upload stores a new source; it does not itself guarantee calculation success. Both engineering-data and orchestration runs call `orchestration.ingest.parse`, which runs the isolated `ingestion.worker`. The worker uses `balance.workbook.read_book` and `workbook_pipeline.parse_workbook` → `StreamLayoutParser`/generic table adapters → unit interpretation/normalisation → engineering stream/equipment register.

OOXML XLSX/XLSM share the bounded openpyxl reader; XLS uses xlrd's bounded BIFF reader. The source report retains worksheet/cell/header evidence. Equipment descriptions/tags enter the register; they do not constitute an independently validated equipment model choice. With an explicit sizing proposal, `orchestration.sizing.derive_size` → `engineering_sizing.adapter.derive` → `engineering_sizing.registry.calculate` reaches the same registered calculation functions. Gas, thermal, liquid and heat-exchanger conversion bridges also delegate their final calculations to the registry. No second pump/area/compressor equation was introduced.

Current formats are inferred from executable routes, not the historical 17-method scaffold README. PDF engineering tables, Word, CSV, JSON, DWSIM-native, images and XLSB have no active upload pathway here; explicit rejection is tested, and engineering compatibility is marked BLOCKED. Nothing in this audit implements document extraction/OCR or restores old adapters.

## Executed synthetic matrix

Twenty-one synthetic workbooks are retained in `backend/tests/fixtures/sizing_cross_file/`, with hashes under `corrections/SIZE-C03_evidence/fixture_manifest.json`. A regeneration script uses existing test dependencies. Files contain no customer data, formulas, external links or executable macros. XLSM has a macro-enabled workbook content type but no VBA payload. This does not certify arbitrary macro-bearing workbooks.

Cases include two worksheets, records in rows and columns, merged title cells, explicit equipment tags/descriptions, alternate headings/units, signed duty, Python-typed Boolean source cells, omitted duty units, gauge pressure and an explicit atmospheric-pressure assumption. This samples layouts; it does not certify every merged engineering header, simulator export or formula-cache arrangement.

Numerical references are independent: compressor near-gamma limit 82.33066173777114 kW (parent Decimal reference); pump hydraulic power 0.1 kW and shaft power 0.2 kW, coordinate 0.22988950107343336 in 1000 US_gpm_psi; exchanger area 10 m²; vaporizer area 12.5 m². Pump differential pressure/efficiency, gas MW/gamma/efficiency/discharge pressure and thermal U/LMTD/F are explicit synthetic engineering assumptions, not invented workbook facts or LLM output. Operating pressure is not substituted for pump differential pressure.

The integration tests run the actual isolated parser worker and existing sizing dispatcher. They do not invoke AI model selection, a browser or persistent live project APIs. A source-backed sizing calculation is not a proof of complete equipment design or successful autonomous extraction of every assumption.

Matrix result: **55 PASS, 5 FAIL, 7 BLOCKED** (67 rows). The passes comprise 33 equivalent-input calculations plus three gauge-basis calculations and 19 correct rejections; they are not 55 priced equipment items. Pytest result: **62 passed, 5 failed**; the seven unsupported-format rejection tests pass as negative tests but remain BLOCKED as engineering pathways. Six missing-unit cases and overflow cases count as passing rejection checks, not computed equipment prices.

- Native-unit row/column calculations pass for all four methods across XLSX/XLSM/XLS.
- Equivalent mass-flow, temperature, absolute-pressure and duty units pass for compressor and thermal cases.
- Gauge pressure is refused without an atmosphere; explicitly supplying 1 bar atmosphere reproduces the independent compressor reference. It is an explicit test assumption, not a default guessed by the engine.
- Pump overflow is rejected after every supported file reader.
- XLSX/XLSM Boolean duties remain unresolved/rejected.
- Two XLS True-duty cases fail because the reader loses Boolean type before the guard.
- Three L/s pump cases fail because that ingestion unit is unsupported and remains unresolved.

Full row-level source/normalisation/calculation evidence is in `cross_file_compatibility_matrix.csv`. NumPy bool/float/int and Decimal/Fraction scalar behaviour is additionally covered by unchanged SIZE-C02 tests at the native/adapter boundary; Excel serialisation does not preserve NumPy scalar identity.

## Ownership and remaining limits

See `cross_file_engineer2_handover.md` for SIZE-XF01 (XLS Boolean type loss), SIZE-XF02 (L/s ingestion capability), reproduction cells, failing tests and expected interfaces. No Engineer 2 architecture was modified. The initial test-author probe mistakenly read pump audit metadata at the top level instead of under `calculation`; that test harness mistake was corrected before final results. It is not a production defect. Its separate initial log is retained, with final logs clearly identified.

The pump correction and native SIZE-C01/C02 checks can pass while cross-file compatibility remains incomplete. Missing original method provenance, full equipment applicability evidence and accepted FV-P1-UNIT-001 evidence remain open; neither this matrix nor a successful parser run passes G1.
