# Engineer1 execution backlog — proposed, not implemented

No Phase1 equation, coefficient or production architecture change was performed. P1/P3/P4/P7 labels below are provisional until the official P0–P9 roadmap is agreed.

| Order | Task | Entry/dependency | Measurable acceptance | Owner |
|---|---|---|---|---|
| 1 | Agree exact source set, official gate and numerical conventions | REQ-02/R-02/R-13; both engineers | Versioned source/page/rights inventory and approved test tolerance/timing policy; 13-field mapping decision recorded | E1 + E2 |
| 2 | Establish independent unit reference cases and parser/bridge parity | REQ-04/R-05/R-06 | kg/h vs m3/h, absolute/gauge, K/deltaK, US/Imperial, energy/power, annual/hourly, standard/actual gas; ambiguous context rejected | E1 |
| 3 | Verify 12 preliminary sizing methods individually | Task2; independent physical equations | Explicit reference calculation, limits/invalid cases, units and uncertainties per registry method; clarify vaporizer duty contract | E1 with E2 adapter review |
| 4 | Verify canonical model-native coordinate adapters | Task2–3; R-05 | Same physical input yields same coordinate across direct/parsed adapters; Nottingham exceptions explicit; no hidden conversion assumption | E1 |
| 5 | Source-check direct historical correlations | Task1–4; costing register | Original pages/units/year/scopes and at least nominal/boundary independent expected values per enabled direct configuration | E1 |
| 6 | Review graph fits, pressure/material factors and extrapolation | Task5; R-15 | Training/holdout provenance, graph-read error, source exponent or explicit assumption, nearest-boundary behaviour and refusal policy independently checked | E1 |
| 7 | Reconcile quantity, purchase/installation/package scope and plant factors | Task5–6; R-08/REQ-11/REQ-12 | AB quantity once; aliases not double counted; included categories excluded from later factors; detailed vs Lang alternatives reconcile | E1 + E2 |
| 8 | Verify price-period/FX observations and visible basis | Task1/5; R-03 | Sourced dated observations independently checked; ratio arithmetic reproduced; proxy/native/FX distinguished in results and exports | E1 + E2 reporting |
| 9 | Independently verify OPEX and Revenue schedules/bases | Task7; R-01/R-04/R-09 | Correct annual quantity/time/price, dependent factor order, no cycle/double ramp, no unsupported sale, approved inputs survive edits; fix handoff with E2 | E1 + E2 |
| 10 | Verify annual ledger and all reported metrics against agreed reference | Tasks7–9; R-10/R-12 | Independent construction/ramp/tax/WC/debt cash ledger, timing-matched NPV/IRR/payback/unit costs, canonical Monte Carlo representative-run and export parity | E1 + E2 P7 |

The current baseline failure R-01 should be triaged with Engineer2 before claiming complete system integration. Do not “fix” it by weakening completeness assertions, inventing a commercial year, changing historical source values or copying Charlie economics prices.

Engineer2 separately owns schema/ingestion, AI review correctness, orchestration freshness, API/UI reconciliation, tenant security and reproducible deployment. Engineer1 supplies dimensional and numerical acceptance contracts rather than rebuilding those layers.
