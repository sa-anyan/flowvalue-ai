# CHARLIE-COV02 · Live AI run of Charlie with OpenPyTEA-first

**Date:** 11 November 2026 · **Owner:** Engineer 1 · **Follows:** CHARLIE-COV01

## Run

- **Code:** `main` plus PR #7 (Garrett corrections) and PR #8 (OpenPyTEA-first, protected user choices), on the local branch `local/charlie-ai-run`.
- **Model:** `gpt-6-luna`, AI enabled.
- **Workbook:** `M&E Balance V2 Team Charlie.xlsx`, uploaded to the local backend through its API (no UI). The same process description as the 6 November run.
- **Steps:** AI engineering extraction (6 of 6 review batches succeeded, 0 AI errors), engineering data approved, equipment stage with AI matching, sizing and pricing (0 AI errors).
- **Private data:** sizes and the full assessment stay in the ignored `outputs/charlie-ai-run-2026-11-11/`.

## Result

| Measure | 6 Nov run (re-priced, COV01) | 11 Nov AI run |
|---|---|---|
| Equipment items (excluding 3 aliases) | 29 | 28 |
| Priced | 29 | **26** (HE-101 and HE-102 unpriced: outside OpenPyTEA's published range, no fallback taken) |
| By library | OpenPyTEA 10 · Garrett 15 · Nottingham 3 · additional 1 | OpenPyTEA 8 · Garrett 14 · Nottingham 4 |
| **Priced inside the source's range** | 16 of 29 (55%) | **14 of 26 (54%)** |
| Extrapolated | 13 (3× to 223×) | 12 (1× to 178×) |
| Equipment total (CPI-proxy 2026 USD) | $4.36 M | $4.83 M |

**Coverage did not move.** G3 measures justified pricing, and in-range coverage is still about 55% against a 95% target.

## Why: OpenPyTEA-first worked, scale is the limit

- **Matching:** the AI listed OpenPyTEA models first for all 28 items and left the configuration to the sizing step. No Garrett selection had to be overridden.
- **Sizing:** the sizing step picked OpenPyTEA wherever Charlie's calculated size sat inside OpenPyTEA's published range. Where it did not, the step fell back to Garrett with disclosed extrapolation, and its recorded reasoning says so for each item. For example:
  - **HE-301:** "OpenPyTEA air-cooler models have lower capacity bounds that do not cover the small calculated area".
  - **C-202:** the cyclone is "below the OpenPyTEA cyclone model's stated 200 cfm minimum".
  - **P-201AB:** "the OpenPyTEA flow model's published minimum exceeds the resulting small liquid flow".

This is the founder rule as designed: OpenPyTEA first, Garrett when OpenPyTEA does not apply. Charlie is a 100 kg/h plant, and much of its equipment is smaller than **both** libraries cover.

## Other findings

1. **Run-to-run variability is large.** The same workbook and description produced very different picks and prices from 6 to 11 November:
   - **R-102:** $92.8 k → **$754.5 k** (Turton → Towler jacketed reactor)
   - **HE-201:** $12.7 k → $43.4 k
   - **FT-101AB:** $119 k → $64 k
   - **HE-301:** OpenPyTEA fin-fan → Garrett 178× extrapolation

   This is the AI repeatability gap in roadmap milestone M5.7. A user-confirmed model choice, now protected (PR #8), is the immediate safeguard.
2. **Two items left unpriced (HE-101, HE-102).** Their OpenPyTEA candidates were out of range, and no Garrett fallback was attempted, unlike the other items. Investigate why the repair path stopped there.
3. **Engineering-data approval during preparation.** Approving while preparation was still running changed the revision under it, and preparation then failed to save. The equipment stage redid the work, so the result is complete. The API should refuse approval while preparation runs.
4. **Hidden AI errors.** In the earlier attempt, every AI call failed (a certificate problem in the local Python), but the app showed only "batch unavailable: RevenueAIError". The real provider message should be shown.
5. **R-101 electrolyser** is unchanged at $3.44 M, 71% of the total, and still needs a current cost basis or a vendor quote.

## Decision needed: equipment below every correlation's range

Twelve items sit below both libraries' published ranges. The options for preliminary estimates:

| Option | Effect |
|---|---|
| A. Extrapolate below range (today) | Prices like a $239 cyclone or $419 pump with motor; not credible, and flagged |
| **B. Price at the correlation's minimum size** | A common estimating convention for very small equipment: the cost floor of the smallest listed unit. Conservative and simple; record it as an explicit assumption per item |
| C. Small-equipment sources | Catalogue or vendor prices for small pumps, tanks and exchangers; most accurate, needs sourcing |

The recommendation is **B now, C over time**, with every floor-priced item listed in the Basis of Estimate. This is a founder and Engineer 1 decision.

Data: `charlie_coverage_map_ai_run.csv` (no sizes).
