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

Entry includes a **Select file type / import source** dropdown. Excel workbooks and Excel-export paths are offered for Aspen Plus, Aspen HYSYS, DWSIM, UniSim, CHEMCAD, PRO/II, gPROMS, SuperPro Designer and other software/Python/MATLAB outputs. Selecting a simulator is guidance about the source, not a claim of native-file or universal export-layout support; the same bounded Excel parser validates the actual uploaded tables. CSV/JSON, native DWSIM and BioSTEAM choices link to the existing Simulation data importer with their format restrictions. PDF/Word, scanned images/PFDs and description-only inputs are labelled unsupported for numerical extraction, with instructions for preparing Excel tables. The dropdown remembers the choice in this browser tab and does not populate any project data.
