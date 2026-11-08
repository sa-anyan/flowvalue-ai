# Economic dashboard recovery — 8 November 2026

## Root causes

The affected Team 8 assessment (755270a083f74634af22514b2ab32830) had no CAPEX/OPEX output. Economic planning carried approximately 331 KB of calculated-stage data, principally 312 KB of equipment matching/sizing audits, and crossed the 240 KB planning bound. The dashboard displayed its empty-state link instead of explaining that stage failure.

After compacting that payload, a live retry exposed missing delivery_basis in the generic CAPEX JSON proposal. A strict capital proposal adapter now requires the process class, delivery basis and published Garrett factors. Economic-only context keeps CAPEX factor ranges and existing capital assumptions; full original engineering evidence stays in the source assessment.

OPEX subsequently reached its dependency check but stopped all costs because revenue-based factors had no Revenue result. OPEX now uses CAPEX and Revenue as optional, fingerprinted cost bases. It calculates supported cash lines and leaves unavailable bases unresolved. When either base changes, its input fingerprint invalidates the saved OPEX result. This does not execute dependencies or approve Revenue assumptions.

## UI and preservation

CAPEX/OPEX show their dashboard layout even when blocked, with real stage errors and missing numerical values. Stale or failed economic runs retain the last successful saved display, flagged as stale; the calculation engine still checks freshness and cannot consume a stale display as an accepted input.

## Live retry

A named version was saved before retrying. No workbook facts, equipment matches or manual prices were replaced. Live AI requests prepared capital/operating assumptions; Python performed calculations.

- CAPEX: USD 3,780,470.15; saved period 2026-09.
- OPEX: USD 829,511.55 in operating year 1 known cash subtotal; saved period 2026-09. Partial: revenue-dependent costs remain unresolved. This is not a complete annual operating cost or an industrial validation claim.

Browser verification confirmed both dashboards display the affected assessment’s saved numerical results. OPEX displays the selected operating year, which may differ from the first-year figure.

Validation: 22 backend regression tests, six dashboard tests and the production build passed.

The successful OPEX calculation used Python only after its proposal had been saved; no additional AI request was needed to calculate it.
