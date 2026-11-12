# G3 gate review pack — 12 November 2026

**Prepared by:** Engineer 1 · **For:** an independent reviewer, Engineer 2, and the founder · **Code basis:** branch `e1/g3-review-pack` (stacked on PRs #16 → #18 → #19), updated by M3.7 on `e1/m3-7-assumption-tier`
**Authority:** official roadmap Phase 3 (implementation work, milestones M3.1–M3.6, testing, acceptance criteria, exit gate G3), plus the rev 1.1 additions (M3.7 and its three criteria).

## Exit gate

> **G3:** FlowValue produces an independently reviewable preliminary plant capital estimate without concealing missing equipment or double-counting installed costs.

## Decision

**G3: NOT YET PASSED. All Phase 3 milestones, including M3.7, are built. The gate's core claims hold on Charlie and on the held-out Team 8 run, but two criteria are partial.**

On Charlie, FlowValue now produces a complete, reconciled preliminary capital estimate:

- 28 of 28 items are priced by a stated method, and none is hidden.
- All four double-count checks pass.
- An estimate class is proposed.
- A Basis of Estimate is generated.

The gate cannot pass yet for three reasons. A fourth, the held-out run, was resolved on 12 November ([Team 8 record](G3-R3-team8-heldout.md)):

1. **No clean held-out project yet.** Team 8 was run on 12 Nov, but its units had already shaped the prompts (corrected in the Phase 5 audit), so it does not count as held out. A new, unseen project is needed.
2. **Most of Charlie's items rest on assumptions.** M3.7 tiers: 2 of 28 items are source supported (70% of priced value), and 26 are assumption based. Of those, 14 use the minimum-size floor, and 12 rest only on sizing inputs the AI estimated.
3. **The OpenPyTEA correlations are unchecked.** They are now the preferred library, but they haven't been checked against their textbook sources.
4. **Escalation still uses the CPI proxy.** No 2025 or 2026 CEPCI value has been added yet.

**Reproduce:** `python docs/verification/phase3/g3_review/reproduce_g3.py [--study DB --assessment KEY]`. It runs the G3 test groups and catalogue checks. With a study, it re-prices a temporary copy without AI. Output contains counts and checks only.

## 1. Acceptance criteria

| ID | Criterion | Status | Evidence / what remains |
|---|---|---|---|
| A1 | All priority equipment models have independently tested calculations | **PARTIAL** | **Sizing:** 20 independently specified reference cases (pumps, exchangers, vessels, compressors, filters, ion exchange, dryers, mixers), bounded references only (Phase 1, PRs #5 and #9, not yet merged). **Costing:** 13 Garrett curves Charlie uses were checked against the printed charts; 6 failed and were corrected (GARRETT-V01/C01, PR #7). R-101 was checked against public $/kW sources (PR #15, COST-DATA-V01). **Remaining:** OpenPyTEA's 421 models have upstream parity only; their Seider, Turton, Towler and Perry sources have not been checked (needs the textbook tables). 10 of Charlie's 28 lines use OpenPyTEA |
| A2 | All material costing sources have valid scope, year, currency and method | **PASS** | 594/594 models carry the required fields (`reproduce_g3.py` catalogue check). OpenPyTEA: 421 USD with scopes; 18 disabled and marked unresolved. Nottingham: 15 GBP with year and page. Garrett: scope, USD, CE 320 and early 1987 are fixed in code, with a page per curve. **Caveat:** all 154 Garrett curves still carry `review_status = Unverified`. The 13 checked curves are recorded in GARRETT-V01, not in that field |
| A3 | Reference plant reaches the coverage target (95% of verified scope) | **PARTIAL** | Priced by a stated method: Charlie 28/28; **Team 8 (held out) 7/7**; 0 unpriced on either. **M3.7 tiers:** Charlie, 2 source supported (7% of items, 70% of value) and 26 assumption based; Team 8, 1 source supported (14%, 23%) and 6 assumption based. The 95% target is met only when assumption-based prices count. A reviewer should decide whether that satisfies A3 |
| A4 | Every unpriced item is visible, with its potential significance assessed | **PASS** | **Visible:** totals keep missing items missing, and the Basis of Estimate lists each one with its reason as "unknown, not zero". **Significance (M3.7):** each unpriced item gets an indicative band from comparable priced items in the study, shown as a share of priced equipment and compared with the estimate class's narrowest typical high range. The band is never added to a total (`test_coverage_tiers.py`). Charlie has no unpriced items |
| A5 | Reported estimate class consistent with documented design maturity | **PASS (provisional)** | M3.5 (PR #18) proposes the class from declared deliverables, and a reviewer confirms it. Charlie: Class 4 with feasibility deliverables declared; the founder must confirm the declarations. The checklist must be checked against AACE 18R-97 Table 3 once the RP is purchased |
| A6 | Basis of Estimate identifies scope, exclusions, assumptions and uncertainty | **PASS** | M3.6 (PR #19): 10 sections generated from the saved study. Charlie's report reconciles to total CAPEX and lists 5 open items |
| R1 (rev 1.1) | Missing inputs → labelled assumptions, reported as a separate tier with stated confidence | **PASS** | M3.7: four tiers per line, by count and value, each with a stated confidence in words (no uncalibrated number), in the equipment result and the Basis of Estimate ([M3.7 record](M3.7-coverage-tiers.md)). Founder decided 12 Nov 2026 to keep the strict rule: AI-estimated physical properties count as assumptions. No UI view yet |
| R2 (rev 1.1) | Alternative correlations kept; user can switch and re-run; change recorded | **PASS** | Alternatives listed per line. A user's choice is recorded as `model_selection {origin: "user"}` and protected from AI re-matching (PR #8; `test_library_preference.py`) |
| R3 (rev 1.1) | Coverage shown on a reference project not used for tuning | **PARTIAL (12 Nov)** | Team 8 is withdrawn (it had shaped the prompts). The founder's unseen PEM hydrogen workbook first exposed three faults: a parser header bug, design basis not reaching the AI, and an untagged RO unit hidden by 100% coverage. All three are fixed. After the fixes: 2/2 units priced, RO out of scope by founder decision, all checks pass ([record](../phase5/heldout_pem_run_2026-11-12.md)). Because its findings drove the fixes, one more unseen workbook should confirm R3 |

## 2. Required tests

| ID | Test | Status | Evidence |
|---|---|---|---|
| T3-1 | Independently established equipment cases: purchased and installed costs, factors, escalation | **PARTIAL** | Garrett printed-source checks (13 curves) and installation metadata on every curve. Escalation: CPI values against BLS; CEPCI 1987 and 2000–2024 against the publisher (COST-DATA-V01). OpenPyTEA source checks are pending |
| T3-2 | Duplicate tags, missing equipment, historical cost years, installed-versus-purchased boundary | **PASS** | `reproduce_g3.py` groups: duplicate tags 5 passed; missing / unpriced 6; cost years and escalation 42; installed / purchased 27 |
| T3-3 | Capital breakdown against a reference project with independently established scope | **PASS (scope), magnitude noted** | Compared with Charlie's own economics study (independently prepared; private, not used as a price source). **Categories:** every category in the study maps to a FlowValue category (table below). Legal fees, owner's costs and land have no FlowValue source and are reported as a gap, not zero. **Magnitude:** see the ratio table below |
| T3-4 | Installation costs not double-counted where a method already embeds them | **PASS** | Charlie: all 4 double-count checks pass and the breakdown reconciles. Unit tests: M3.4 fixtures (`test_capex_scope.py`) and `test_installation_costs.py` |

**T3-3 magnitude (fixed capital / purchased equipment, each on its own basis):**

| Basis | Ratio |
|---|---|
| FlowValue, Garrett minimum factors | 2.51 |
| FlowValue, Nottingham Lang screening comparison | 3.60 |
| Charlie economics study (its own factor set) | 4.29 |

Garrett's minimum factors are the low bound; midpoint and maximum stop for confirmation of the offsite allowance, an intended guard. The study's factor set sits above Lang. The factor choice is a user or AI decision recorded in the Basis of Estimate, not a defect. A reviewer should confirm which factor basis the study intends.

**Category map, Charlie economics study → FlowValue M3.3:**

| Study | FlowValue |
|---|---|
| Purchased equipment | `purchased_equipment` |
| Installation | `installation` |
| Instrumentation and control | `instrumentation_control` |
| Piping | `piping` |
| Electrical | `electrical` |
| Yard improvements | `yard_utilities_offsites` |
| Service facilities | `yard_utilities_offsites` |
| Buildings | `buildings` |
| Land | `land` |
| Engineering and supervision | `engineering_supervision` |
| Construction expenses | `construction_overheads` (Garrett combines this with engineering) |
| Legal fees | `owners_costs` (gap: no registered factor) |
| Contractor's fee | `contractor_fee` |
| Contingency | `contingency` |
| Working capital | `working_capital` |
| — | `civil_structural`, `environmental_controls`, `startup_commissioning` (in FlowValue, not in the study) |

## 3. Implementation work and milestones

| Item | Status | Where |
|---|---|---|
| Equipment engineering, priority families | PARTIAL | Phase 1 sizing references; Charlie's 7 originally unpriced items are now priced (in range or floored) |
| Cost correlations: documented scopes, material and pressure factors, dated escalation, currency, quotations | PASS, except escalation basis | Scopes (#16), FX for Nottingham GBP, user comparables. CEPCI series added (#16) but has no 2025/2026 value, so prices use the CPI proxy |
| Scope completeness (17 categories) | PASS | #16. Owner's costs is a visible gap |
| Estimate maturity, proposed not certified | PASS (provisional checklist) | #18 |
| Uncertainty tied to maturity, quotes and evidence | PARTIAL | Class range plus wide-end reasons (#18). Not yet narrowed or widened numerically by quotes or statistics. Monte Carlo (#13) is not yet linked to the class |
| M3.1 Priority sizing library | PARTIAL | As A1 |
| M3.2 Source-controlled costing catalogue | PARTIAL | Garrett 13/154 checked and 6 corrected; OpenPyTEA source checks pending |
| M3.3 Capital breakdown | PASS | #16 |
| M3.4 Purchased / installed overlap controls | PASS | #16 |
| M3.5 Estimate maturity | PASS (provisional) | #18 |
| M3.6 Basis of Estimate | PASS | #19 |
| M3.7 Assumption tier and switchable correlations | PASS | Switching: #8. Tiers and unpriced significance: [M3.7 record](M3.7-coverage-tiers.md) |

## 4. Path to G3 (in order)

| # | Action | Owner | Unblocks |
|---|---|---|---|
| 1 | Review and merge, in order: #3, #4, #5, #6, #7, #8, #9, #14, #15, #16 → #18 → #19 → this pack | Founder, E2 review | Everything; the pack runs on the merged code |
| 2 | ~~Build the M3.7 assumption tier and the A4 significance band~~ Done (M3.7); founder kept the strict assumption rule | E1 → founder | R1, A4 |
| 3 | ~~Freeze matcher prompts and rules, then run Team 8 once~~ Done 12 Nov 2026 ([record](G3-R3-team8-heldout.md)) | E1, founder go-ahead | R3 |
| 4 | Supply a 2025 or 2026 CEPCI value (issue and page) | Founder | Escalation basis, T3-1 |
| 5 | Supply Seider 2016 Table 16.32 / §16.5 and Turton 2018 App. A tables, then check the OpenPyTEA models Charlie and Team 8 use | Founder → E1 | A1, M3.2 |
| 6 | Confirm Charlie's design-maturity declarations and CAPEX factor basis, and record the class review | Founder / reviewer | A5, T3-3 |
| 7 | Independent reviewer runs `reproduce_g3.py` (with Charlie and Team 8) and signs below | Reviewer | Gate |
| 8 | Purchase AACE 18R-97 and check the deliverable checklist against Table 3 | Founder → E1 | A5 provisional → final |

Items 4, 5 and 8 depend on material only the founder can obtain. Items 2 and 3 are done. Item 5 now matters more: OpenPyTEA prices 6 of Team 8's 7 items.

## 5. Sign-off

| Role | Name | Decision | Date |
|---|---|---|---|
| Engineer 1 | | Prepared; recommends NOT YET PASSED | 12 Nov 2026 |
| Engineer 2 | | | |
| Independent reviewer | | | |
| Founder | | | |

Private evidence (Charlie sizes, prices and the economics study values) stays on the founder's machine and is not committed.
