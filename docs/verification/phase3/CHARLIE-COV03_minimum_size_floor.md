# CHARLIE-COV03 · Minimum-size floor for equipment below every correlation's range

**Date:** 11 November 2026 · **Owner:** Engineer 1 · **Decision:** founder, option B in CHARLIE-COV02

## Rule

When an item's size is **below** a correlation's range, it is priced at the correlation's **minimum size**: the cost of the smallest unit the source covers. The floor is recorded on the line as an explicit assumption: requested size, size priced, the ratio between them, and a "BELOW-RANGE FLOOR" issue to list in the Basis of Estimate.

| Library | Minimum used | Notes |
|---|---|---|
| Garrett (graph curves) | Lowest digitised chart anchor | Replaces downward extrapolation |
| OpenPyTEA | Published lower bound (`s_lower`) | Previously refused (out of range) |
| Nottingham, additional models, Garrett direct-equation curves | Unchanged | They keep their own range rules; follow-up |

- **Sizes above a range are unchanged.** Garrett still extrapolates with disclosure; OpenPyTEA still refuses.
- **Per-item override:** `costing_options.below_range_policy = "extrapolate"` restores the previous behaviour for that item.
- **The AI sizing step** is told to keep the best-matching model when a size is below range, instead of switching library (cache version bumped).

## Effect on Charlie (11 November AI run, re-priced in Python with the AI's model choices)

| Measure | Before | With floor |
|---|---|---|
| Items priced | 26 of 28 | **28 of 28** |
| In range | 14 | 14 |
| Minimum-size floor | — | **14** |
| Extrapolated below range | 12 | **0** |
| Unpriced | 2 (HE-101, HE-102) | **0** |
| Equipment total (CPI-proxy 2026 USD) | $4.83 M | $5.06 M (+4.8%) |

Every item now has a price from a stated method: either in range, or the documented floor. Against the G3 test ("priced with justified methods, unpriced items visible"), Charlie moves from about 54% to **all items covered by a stated method**.

## Limits of the floor

The floor is conservative, so it **overstates** when an item is far below the minimum. Four items sit more than 100× below theirs:

| Item | Times below minimum | Floor price |
|---|---|---|
| HE-301 condensate cooler | 178× | $54 k |
| PD-201AB positive-displacement pump | 144× | $36 k |
| P-102AB pump | 111× | $7 k |
| C-202 cyclone | 102× | $3.8 k |

These are the first candidates for real small-equipment prices (option C: catalogue or vendor quotes). Until then they stay floored and listed.

## Unchanged from COV02

- **R-101 electrolyser** ($3.44 M, 68% of the new total) still needs a current cost basis.
- **Run-to-run variability** in the AI's model choices (for example R-102 at $93 k versus $755 k across runs) still applies. Confirm key models in the equipment page; user choices are protected.
- Prices still use the CPI proxy until CEPCI values are supplied.

Data: `charlie_coverage_map_floor.csv` (no sizes).
