# Excel engineering ingestion: repeated stream blocks and source review

The canonical path remains `orchestration.ingest` → isolated worker →
`workbook_pipeline.parse_workbook` → `StreamLayoutParser` → engineering registers.
No simulator script, macro, external link or workbook formula is executed.

## Layout handling

`repeated_stream_blocks.py` recognises repeated stream identifiers above groups
of explicit mass/molar flow subheaders and shared component rows. It supports the
Nottingham Charlie arrangement without relying on its filename, sheet name,
stream numbers or equipment names. The existing generic horizontal/vertical,
long-form, irregular and M&E8 adapters remain available for other regions.

Reference MW/standard-enthalpy columns outside stream groups do not become
streams. kg/hr and kmol/hr subheaders attach to their own columns. Component
flows, mole/mass fractions and explicit totals remain distinct. Blank separator
rows do not hide later temperature, pressure or enthalpy-flow observations.
Every value retains its original cell, headers, units and cached-formula status.
Missing units/caches remain unresolved; conservation is not assumed from a
successful extraction. Additional unsupported physical properties remain in the
source inventory for source-backed AI review, not invented measurements.

Equipment tags accept up to three trailing letters, including AB. The register
uses all available descriptions per sheet/case, recognises common unit names,
and reads leaving/from/entering/to wording for source-backed inferred links.
Base tags and AB variants are not automatically two independent units: alias
issues require confirmation before both are costed. Missing descriptions and
service conflicts remain explicit. A named unit is not automatically sized or
matched to a validated cost model.

## AI review

`orchestration.workbook_review.review_contexts` partitions stored source cells
into bounded regions, supplies exact identity/header dependencies and a global
register-key manifest, and includes relevant Python observations. AI reviews each
region, corrects semantic associations using real cell references and searches
for omitted records. Python independently reads every proposed numeric value and
runs dimensional conversion. AI does not supply replacement numbers or equations.

Successful batches are applied incrementally and cached; a failed batch does not
erase successful work. Metadata records reviewed/unreviewed regions, unique
source-cell coverage, cache use and truncated inventories. "Reviewed" indicates
AI interpretation, not independent engineering verification. Source inventories
beyond the existing 12,000-cell limit are explicitly partial. Other archive,
cell/sheet/property, worker time/memory and output bounds remain active.

Source data and original Python extraction are preserved. The UI takes the most
recent reviewed equipment type and the calculated sizing record when available,
while missing dimensions continue to display as missing. Users should upload a
new assessment to use the new extraction; old baselines are not rewritten.

## Checks and boundaries

Automated synthetic Nottingham-style tests exercise repeated blocks, nested
headers, reference-column exclusion, blank separators, mass/molar flows,
fractions, pressure, enthalpy flow, AB tags, equipment types and graph links.
Source-review tests check complete supplied-cell coverage under context bounds,
partial failures and baseline preservation. Existing parser/engine tests remain
required regression checks.

Real-workbook before/after extracts, original test copies, runtime summaries and
AI review artifacts are saved privately under ignored `outputs/parser-rewrite/`.
Template variants with images instead of cells, ambiguous units, absent formula
caches, different unsupported layouts or excessive resource use may require
review. This implementation does not promise universal Excel compatibility.
