# FlowValue — input-specific Python parser scaffolds

**Status (28 October 2026): placeholders only.** This directory has one Python module for each of the **17 exact input method IDs** defined in `frontend/src/lib/import-methods.ts`. The code files intentionally contain only a module header and five numbered TODO sections; there are **no parsing functions, imports, registrations, UI changes or new upload endpoints**. Work through and implement each input method separately with the founder.

## One module per Entry selection

| UI input method ID | Planned Python module | Existing behaviour to preserve |
| --- | --- | --- |
| `excel` | `excel_workbook.py` | Existing `app.parsers.balance` and isolated `excel_service/excel_worker` |
| `csv` | `csv_stream_table.py` | Existing `app.parsers.stream_parser.parse_csv` |
| `json` | `json_stream_table.py` | Existing `app.parsers.stream_parser.parse_json` and project validation |
| `aspen-plus` | `aspen_plus_excel.py` | Generic Excel; no Aspen-specific importer yet |
| `aspen-hysys` | `aspen_hysys_excel.py` | Generic Excel; no HYSYS-specific importer yet |
| `dwsim-excel` | `dwsim_excel.py` | Generic Excel; no dedicated DWSIM Excel importer yet |
| `dwsim-native` | `dwsim_native.py` | Existing `app.parsers.dwsim_parser.parse_dwxml` |
| `unisim` | `honeywell_unisim_excel.py` | Generic Excel; no UniSim-specific importer yet |
| `chemcad` | `chemcad_excel.py` | Generic Excel; no CHEMCAD-specific importer yet |
| `pro-ii` | `pro_ii_excel.py` | Generic Excel; no PRO/II-specific importer yet |
| `gproms` | `gproms_excel.py` | Generic Excel; no gPROMS-specific importer yet |
| `superpro` | `superpro_designer_excel.py` | Generic Excel; no SuperPro-specific importer yet |
| `biosteam` | `biosteam_snapshot.py` | Existing trusted BioSTEAM snapshot ingestion; uploaded Python scripts are never executed |
| `other-excel` | `other_software_python_matlab_excel.py` | Generic Excel; no arbitrary Python/MATLAB code execution |
| `documents` | `pdf_word_engineering_report.py` | Not supported; this module does **not** add PDF/Word parsing |
| `images` | `scanned_table_image_pfd.py` | Not supported; this module does **not** add OCR/PFD interpretation |
| `manual` | `manual_natural_language.py` | Supplementary text context, not a verified balance parser |

## Future implementation contract (not implemented)

1. **Input format and acceptance:** agree samples, formats, file limits, content provenance and failure cases.
2. **Extraction and safety:** bounded resources; do not run uploaded scripts, macros, untrusted native simulation files or model-generated code.
3. **Canonical stream/balance mapping:** map supported observations to the existing `app.parsers.stream_parser` models and/or `app.parsers.balance.models` without inventing mass/energy data, units or equipment.
4. **Validation and user review:** transparent missing and conflicting values, source references/cells, interpretation and independent validation.
5. **Fixtures and acceptance tests:** use real representative exports plus safe synthetic and negative fixtures before promoting a method to implemented.

**No automatic delegation:** the Entry selector currently chooses its existing Excel/simulation/unavailable pipeline. These empty modules are not imported or referenced by that production path. Do not change it until the user chooses the specific parser to implement and tests establish safe equivalence.
