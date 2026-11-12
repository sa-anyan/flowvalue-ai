# COST-DATA-V01 · Check of externally researched cost data

**Date:** 12 November 2026 · **Owner:** Engineer 1 · **Input:** ChatGPT research returned to the founder on 11 November 2026 (CEPCI, small-equipment prices, electrolyser costs, references)

The original research review records each figure as checked against its cited source. Historical CEPCI observations and opt-in translation support are now included in the branch; the default 2026-09 calculation still uses the existing CPI proxy because no target-period CEPCI observation is available. Small-equipment and electrolyser research below does not introduce new price overrides.

## 1. CEPCI: verified

| Check | Result |
|---|---|
| Annual CEPCI 2000–2024 | **All match** the publisher's annual report page (chemengonline.com `pci-cost-download.php?From_Year=2000&To_Year=2024&type=year`, read 12 Nov 2026). Includes 2001 394.3, 2008 575.4, 2016 541.7 and 2024 796.2 |
| 1987, 1996, 1997 | **Match** Vatavuk, "Updating the CE Plant Cost Index", *Chem. Eng.*, Jan 2002, Table 2 (PDF page 2): 323.8, 381.7, 386.5 |
| 2002 revision splice | **Confirmed.** Revised sub-indexes were normalised so that January 2001 equals the old index; earlier history was not recalculated. Use the publisher's spliced series |
| Garrett "CE 320, early 1987" | Consistent with the 1987 annual average of 323.8. No monthly 1987 value found. Keep 320 as Garrett's stated basis |
| 2025 annual and 2026 monthly | **Not available.** Behind the publisher's paywall. Public text says 2025 was +1.6% on 2024, and August 2026 (preliminary) was +8.5% on August 2025. These are not index values and are not used |

**Blocker:** CEPCI can't replace the CPI proxy until there is a **target-period value** (2025 annual, or a 2026 month) from a *Chemical Engineering* subscription.

### Why it matters: CPI proxy against CEPCI (both to 2024)

| Source year | CEPCI ratio | CPI-U ratio | CPI proxy versus CEPCI |
|---|---|---|---|
| 1987 (Garrett, at 320) | 2.49 | 2.76 | about **+11%** (overstates) |
| 2008 (NREL electrolyser) | 1.38 | 1.46 | about **+5%** |
| 2016 (Seider) | 1.47 | 1.31 | about **−11%** (understates) |

The error runs in different directions by source year, so mixed-library totals do not cancel. CPI-U annual averages used: 1987 113.6, 2008 215.303, 2016 240.007, 2024 313.689.

## 2. Small-equipment prices: none usable

No figure matches the duty. ChatGPT labelled them "not duty-qualified", and that is correct.

| Item | What was found | Verdict |
|---|---|---|
| HE-301 cooler | A rack-mounted IT liquid cooler (10 kW, £5.3k) | Wrong service. Not rated for 207 °C process liquid |
| PD-201AB | Cast-iron progressive-cavity pump (£2.6k) | Not food-grade; capacity not confirmed at 110 L/h |
| P-102AB | 12 V gear pump (£164) | Not centrifugal; about 8× the flow |
| C-202 | Steam separators (£1.2–1.3k) and a dust-sampling cyclone (€2.7k) | Not solids cyclones at the stated duty |

**Decision:** keep all four at the minimum-size floor (CHARLIE-COV03) until there are vendor budget quotes.

**Flag for the founder:** C-202 is modelled as spray-dryer exhaust at **19.8 bar(a)**. Spray dryers normally run near atmospheric pressure. Check the M&E pressure for this stream and its unit (bar or psi; gauge or absolute) before pricing it.

## 3. Electrolyser: supports R101 review

ChatGPT's sources agree with the R101 recommendation (NREL 2008 base case, $1,536/kW uninstalled system, CPI-proxy 2026-09):

- IEA GHR 2024: PEM $2,450/kW and alkaline $2,000/kW **installed**, including EPC and contingency. That is above an uninstalled figure, as expected.
- IRENA 2023: PEM system $700–1,400/kW at 10 MW or more. Scope and year are less clear.
- Nel order, January 2025: about US$7 M for 2 × 2.5 MW containerised PEM. That implies about **$1,400/kW** (derived here; delivery and installation scope not stated). This is the closest public small-scale reference, and it sits inside the R101 band of $1,150–1,610/kW.
- DOE alkaline uninstalled system, $500/kW (2022): assumes high-volume manufacturing, so not comparable for about 2 MW.

**No change to R101.** Watch for double counting: if the installation factors in M3.4 are applied on top of an installed benchmark, installation is counted twice. Only uninstalled figures should feed purchased-equipment cost.

## 4. References and AACE

- Bibliographic details match the publisher records: Seider 4th (2017), Turton 5th (2018), Towler & Sinnott 2nd (2012), Perry 7th (1997).
- The AACE 18R-97 class summary (Classes 1–5, maturity and accuracy ranges) comes from the public table-of-contents sample, August 2020 revision. It is good enough to draft M3.5. The gate still needs the purchased document.
- The textbook tables still need library or owned copies. None were reproduced.

## Branch handoff — 12 November 2026

Committed the historical CEPCI catalogue, opt-in translation and focused tests to `e1/m3-capex-scope`. Verification: **39 passed** across `test_cost_translation.py` and `test_cepci_series.py`; no deployment performed. The generated `frontend/next-env.d.ts` development-path change is intentionally excluded. The research sources were not independently rechecked during this Git handoff.
