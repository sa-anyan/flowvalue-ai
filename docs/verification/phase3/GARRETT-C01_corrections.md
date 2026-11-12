# GARRETT-C01 · Digitised corrections for the failing Garrett curves

**Date:** 11 November 2026 · **Owner:** Engineer 1 · **Follows:** GARRETT-V01

**Decision: corrected.** Seven curves now use digitised anchors; one merged curve is blocked until it is split. Full backend suite: 4,215 passed, 0 failed.

## Method

The source pages were rendered at 4× and digitised pixel by pixel (`garrett_c01_evidence/digitise.py`):

1. Axes are calibrated from the plot frame on a log-log scale. Decade gridlines land within about 2 px of their predicted positions on every page used.
2. At each size, the line centre is traced over 5–9 nearby columns, skipping gridlines, and the median is taken.

**Validation against printed exponents.** On a page that already passed GARRETT-V01, the shell-and-tube exchanger traced at slope 0.686 against the printed 0.68. On the corrected pages:

| Curve | Traced slope | Printed exponent |
|---|---|---|
| G290-104 ion exchange | 0.967 | 0.97 |
| G296 mixed flow / axial flow | 0.790 / 0.792 | 0.79 |
| G303-141 horizontal 150 psi tank | 0.731 | 0.72 |
| G303-143 small cone-roof tank | 0.523 | 0.51 |
| G303-144 small storage tank | 0.771 | 0.71 |

The two curved lines (conventional pump, cyclone) have no printed exponent.

## Changes

| Curve | Correction |
|---|---|
| G296-122 conventional pump | 14 anchors, 1.5 to 300. The old readings matched no line |
| G296-123 in-line pump | 6 anchors, 8 to 50; the line starts at about 7.5 and joins the conventional curve near 60 |
| G290-104 ion exchange | 12 anchors, 15 to 4,000 gpm |
| G303-141 / -143 / -144 tanks | Anchors only along each printed line (ends at about 75k, 35k and 20k gal) |
| G279-066 cyclone | 13 anchors, 1.5k to 150k cfm |
| **G296-124 mixed/axial pump** | **Blocked**: the page prints two separate lines, so one combined price is not defensible; split before use |

Mechanism: the existing `source_corrections.json`, now with a per-model page reference, method and confidence. It also fixes a bug: the correction loader forced the dryer's size unit ("actual chamber volume, ft3") onto **every** corrected curve. It now changes the unit only for the dryer corrections.

Four existing tests pinned the wrong readings: cyclone anchors (20 → $5,000 and 700 → $65,000), a cyclone "in-range" size beyond the line end, and the merged pump curve. They now assert the digitised values, with comments explaining why. New tests are in `backend/tests/test_garrett_c01_corrections.py`.

## Before and after

In-range checks (USD at CE index 320) now reproduce the chart:

| Check | Before | After | Chart |
|---|---|---|---|
| Ion exchange, 1,000 gpm | 324,402 | 206,418 | 205,729 |
| Horizontal tank, 10k gal | 15,577 | 26,641 | 26,574 |
| Cone-roof tank, 10k gal | 25,713 | 13,976 | 14,083 |
| Small storage tank, 10k gal | 7,166 | 5,438 | 5,600 |
| Conventional pump at 10 | 19,443 | 3,220 | 2,796 |
| Cyclone, 50k cfm | 9,213 | 20,729 | 19,299 |

The pump and cyclone carry a single fitted exponent over a curved line, so in-range residuals of about 15% remain and are flagged by the existing fit diagnostics.

## The bigger issue for Charlie: size range

Charlie's equipment on these curves sits **far below** the printed charts:

- Pumps: 0.002–0.047 against a chart that starts at 1, so 20–500× below.
- T-201: 72 gal against 1,000 gal.
- Ion exchange: 1.6 gpm against 10 gpm.
- C-202: 288 cfm against 1,000 cfm.

Their prices therefore come from extrapolation, which the code flags as very large. After correction the six pumps price at $47–$250 (1987 dollars), previously $140–$868. **Neither is a credible price** for a pump with its motor. Small equipment needs a costing method valid at that scale, or an explicit vendor price. That is tracked under M3.1 (priority equipment coverage).

Full figures: `garrett_c01_evidence/reprice_before_after.json`.

## Not changed

- The marginal fluid-bed dryer (G277-060).
- The other 141 Garrett curves. They need the same check, page by page.
- Escalation: prices remain at CE index 320 until real CEPCI values are supplied.
