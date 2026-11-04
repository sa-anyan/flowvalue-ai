# Charlie — independent equipment pricing

All amounts are quantity-extended USD at the existing September 2026 price basis. CPI is a purchasing-power proxy. E = ESTIMATED — ENGINEERING ASSUMPTION; U = UNPRICED — SOURCE REQUIRED; A = ALIAS — NO ADDITIONAL PURCHASE. Model IDs refer to the executable Garrett catalogue; estimates retain graph/extrapolation and sizing warnings.

| Equipment | Costing method | Independent price | Source | Status |
|---|---|---:|---|---|
| BL-201AB | G261-016 | $40,267.87 | Garrett p. 261 | E |
| C-201 | No supported basis | — | Source required | U |
| C-202 | G279-066 | $185.30 | Garrett p. 279 | E |
| FT-101AB | G282-076 | $3,092.04 | Garrett p. 282 | E |
| FT-201 | Alias | $0 additional | Reference: FT-201AB | A |
| FT-201AB | G282-076 | $3,979.83 | Garrett p. 282 | E |
| HE-101 | G286-091 | $2,547.48 | Garrett p. 286 | E |
| HE-102 | G286-091 | $1,355.71 | Garrett p. 286 | E |
| HE-103 | G286-091 | $2,261.06 | Garrett p. 286 | E |
| HE-201 | G286-091 | $13,519.25 | Garrett p. 286 | E |
| HE-301 | G286-089 | $34,227.25 | Garrett p. 286 | E |
| MT-101 | G258-008 | $5,948.94 | Garrett p. 258 | E |
| P-101AB | G296-122 | $4,899.56 | Garrett p. 296 | E |
| P-102AB | G296-122 | $1,534.35 | Garrett p. 296 | E |
| P-103AB | G296-122 | $6,029.56 | Garrett p. 296 | E |
| P-104AB | G296-122 | $4,014.42 | Garrett p. 296 | E |
| P-105AB | G296-122 | $868.06 | Garrett p. 296 | E |
| P-201AB | G296-122 | $5,187.24 | Garrett p. 296 | E |
| PD-201 | Alias | $0 additional | Reference: PD-201AB | A |
| PD-201AB | No supported basis | — | Source required | U |
| R-101 | No supported basis | — | Source required | U |
| R-102 | G258-007 | $105,503.58 | Garrett p. 258 | E |
| R-201 | No supported basis | — | Source required | U |
| S-201 | No supported basis | — | Source required | U |
| T-101 | Alias | $0 additional | Reference: T-101AB | A |
| T-101AB | G290-104 | $3,758.89 | Garrett p. 290 | E |
| T-102AB | G290-104 | $3,757.60 | Garrett p. 290 | E |
| T-104 | No supported basis | — | Source required | U |
| T-105 | No supported basis | — | Source required | U |
| T-106 | G303-141 | $2,150.48 | Garrett p. 303 | E |
| T-201 | G303-143 | $17,506.76 | Garrett p. 303 | E |
| T-301 | G303-144 | $3,553.11 | Garrett p. 303 | E |

- Independently computed engineering-assumption estimates: 22. Strict CALCULATED — CORRELATION with no provisional-sizing/graph qualification: 0.
- Independent analogies: 0. Explicit user prices: 0. Unpriced assets: 7. Aliases: 3.
- Coverage: 22/29 separate equipment records (75.9%); 22/32 source tags numerically priced (68.8%), with three additional alias records. Alias PD-201 still references an unpriced canonical pump; it does not add another missing purchase.
- Purchased-equipment subtotal: $266,148.33. Partial CAPEX subtotal: $1,456,762.89. The previous seeded $29,085,409.15 is not an independent estimate and is superseded for this demonstration.
- R-101 stays unpriced. PD-201AB is identified as a positive-displacement slurry pump; no compatible, adequately supported price was forced. R-201 is not assigned R-102's cost.
- Focused checks: seven stale imported source records rejected; explicit user reapproval remains possible; aliases charge no additional cost; one canonical end-to-end smoke run reconciles purchase subtotal to CAPEX. Four focused provenance tests and TypeScript checking passed. No full regression suite, research or LLM calls.

Local assessment: `1ae103ba1ddd4aa594a0525d4522f37d`.

Changed files: `backend/equipment_costing/manual.py`, `quotes.py`; `backend/orchestration/pricing_status.py`, `pipeline.py`, `service.py`; `frontend/src/components/assessment-workspace.tsx`, `equipment-price-editor.tsx`, `premium-equipment-workspace.tsx`, `capex-studio.tsx`; `backend/tests/test_pricing_provenance.py`; `docs/equipment-pricing-provenance.md`; this table.
