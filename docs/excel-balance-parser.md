# Excel mass and energy balance intake

This increment adds engineering workbook parsing and a compact process-description comparison on the existing `/entry` page. It does not size equipment, update the economic model, generate a PFD or reconstruct missing engineering data. Existing CSV/JSON/DWSIM imports and all other pages remain available.

## Supported structures

- `.xlsx` OOXML workbooks, read with openpyxl in formula and cached-value modes; `.xls` OLE/BIFF workbooks read with xlrd 2.0.2.
- Multiple worksheets, including hidden worksheets, and separated tables on a worksheet. Side-by-side tables with separate identifier headers are segmented.
- Records in rows (`Stream ID | Mass flow [kg/h] | …`) or records in columns (`Stream ID | Units | S1 | S2`, followed by property rows).
- Long property tables (`Stream ID | Property | Units | Value`). Repeated identifiers in this layout group their observations; missing IDs are not automatically carried forward.
- Merged heading cells and shared merged property headers. Units may be in property labels or a separate header row/units column. Numeric values in percent-formatted Excel cells retain their stored fractional scale.
- Explicit material/energy stream identifiers and equipment tags; name-only equipment ledgers are marked provisional. Common aliases include Stream number/no., source/from, destination/to, inlet/outlet streams, temperature/temp, pressure, mass/molar flow, vapor/vapour fraction and heat/work/power labels.
- Explicit case/scenario columns preceding a stream identifier, so separate operating cases are not summed together. Cross-sheet repeated observations are retained, with conflicts exposed rather than choosing a winner.

The unit registry converts supported mass/molar/volume flows, temperature, pressure, density, specific enthalpy, enthalpy flow, heat/work/power, concentrations, fractions, volumes, areas and lengths. Canonical bases include kg/h, kmol/h, degC, bar_abs or bar_gauge, kW and kg/m3. Gauge pressure is **not** converted to absolute using an assumed atmospheric pressure. Unsupported or ambiguous units retain their source label and have no normalized value. Bare component names without a declared composition basis remain unresolved.

Every extracted observation stores filename, sheet/cell, supporting header/unit cells, source value/unit, formula text where available, cache indicator, normalized value/unit, interpretation and status. A SHA-256 fingerprint identifies the input file. Downloaded parsed evidence includes all records/issues even where the UI displays a bounded preview.

## Meaning of status and validation

- **Verified:** a directly supported source observation with a supported interpretation, or the specifically named deterministic arithmetic check. This does not validate plant design, prove measurement quality or certify workbook completeness.
- **Inferred:** source-declared synthetic/inferred/unverified data, name-only equipment identifiers, formula caches, legacy `.xls` stored results or AI description mappings requiring confirmation.
- **Unresolved:** missing/invalid values, unknown units/bases, conflicting observations, missing connections or insufficient prerequisites.

Implemented checks include invalid/non-finite/ambiguous numbers; negative non-signed flows and invalid temperature/absolute pressure/fraction ranges; phase labels; missing/duplicate identifiers; conflicting properties/declarations; composition sums; absent endpoint equipment; equipment inlet/outlet assertions that conflict with stream endpoints; missing formula caches and formula errors (also outside recognized tables).

Overall mass closure requires an explicit workbook declaration such as `Mass balance basis | steady state; complete boundary`, explicit inlet/outlet/internal classifications for all material records in the case, unique IDs and confirmed compatible flows. Component closure additionally requires complete explicitly based component flows/fractions and `Component balance basis | nonreacting`. Reaction generation/consumption is not guessed. Arithmetic uses relative tolerance 1e-4 and absolute tolerance 1e-6, with residuals and participating evidence IDs returned.

Energy closure additionally requires `Energy balance basis | steady state; complete boundary; kinetic and potential negligible; common enthalpy reference`, `Energy sign convention | positive into boundary`, complete material enthalpy-flow observations and explicitly directed heat-added, heat-removed, work-in and work-out terms, including known zeroes. Directed terms require non-negative magnitudes. Missing terms, signed ambiguous duties or electrical load ledgers alone cannot establish closure. No enthalpy is synthesized from temperature, composition or a natural-language description.

These are declarations in the source, not inferred physical facts. Conflicting declarations disable the relevant check. Transient balances, accumulation, reaction species generation and arbitrary control volumes need additional supported inputs/methods and remain unresolved here.

## Description dialogue

