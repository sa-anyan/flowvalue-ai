# GARRETT-V01 · Verification of the 13 Garrett curves used by the Charlie reference project

**Date:** 11 November 2026 · **Owner:** Engineer 1 · **Phase 3 milestone:** M3.2 (source-controlled costing catalogue)

**Decision: 6 PASS, 1 MARGINAL, 6 FAIL.** The six failing curves price 12 of Charlie's 22 Garrett-priced lines. No production data was changed in this ticket; corrections follow in GARRETT-C01 after a pixel-level digitisation (see "Next").

## Why these 13 first

Charlie is the reference project (G0 sign-off S1). These 13 curves carry every Garrett price in Charlie's current independent pricing (`docs/charlie-independent-pricing-results.md`), so their accuracy decides Charlie's equipment cost and the M3 coverage measure. The other 141 Garrett curves follow in later batches.

## Method

- **Source:** the supplied Appendix 1 PDF. SHA-256 `720cca1e5e8927c4…` matches `pdf_sha256` in `review_curves.json`, so the stored readings came from this exact file.
- Each chart page was rendered at 2.2× and read independently of the stored values, at the same sizes.
- **Independent check:** most pages print a size exponent *n*. A correct set of readings must follow C ∝ Sⁿ along a straight line. Stored readings whose slopes contradict the printed exponent are wrong regardless of reading precision.
- **Tolerance:** visual reads of a log-log chart carry roughly ±10–15%, more on curved lines. PASS means within about 20% and consistent with the printed exponent. FAIL means a deviation well beyond reading error or a slope that contradicts the exponent.

This is a second visual reading, not a digitisation. Its job is to find gross errors, which it did.

## Results

| Curve | Charlie tags | Verdict | Finding |
|---|---|---|---|
| G258-007 Agitated reactor 50 psi | R-102 | PASS | Within 11%; follows printed 0.53 |
| G258-008 Agitated open tank | MT-101 | PASS | Within 10% |
| G261-016 Turbo blower 3 psi | BL-201AB | PASS | Within 17% on a curved line |
| G282-076 Pressure leaf / plate and frame filter | FT-101AB, FT-201AB | PASS, with basis caveat | Readings match, but the **whole chart is stainless steel**; the page prints 0.69 for mild steel |
| G286-089 Air-cooled exchanger | HE-301 | PASS | Within 7%; follows printed 0.39 |
| G286-091 Shell-and-tube exchanger | HE-101, -102, -103, HE-201 | PASS | Within 7%; follows printed 0.68 |
| G277-060 Fluid-bed dryer | PD-201AB (provisional) | MARGINAL | Largest point about 25% high |
| **G296-122 Conventional centrifugal pump** | **P-101AB … P-105AB, P-201AB** | **FAIL** | Stored 5 / 21 / 70 $k at 1 / 10 / 100; chart 1.4 / 2.8 / 11. **3.5–6.5× too high.** The readings stored under G296-124 (mixed/axial) actually trace the conventional line; labels were mixed up. Mixed and axial flow are also two separate lines on the page, not one |
| **G290-104 Ion exchange** | **T-101AB, T-102AB** | **FAIL** | 60–95% high above 100 gpm; stored slope 1.06 vs printed 0.97 |
| **G303-141 Horizontal pressure tank** | **T-106** | **FAIL** | About half the chart value; the 100,000 gal point lies beyond the line's end (about 75,000 gal) |
| **G303-143 Small cone-roof tank** | **T-201** | **FAIL** | About 1.8–1.9× the chart value; the 100,000 gal point lies beyond the line's end (about 35,000 gal) |
| **G303-144 Small storage tank** | **T-301** | **FAIL** | About 1.6–2× the chart; stored slopes 0.60 and 0.46 contradict printed 0.71; line ends at about 20,000 gal |
| **G279-066 Cyclone / multiclone** | **C-202** | **FAIL** | The size axis was misread by about 3×: stored (200, 22) and (700, 65) correspond to chart points (60, 22) and (160, 65). The curve ends at about 160,000 cfm |

Full readings: `garrett_charlie_curve_verification.csv`.

## Effect on Charlie

- **Pumps (6 lines) are overstated** by roughly 3.5–6.5× at the curve's anchors.
- **Ion exchange (2 lines) and two tanks (T-201, T-301) are overstated**; **T-106 is understated**.
- **C-202 is understated**, because cost is read at about a third of the true size.
- **Filters** may be overstated by about 45% if the equipment is mild steel and the 0.69 factor is not applied.

The current Charlie equipment total is therefore not reliable for Phase 3 coverage or CAPEX until GARRETT-C01 lands.

## Wider implications

- All 154 Garrett curves are recorded as `Unverified`: 143 low-confidence readings, and 533 of 1,031 points missing. This first batch failed 6 of 13, so the remaining 141 need the same check before any is relied on.
- Several stored points lie **beyond the end of the printed line** without being flagged as extrapolation. The catalogue should record each line's start and end so out-of-range use is flagged.
- **Material and configuration basis** must be carried per chart: stainless versus mild steel, the pump's included motor, coupling and base, and the exchanger's floating head at 150 psig.

## Next

1. **GARRETT-C01, correction:** digitise the six failing curves at pixel level from the rendered pages (axis calibration plus line tracing), confirm against the printed exponents, and apply through the existing `source_corrections.json` mechanism, with tests that pin the corrected anchors and the line ranges. Re-price Charlie and record before and after.
2. **Record chart ranges and material bases** for these 13 curves, and flag out-of-range use as extrapolation.
3. **GARRETT-V02 onward:** verify the remaining 141 curves in page order.

No production data, coefficients or prices were changed by this ticket.
