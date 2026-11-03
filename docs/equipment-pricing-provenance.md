# Independent equipment pricing provenance

The Charlie price importer and embedded price profile were removed in commit 0238ab8. Their archived local copies and original workbooks remain reference material; no runtime code loads them.

Numerical estimates now carry `pricing_status` and `pricing_provenance`: identification, sizing parameters/assumptions, selected model/source/formula, original price and period, escalation audit, quantity-extended purchase/installation components and target period. Escalation never establishes independent costing. Digitised charts, extrapolations and assumed engineering inputs remain estimates rather than being labelled calculated solely because they return a number. CPI escalation is explicitly a purchasing-power proxy.

Manual/comparable inputs labelled as automatic project benchmarks, prior CAPEX outputs or Charlie economics workbook sources are rejected unless a separate explicit user edit approves the amount. A saved script's `approved: true` flag is insufficient. The existing edit endpoint records explicit approval; the drawer exposes reapproval. Original source values are retained. Normal source-backed independent comparables and direct user prices remain available.

Confirmed scenario aliases retain original tags and references, adding no purchased cost even if the canonical asset itself is still unpriced. That asset remains unresolved. CAPEX responses now carry equipment-scope completeness and excluded equipment; the UI labels incomplete totals as known CAPEX subtotals.

Current executable equipment correlations are Garrett. No Turton/Guthrie/Seider support is implied merely by their names. There were no provider or research calls, parser changes, financial-engine rebuilds, simulations or deployments in this correction.

Focused verification rejects the seven seeded workbook prices, retains an explicitly reapproved user price, checks unpriced R-101 and three zero-additional-cost alias relationships, and reconciles the canonical purchased-equipment subtotal with CAPEX. The 32-record end-to-end run is preserved locally; original studies and baselines remain unchanged. The previous fully priced demonstration is historical evidence of the removed shortcut, not independent costing evidence.

See the adjacent [32-record result table](charlie-independent-pricing-results.md) for counts, prices, source pages, coverage and remaining gaps.