Text is editable and associated with the current attachment. Changing text or replacing the workbook invalidates previous comparison results. **Basic tag check** makes no AI call. **Compare with AI** uses the existing server-side AI configuration and OpenAI structured outputs; one bounded request on click, no web search or tools, `store=False`.

Only description text and extracted names/types/tags/endpoints reach the provider, not the workbook, cell formulas, numerical balance values, economic data or credentials. The provider can return existing-tag pairs with exact description excerpts and unresolved excerpts. Server checks reject unknown tags and fabricated quotes, then deterministic code compares pairs with workbook endpoints, reports agreement/reverse-direction contradiction/missing connections, and asks short clarification questions. No model-generated engineering values, new entities or graph edits are accepted. Agreement remains advisory and does not override synthetic/unverified source quality. AI errors/disabled configuration retain both inputs; basic checks remain available.

## Storage and safeguards

The existing project snapshot now has an optional `balance_import` attachment, separate from the financial `project`, canonical CSV streams and native DWSIM import. Browser drafts and authenticated Save revision/load retain the report and description. Existing ownership/RLS and versioning endpoints are reused without schema, sharing or permission changes. The existing 2 MB saved-project snapshot cap remains; oversized reports can be downloaded and split. Raw uploads are temporary server files removed after parsing, not persistent cloud file storage.

Limits: 4 MiB upload; 40 sheets; 10,000 rows and 256 columns per sheet; 150,000 scanned cells; 300 detected tables; 1,500 records; 5,000 extracted observations; 256 observations per record; 2,000 issues/checks. Archive expansion is bounded to 40 MiB total/20 MiB per member, 2,048 members and compression ratio 1,000. Duplicate archive members, XML DTD/entities, macros and oversized ranges/styles are rejected. No formula evaluation, external-link refresh, embedded-code execution or uploaded-code import. Parsing runs in a short-lived killable worker with 25-second wall time, 20-second CPU and 512 MiB address-space limit on Linux; one parse worker at a time. Worker environment excludes application secrets. A busy parser returns 429; malformed/over-limit input returns 422/413 and preserves the previous import.

## Verification artifacts and limits

Synthetic workbooks are retained under `backend/tests/fixtures/balance/`. Tests also save parsed JSON and rejected/oversized test inputs under the ignored private `outputs/balance-parser-tests/` folder. The local Protein-from-Air engineering test workbook and its parsed report are copied there; its source file remains unchanged and is not committed or made a public application default. It separates documented equipment/load ledgers from synthetic streams and inferred routing: those caveats are retained. It is not an independently validated industrial process benchmark.

Unsupported/unresolved examples: image-only tables, PFD/P&ID drawings, embedded objects, macros, external workbook refresh, Power Query, `.xlsb`/`.xlsm`/ODS/renamed HTML/XML, encrypted files, locale-ambiguous numeric text, unsupported units/aliases/languages, arbitrary multi-level headers, headerless matrices, unspecified composition bases, implicit flow directions, arbitrary case layouts, and formula results without caches. `.xls` formula text and cache freshness are unavailable and all stored results require confirmation. No universal Aspen/HYSYS/DWSIM compatibility is claimed; an export is supported only to the extent its actual Excel cells match recognized structures. Unclassified sheets and unmapped headers are reported, and coverage is always labelled partial.

