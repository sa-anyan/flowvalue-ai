# Phase 3 plan — equipment design, costing and CAPEX

**Started:** 11 November 2026 · **Reference project:** Charlie (G0 sign-off S1); Team 8 held out · **Gate:** G3, a preliminary plant capital estimate an independent reviewer can check, with no hidden missing equipment and no double-counted installation.

## Milestones and order

| Milestone | Work | Owner | First ticket |
|---|---|---|---|
| **M3.2** Source-controlled costing catalogue | Verify each correlation against its printed source: page, chart range, base year and index, units, material and scope. Garrett first (154 curves, all unverified), then Nottingham (15), then the 4 additional models. OpenPyTEA (421) already has pinned upstream parity; check its source basis and scope | E1 | **GARRETT-V01** (done: 13 Charlie curves, 6 fail) → GARRETT-C01 correction |
| **M3.1** Priority equipment sizing | Close Charlie's 7 unpriced items: C-201 spray dryer, PD-201AB, R-101 electrolyser, R-201, S-201 centrifuge, T-104, T-105 | E1 | After GARRETT-C01 |
| **M3.4** Purchased versus installed scope | Apply the B08 decision C scope rules in CAPEX; record each source's inclusions; test that installation is counted once | E1 with E2 | After B08 integration |
| **M3.3** Capital cost breakdown | Equipment, installation, piping, instrumentation, electrical, civil, utilities, buildings, engineering, construction, commissioning, owner's costs | E1 | After M3.4 |
| **M3.5** AACE estimate class | Propose a class from the documented design maturity, for review rather than automatic certification | E1 | Needs the AACE 18R-97 guidance |
| **M3.6** Basis of Estimate report | Scope, exclusions, assumptions, sources and uncertainty, generated from the saved study | E1 with E2 | Last |

## Escalation (needed before CAPEX totals mean anything)

Garrett prices are at CE Index 320 (early 1987). The code currently escalates with a CPI proxy where no native index observation exists (Phase 0 finding R-03). Phase 3 needs dated CEPCI values up to the study year from a cited source; until then every escalated Garrett price stays labelled as proxy-escalated.

## Sources in use (local only; nothing copied into the public repository)

- Garrett, *Chemical Engineering Economics* (1989), Appendix 1. SHA-256 matches the catalogue's recorded file.
- Nottingham CEEDG501 *Cost Estimation* Rev 3.
- Charlie M&E workbook and the Charlie economics study. The study is a comparison made after independent calculation, never a price source.

**Still needed from the founder:** current CEPCI values; Turton, Peters & Timmerhaus or Towler & Sinnott for cross-checks; AACE 18R-97; an electrolyser cost source or vendor quote.

## G3 acceptance targets (from the roadmap)

- All priority equipment models independently tested.
- Every costing source records scope, year, currency and method.
- At least 95% of Charlie's verified equipment scope priced with justified methods; every unpriced item visible with its significance.
- Estimate class consistent with design maturity; Basis of Estimate complete.
