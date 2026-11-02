# Current assessment dashboard restoration

The current assessment frontend reuses the original FlowValue forest-green, sage and neutral visual language from `checkpoint-before-costing-rebuild-2026-10-29`. The legacy frontend is a design reference, not a replacement for the current API contracts or calculation engines.

The shared shell covers Entry, TEA overview, Engineering data, Equipment, CAPEX, OPEX, Revenue and Financial Model. It includes persistent light/dark preference, responsive navigation, visible current-page state and keyboard focus. Entry retains the explicit process and revenue descriptions, AI consent, and saved-scenario re-evaluation. Excel drag/drop uses the existing upload endpoint.

`workspace-visuals.tsx` renders only saved calculation values: cumulative/annual project cash flow, capital allocation, equipment purchase costs, annual operating cost categories and payment-method revenue. Missing values are not substituted with zero. Chart interactions change the view, never the engineering assumptions. Monetary values continue to come from existing Python results with their saved currency/date basis.

Detailed tables support text filtering, numeric/text column sorting and CSV export of visible rows. Formula-like CSV text is escaped. Assumption edits, audit rationale, source evidence, research consent, reports and scenario history retain their existing workflow. Saving assumptions still requires the explicit recalculation action.

Historical modules absent from this clean rebuild (such as the old process visualisation or sensitivity engine) are not restored as nonfunctional navigation entries. No backend engine calculations changed in this restoration.

Browser verification uses the saved M&E8 assessment without rerunning AI or external research. QA screenshots and checks are retained under ignored `outputs/dashboard-restoration/`.

## Verification — 2 November 2026

- TypeScript check and Next.js production build passed.
- Headless browser checked the expected title, active navigation, rendered assessment and absence of page-level horizontal overflow on all eight current stages.
- Annual/cumulative chart toggle, keyboard point inspection, table filtering and light/dark toggle passed.
- Entry checked at 390 px, including the dedicated revenue-description field.
- No paid AI/research actions or baseline edits were triggered by this verification.
