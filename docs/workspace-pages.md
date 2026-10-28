# Analyst workspace pages

This content move preserves the existing Entry, Main dashboard and Process Visualisation work and the existing public URLs.

| Page | Content |
|---|---|
| `/entry` | Existing uploads, stream data, project context and base assumptions |
| `/main-dashboard` | Existing six headline metrics and three summary charts |
| `/dashboard` | Analyst workspace: design basis, evidence, AI connection, engineering reference and release checks |
| `/capex` | CAPEX parent route opens the Summary dashboard; nested child links expose equipment, capital cost categories, assumptions and validation |
| `/opex` | Fixed/variable operating assumptions, operating ledger, coverage and explicit reviewed OPEX application |
| `/revenue` | Product pricing, capacity/utilization and policy/production-credit scenarios |
| `/scenario` | Market advisor, cash flow, uncertainty chart and executive memo |
| `/sensitivity` | Interactive financial sliders, tax assumptions and tornado sensitivity chart |

CAPEX/OPEX/Revenue are under Analyst Workspace; Scenario and Sensitivity remain under Playground. Analysis Tools and its duplicate links are removed. Saved `/dashboard` section links redirect to their topic pages. Process flow and saved-revision discussion retain their separate pages.

A shared route-group layout preserves project/scenario state during client navigation. Category editors filter one shared ledger without deleting other categories. Existing economic calculations and capital planning limitations remain unchanged. This is not Phase C economics or a new revenue-opportunity agent; the latest conversational waste-revenue workflow specification remains intact for future delivery.

Validation covers routing and legacy links, existing draft/engineering-scope checks, TypeScript, lint and production build, plus browser checks for topic content, retained input/sensitivity edits, shared ledger filtering, import and export. No paid research calls are needed.

## CAPEX child navigation and capital dashboard (implemented UI)

Clicking **CAPEX** expands its children, with **Summary** as the default at `/capex` or `/capex/summary`. The nested routes are `/capex/equipment`, `/capex/direct-costs`, `/capex/indirect-costs`, `/capex/working-capital`, `/capex/assumptions` and `/capex/validation`. Legacy `/dashboard#equipment` and `#engineering-analyst` anchors now reach the equipment child. The shared workspace layout retains the project when navigating among these pages.

**Summary** uses active calculated purchased and bare-module equipment costs in KPI cards, equipment-type pie and per-unit bar charts, and a capital build-up table. The table displays the legacy-style direct and indirect cost categories as explicitly **not established** until supported by project data; it does not copy historical percentage factors or numerical assumptions from the founder's workbooks. A separate planning ledger includes direct, indirect, working-capital and unclassified line items; it is **not** automatically added to the financial engine's CAPEX, because overlapping installed equipment/installation costs have not been independently reconciled. A true *total project investment* figure therefore remains not established until the required capital-cost engine integration and review are complete.

Equipment child retains the existing equipment editor, engineering analyst and relevant engineering modules. Direct/Indirect/Working Capital children provide editable, versioned capital register items (quantity, rate, cost basis, status and classification). Assumptions & Sources surfaces CEPCI and linked evidence. Validation flags incomplete/unclassified cost items, scoped equipment warnings and unconnected full-project CAPEX. Project-specific context adapts to the uploaded equipment, source evidence, site description and imported process stream records. This is a live UX restructure and ledger edit path, **not** completion of the proposed industrial total-capital engine in Phase C.

## Entry simplification — 28 October 2026

Entry now focuses on Excel mass/energy-balance intake and its process-description dialogue. The older CSV/JSON/DWSIM importer, project context editor and financial assumption controls are available under **Simulation data** at `/simulation-data`. Old `/entry#streams` and `/dashboard#streams` links resolve there. Account controls, saved data and calculation behavior are preserved.

## Empty-first analytical rebuild — 28 October 2026

The application no longer seeds active data from `/api/demo` or automatically loads a saved startup project. A new browser-storage generation leaves older active drafts archived and starts empty. Saved cloud versions and original Excel files are retained for explicit review, not loaded as the live model. Empty analyst pages display no metrics/charts rather than zeros or demonstration estimates. The process view is empty without a manually loaded project. Fresh Excel balance imports remain independently stored in the browser tab and downloadable before a new economic project exists; cloud project saving still requires an existing assessment project. Earlier startup-project behavior described in historical acceptance documents is superseded by this empty-first mode.
