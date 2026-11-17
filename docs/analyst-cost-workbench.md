# Analyst cost-driver workbench

Implemented locally 17 November 2026 as a read-only presentation layer on saved calculation records. This does not add engineering costing methods, a construction-ready bill of materials, or an estimate accuracy class.

The guided Equipment, CAPEX, OPEX and Revenue pages now include:

- Area-proportional composition maps and ranked drivers, with category-to-record drill-down and breadcrumbs.
- Pareto/concentration views for non-negative known amounts, with an explicitly labelled 80% reading guide. Signed credits use the waterfall or ledger.
- Contribution waterfalls from zero, showing the saved parent separately from the sum of known child contributions.
- Searchable exact-value ledgers, record inspection, saved formulas, bases, quantities/rates, currency/date, sources, rationale and uncertainty where present.
- Parent-versus-child reconciliation and visible unresolved scope. A matching priced subtotal does not establish full physical scope coverage.
- OPEX operating-year selection and grouping by category, fixed/variable behaviour or method. Non-cash and financing entries remain outside cash OPEX.
- Separate monetary bases for Equipment and separate saved-versus-unapproved-preview identification for Revenue. Avoided OPEX is not included as income.
- A chart-record CSV containing paths, IDs, original saved decimal amounts, project/revision, status and source records. Group totals are labelled display aggregations; this extract is not the economic workbook/report. Formula-like text is neutralised for spreadsheet opening.

CAPEX uses the engine's declared `breakdown` and `counted` flags. Combined/embedded rows remain available as accounting evidence but are not charged again. Purchased-equipment and source-defined unit-capital records retain their different costing bases. Legacy outputs without an additive breakdown expose only their three distinct capital components.

## Detail limits

A piping fraction of purchased equipment is an allowance, not a count of pipes, valves, supports or bolts. An equipment correlation is not a verified fabrication/component take-off. The workbench stops at the finest saved record and labels that boundary. Bolt-level accounting requires a separately supplied and validated quantity take-off/BOM contract and independently reconciled pricing; no parser or take-off capability is implied by these visuals.

## Verification

66 focused frontend checks passed (including ten new cost-exploration regressions). Source TypeScript passed with duplicate demo-build output globs excluded; the existing generated-type issue in the standard typecheck configuration was not changed. New cases cover blank/zero/signed values, incomplete grouped descendants, CAPEX embedded/alias exclusions, selected OPEX years and cash scope, pending revenue, area proportions, Pareto eligibility, export lineage and separate equipment scopes/bases.

Browser checks on the existing local saved assessment verified capital category/factor inspection, pricing formula/base/rationale display, composition/Pareto/waterfall/ledger rendering, OPEX year/behaviour selection, quantity/rate/source inspection, Equipment/Revenue reconciliation, and narrow-screen containment. The browser-produced CAPEX CSV contained 42 records and retained the original decimal amount, project ID, revision and source JSON. No prices/assumptions were edited or saved for QA; no research requests or new economic-engine code were introduced. This does not revalidate the engineering accuracy of the underlying saved assumptions.
