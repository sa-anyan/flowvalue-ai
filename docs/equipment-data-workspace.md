# Equipment data workspace

The Engineering Data navigation opens `/data/equipment`; `/data` remains compatible. The same modular explorer is available on the Equipment costing page, keeping source data close to configuration and cost decisions.

The workspace has a searchable, status-filtered equipment/stream directory and a single selected-record inspector. Summary counts describe the extracted register. Connections, Properties, Components and Evidence are separate views; unrelated stream records are not expanded into a long page. Lists and observations scroll vertically within bounded panels. Cards wrap instead of requiring horizontal table scrolling, including at mobile widths.

Connection lines represent existing register associations only: no direction, physical process sequence or balance validation is inferred. Clicking an associated record opens its own inspector. Equipment observations and associated stream observations retain distinct labels; stream properties are not presented as equipment design capacities. Evidence exposes original and normalised values, units, worksheet/cell, workbook, interpretation, formula when present and status. Source verification is not presented as whole-plant validation.

The existing costing assumptions, source reports, specialist reviews, research permissions and scenario/version controls remain accessible. Long ancillary reviews are collapsed by default. This change is frontend presentation only; parsing, calculations, saved results and engineering connections remain unchanged.

## Verification — 2 November 2026

Read-only browser checks use the founder's saved assessment `2f2c8ed1d44e49dba0d73d965e81659b`. Equipment selection, both registers, all four inspector views, source evidence, associated-record navigation, search/reset, dark mode and absence of horizontal page/inspector overflow at 1440 px and 390 px passed. No paid AI calls or saved-model mutations were made. Screenshots and checks are retained in ignored `outputs/equipment-data-ux/`.