Sources: [openpyxl workbook reader](https://openpyxl.readthedocs.io/en/stable/api/openpyxl.reader.excel.html), [xlrd reader API](https://xlrd.readthedocs.io/en/stable/api.html), [OpenAI structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs).

## Import-source selector

Entry includes a **Select file type / import source** dropdown. Excel workbooks and Excel-export paths are offered for Aspen Plus, Aspen HYSYS, DWSIM, UniSim, CHEMCAD, PRO/II, gPROMS, SuperPro Designer and other software/Python/MATLAB outputs. Selecting a simulator is guidance about the source, not a claim of native-file or universal export-layout support; the same bounded Excel parser validates the actual uploaded tables. CSV/JSON, native DWSIM and BioSTEAM choices now invoke the existing format-specific handlers directly from Entry, with matching file filters and a stream preview. They remain separate from Excel cell evidence and do not establish balance closure. PDF/Word, scanned images/PFDs and description-only inputs are labelled unsupported for numerical extraction, with instructions for preparing Excel tables. The dropdown remembers the choice in this browser tab and does not populate any project data.

## Future input-specific parser scaffolds — no new implementations

The 17 Entry dropdown methods now each have a separate, deliberately non-executable Python placeholder in [`backend/app/parsers/inputs/`](../backend/app/parsers/inputs/README.md). These stubs are **not wired into the Excel balance intake, the import API or the UI**. They exist so each simulator/export/document/text pathway can be researched, specified and validated individually. Existing working parsers (`stream_parser.py`, `balance/`, `dwsim_parser.py`) are unchanged; PDF/Word/scanned files remain unsupported.


## Aspen HYSYS adapter — independent canonical extraction (2026-10-28)

Selecting **Aspen HYSYS** in Entry now transmits the source identifier `aspen-hysys` with an Excel upload. The existing bounded, killable Python worker dispatches that selection to `backend/app/parsers/inputs/aspen_hysys_excel.py`. All other Excel selections still use the generic workbook parser. The response remains the same **`flowvalue-balance-v1`** canonical `BalanceReport`, including source filename, SHA-256, stream identifiers, per-value sheet/cell/unit provenance, normalized supported quantities, issues and review state. No report styling, equipment costs, financial calculations, AI inferences or process diagrams are added.

The dedicated adapter independently recognises a property/units/stream-column matrix (for example `Property | Units | S-101 | S-102`) by headers and property groups rather than fixed row positions. It extracts supported phase, temperature, pressure, density, mass/molar enthalpy, total mass/molar flow and **component mass/molar flows only when the flow section and units explicitly establish the basis**. Unit normalisation is delegated to FlowValue's existing registry, without guessing unknown unit or pressure conventions. Unrecognised rows are reported; incomplete or unsupported data does not become a complete mass/energy balance. Where no HYSYS signature is found the generic parser may still extract standard tables, but the result explicitly flags the unmatched HYSYS layout.

**Third-party research/reference:** [Mo-Somji/HYSYS-ME-Balance-Formatting](https://github.com/Mo-Somji/HYSYS-ME-Balance-Formatting) and its [raw HYSYS reference export](https://github.com/Mo-Somji/HYSYS-ME-Balance-Formatting/blob/main/Data/Raw_Data_Input.xlsx) and [formatted result](https://github.com/Mo-Somji/HYSYS-ME-Balance-Formatting/blob/main/Outputs/Results.xlsx). The repository did not display a licence when inspected. **No source code, workbooks or sample data from that repository were copied into FlowValue.** The FlowValue adapter is independently written and has its own synthetic regression fixtures. Permission or an explicit licence should be obtained before reusing their code or redistributing their workbooks.

Current acceptance limits: HYSYS exports vary; this adapter handles only the recognised tabular layout, does not evaluate Excel expressions or infer absent component mass balances, and does not validate simulator convergence. Real reference data has not yet been independently benchmarked in an authorised test environment, so compatibility with that exact source workbook is **not confirmed**.


## Entry source confirmation and sample files

The Entry importer now uses a **select → sample preview/download (optional) → Lock in → upload** flow. Choosing a different source unlocks the selection so an incompatible file is not accidentally sent to the previous parser. The locked choice is remembered in this browser tab; sample download is optional. The in-app preview shows representative fields and the download offers the full file.

Sample links follow existing, actual test/reference files:
- **Generic Excel:** copy of FlowValue's synthetic tested simple.xlsx fixture, available at /examples/excel-balance-sample.xlsx.
- **CSV/JSON:** synthetic canonical stream-table examples.
- **Native DWSIM:** synthetic .dwxml parser fixture at /examples/dwsim-native-sample.dwxml.
- **BioSTEAM:** water-heating demonstration JSON.
- **Aspen Plus, Aspen HYSYS, DWSIM Excel, UniSim, CHEMCAD, PRO/II, gPROMS, SuperPro and other Excel origins:** clearly labelled **generic Excel example**, **not** a vendor-specific template or compatibility guarantee. The HYSYS adapter has independently authored synthetic tests but no published HYSYS-specific workbook yet.

The PDF/Word, scanned-image/PFD and manual-description selections have no numerical file sample because file extraction is unavailable. Locking one of them shows the limitation; manual context can still be supplied in the process-description box.

These files are examples and parser fixtures: the parsers are **rule-based, not machine-learning models trained on these files**. Sample availability does not prove industrial validation, balance closure or full vendor support. No unlicensed third-party workbook is redistributed.


## Contextual help on Entry

Long explanatory copy in the Entry mass/energy balance intake is presented via small question-mark disclosures rather than permanent paragraphs. Pointer hover reveals the explanation; activating the disclosure by click, tap or keyboard toggles it. Source-specific requirements, sample notes, preview limitations, parser-design disclaimers, AI data-sharing details, evidence storage notes and the meaning of validation status remain available without crowding the entry form. Upload constraints, unsupported status, active processing state, errors, missing data and engineering validation results continue to display prominently. This is a presentation-only change; no parser, validation or provider behaviour is altered.

### XLSM description parser (28 October 2026)

The founder-supplied `flowvalue_smart_meb_parser.py` is preserved byte-for-byte as
`backend/app/parsers/inputs/xlsm_parser.py`. Production calls its `parse_sheet`
and `classify` functions through `xlsm_adapter.py`, using the bounded existing
openpyxl reader instead of the script's unavailable `artifact_tool` loader or
its disk-writing CLI. `.xlsm` uploads use this adapter regardless of simulator
selection. Macros and external links are never executed/refreshed.

This route identifies numeric stream labels and equipment tags in adjacent or
inline stream descriptions. It does not extract numerical balances, infer
untagged equipment, establish connections, or size equipment. Classification
remains inferred; ambiguous types and missing equipment require manual review.
Source description cells are retained in the canonical report. Other Excel
formats retain their existing paths. Tests cover tagged equipment, source
cells, ignored macro payloads/formulas, malformed uploads and isolated-worker
integration. No claim of complete engineering workbook extraction is made.

### XLSM stream inventory update

XLSM parsing now retains each detected stream as a material record even when
its description has no equipment tag. Repeated descriptions in distinct source
cells are preserved rather than deduplicated away. No equipment is invented
for untagged streams; the properties UI groups these as Unassigned, with sheet
identity retained. Per-stream properties are cached for reuse across equipment
mentions; row-label indexes are built once per sheet. No extra workbook reads,
AI calls or formula execution were added. Existing limits still apply. This
extends supported description tables, not arbitrary spreadsheet recognition.

Team 8 acceptance: 14 stream records on Mass and Energy Balance (including
13/14), plus 18 separately sourced records on Energy calculation. These sheets
must not be interpreted as one validated process. Local whole-workbook parsing
remained about 1–1.5 seconds; timing varies, and no strict no-slowdown guarantee
is made for the larger output. Component-total reconciliation remains separate.

### Workbook pipeline v2

The web worker now uses `workbook_pipeline.parse_workbook` for generic Excel
(including XLSM). It reads the workbook once, detects description stream
blocks, applies canonical row/column/long-form recognition on other sheets,
retains stream/component evidence, interprets explicitly tagged directional
clauses, and builds a worksheet-scoped equipment register. Explicit HYSYS
exports retain their dedicated adapter. Uploaded scripts/macros never run.

Subcolumn spacing is discovered from unit headers within each stream block;
no fixed five-column mass-flow offset is required. Missing volume entries do
not hide component mass entries. Component-total mismatches and workbook
error cells are surfaced as review issues, not silently corrected. Comparison
of stored component sums is not plant mass-balance verification.

Limitations: description-block and generic adapters are not yet combined
within a single worksheet. Numeric IDs are supported by the description-block
adapter; canonical adapters support other explicit IDs. Unsupported layouts,
unnamed streams, untagged equipment, ambiguous wording, absent units and
unavailable formula caches remain unresolved. No universal compatibility
claim is made. Sheets are not automatically assumed to describe one process.
Generic validation checks remain scoped to their source sheets and precede
register interpretation; missing-endpoint warnings require operator review.

Team 8 regression: 14 main-sheet streams plus 18 on Energy calculation,
7 tagged equipment items, and both 100 kg/h component-total discrepancies.
Whole-workbook local timing is approximately 2 seconds with broader extraction
and checks, not a guarantee for arbitrary workbooks. Test inputs and parsed
real-workbook evidence are retained under the private ignored outputs folders.


### Current stream-centred engine (v3; review branch, not deployed by this task)

See [engineering review](parser-v3-engineering-review.md) and
[raw benchmark records](parser-v3-benchmarks.json). Region-level adapters now
coexist on one worksheet; scoped stream/equipment keys and explicit connection
records replace numerical property copies. The generic worker and compatibility
XLSM function use one engine. Earlier v1/v2 notes above are historical.
