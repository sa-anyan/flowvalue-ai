# CHARLIE-COV01 · Charlie equipment coverage map

**Date:** 11 November 2026 · **Owner:** Engineer 1 · **Milestones:** M3.1, M3.2 · **Measures:** the G3 coverage target (at least 95% of verified equipment scope priced with justified methods)

## Method

- **Input:** the latest saved Charlie run (6 November 2026, `charlie-final-run10`), already matched and sized.
- **Re-priced in Python only** (no AI calls) with `main` plus PR #7 (Garrett corrections) and PR #8 (OpenPyTEA-first).
- **Not repeated:** AI matching. No AI key is configured in this checkout, so the OpenPyTEA-first rule has **not** re-selected models here. The "OpenPyTEA models available" column shows where it will when the run is repeated with AI enabled.
- **Prices** are 2026 USD reached with the consumer-price (CPI) proxy, **not** CEPCI (Phase 0 finding R-03).
- **Private data:** sizes come from the private Charlie workbook and are kept in the ignored `outputs/charlie-coverage-2026-11-11/`, not in this public repository.

## Headline

| Measure | Result |
|---|---|
| Register entries | 32 (29 equipment + 3 aliases counted once under their AB entries) |
| Priced | **29 of 29** (no item is unpriced) |
| By library | OpenPyTEA 10 · Garrett 15 · Nottingham 3 · additional models 1 |
| **Priced inside the source's range** | **16 of 29 (55%)** |
| Priced by extrapolation | 13 of 29: 3× to 223× outside the chart (all Garrett) |
| Garrett items with OpenPyTEA models of the same family | 13 of 15; only ion exchange (T-101AB, T-102AB) has none |
| Equipment total | $4.36 M, of which **R-101 electrolyser $3.44 M (79%)** |

Every item has a price, but only 55% are inside their source's range. Phase 3's measure is "priced with justified methods", and a price extrapolated 20–200× beyond a chart is not justified. **G3 coverage today is about 55%, against a 95% target.**

## Items priced by extrapolation

| Item | Library and model | Times outside chart | OpenPyTEA same-family models |
|---|---|---|---|
| P-102AB | Garrett conventional pump | 223× | 14 |
| C-202 | Garrett cyclone | 102× | 12 |
| P-201AB | Garrett conventional pump | 58× | 14 |
| P-104AB | Garrett conventional pump | 25× | 14 |
| P-101AB | Garrett conventional pump | 19× | 14 |
| T-101AB, T-102AB | Garrett ion exchange | 9× | none |
| T-106, T-301 | Garrett tanks | 9× | 24 |
| HE-103, HE-201 | Garrett heat exchangers | 7× | 33 |
| S-201 | Garrett centrifuge | 4× | 13 |
| T-105 | Garrett horizontal pressure tank | 3× | 24 |

These are Charlie's small items: a 100 kg/h plant is smaller than most 1987 Garrett charts cover.

## Items needing engineering review even though in range

| Item | Price | Why review |
|---|---|---|
| **R-101 electrolyser** | $3.44 M (OpenPyTEA, NREL 2008) | 79% of all equipment cost. Order of magnitude plausible for about 2 MW of electrolysis, but it decides the whole estimate: needs a current, cited cost basis or a vendor quote |
| **BL-201AB blower** | $289 k (OpenPyTEA screw compressor, about 90 hp) | 90 hp looks large for this duty; check the sizing inputs before the price |
| **FT-101AB filter** | $119 k (OpenPyTEA gravity filter) | About 40× the earlier Garrett estimate for the same 3.7 m²; check the correlation's basis and units |
| **R-102 and R-201** | $92.8 k each, same size | Identical size and price: confirm R-201 is a separate vessel, not a duplicate of R-102 (open since the Phase 0 review) |

## Effect of GARRETT-C01 (PR #7)

The equipment total changes only slightly ($4.367 M → $4.356 M), because R-101 dominates. Line by line: pumps P-101AB, P-102AB, P-104AB and P-201AB fall by 68–82%; tanks T-105 and T-106 rise by 71%; T-101AB, T-102AB and T-301 fall by 24–36%; C-202 rises by 28%. All of these are still extrapolated, so the corrections fix the anchors but not the size-range problem.

## Next steps, in order

1. **Re-run Charlie with AI enabled** (where the AI key is configured) so OpenPyTEA-first re-selects the 13 Garrett items, then repeat this map. Most should move into an in-range OpenPyTEA correlation.
2. **For items still out of range:** check whether a smaller-range method exists (Nottingham's motor-power pump equation, a supplier price) and record any remaining extrapolation as an explicit exception with its significance.
3. **Review the four items above**, starting with R-101 (cost basis or quote) and BL-201AB (sizing).
4. **Escalation:** replace the CPI proxy with CEPCI once values are supplied; every price above moves.
5. **Source checks:** the OpenPyTEA correlations now pricing Charlie (gravity filter, vertical cylinder, jacketed reactor, electrolyser, double pipe, spray dryer, screw compressor, air-cooled fin-fan) against Seider, Turton, Perry and NREL once those sources are available.

Data: `charlie_coverage_map.csv` (no sizes).
