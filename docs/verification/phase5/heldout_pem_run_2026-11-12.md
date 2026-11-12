# Held-out run: PEM hydrogen workbook — 12 November 2026

**Owner:** Engineer 1, on the founder's instruction · **Gates:** G3 (R3 held-out coverage) and G5 (live-model evaluation) · **Code:** `e1/p5-audit` at `6060d6f` (PR #35), plus the two fixes recorded below

## Source and pre-checks

- **Workbook:** an industrial PEM hydrogen M&E balance from the founder. It is a QA reference, illustrative and location neutral, laid out like the Charlie template. SHA-256 prefix `2e8b33f2ea54c693`.
- **Contents:** 6 sheets, 7 streams, tagged units EL-101 (PEM electrolyser) and HE-101 (coolant heat exchanger), plus an untagged RO unit.
- **Formulas:** all 280 have saved values.
- **Not seen before:** never opened in FlowValue. Neither tag appears in any AI module; this is enforced by `test_prompts_contain_no_project_equipment_tags`.
- **Caveat:** the layout follows Charlie, and the matcher's general electrolyser rule came from Charlie. The workbook is unseen, but not fully independent of the tuning project.
- **Run setup:** a scratch database; no process description and no Revenue Box (a cold start); AI on; engineering approval given by script.

## Results

| Stage | Outcome |
|---|---|
| Engineering data | First attempt **failed** (finding 1, fixed). After the fix: 7 streams and 2 equipment items; the AI review completed |
| Equipment | EL-101 matched to OpenPyTEA PEM electrolyser (DOE 2016) at 2,400 kg/day: correct, in range, inputs from the study. HE-101 matched to a plate-and-frame exchanger: heat duty 1,611 kW (matches the workbook's thermal duty); 7 inputs are AI-labelled assumptions |
| CAPEX | Ready; 4 of 4 double-count checks pass; reconciles; Class 5 (no declarations); fixed capital ÷ equipment 2.51. **The RO unit is missing** (finding 3) |
| Revenue, finance | Stop and ask for a Revenue Box: correct behaviour |
| OPEX | Ready (partial). Electricity basis wrong by 0.9% (finding 2) |
| Run-to-run variance (M5.7) | Matching only: 3 uncached runs gave identical model choices for 2 of 2 items. **With the priced outcome added (see finding 9): 1 of 2 items differs across runs (share identical 0.5)** |
| AI decision log (M5.6) | Every call logged with model and fingerprints. The matcher's prompt version was missing (finding 6, fixed) |

## Findings by phase

| # | Finding | Phase (milestone) | Owner | Status |
|---|---|---|---|---|
| 1 | **A valid .xlsx was rejected as "Malformed or unsupported Excel workbook".** The writer omitted the optional `<dimension>` record, so read-only openpyxl reports no sheet size and `rows × cols` raised `TypeError`. The generic message hid the cause | **P2** (workbook ingestion) | E2 area; fixed by E1 | **Fixed:** the sheet is measured when the size is absent, and limits still apply. `test_workbook_missing_dimension.py` |
| 2 | **Design-basis values never reached the AI.** (Root cause corrected: the parser does keep these cells; the OPEX/CAPEX AI context listed a cell layout but never included the cells.) Mass Balance 1, Energy Balance 1 and Sources and Assumptions are standard "Parameter / Value / Unit" tables, but they are skipped as "no supported engineering table". Their values (55.5 kWh/kg, 85% RO recovery, coolant Cp 4.18, temperatures) never reach the AI. **Effect:** the OPEX AI said "No measured electrical duty is provided" and assumed 55 kWh/kg (0.9% low), and the exchanger Cp was AI-estimated although the workbook states it | **P2** (data architecture); seen in **P4/P5** (grounded accuracy) | E1 | **Fixed:** `ingestion/design_basis.py` extracts parameter tables with their cells; the AI receives them as `workbook_design_basis` with an instruction to cite them (prompt `engineering-orchestrator-6`). Verified: the AI now cites Mass Balance 1!C9, 55.5 kWh/kg, 5,550 kW |
| 3 | **An untagged unit is missing from the register and the CAPEX.** The RO unit is named in three stream descriptions and on the cover page. The AI review noticed it in a scope note ("No separate RO equipment tag…") but did not register it. CAPEX then reports 100% coverage and no unpriced items, so the missing unit is concealed by the metric | **P2** (M2.6 identification), **P3** (completeness guard: G3's core claim), **P5** (workbook-engineer specialist) | E1 (guard); E2 (identification) | **Guard fixed:** `register_completeness.py` flags equipment families named in source text but absent from the register. Coverage is then not complete, the 95% target is not met, and the Basis of Estimate lists the unit. Cleared by adding the unit or recording a decision with a basis (`plan.register_review`). Verified: RO flagged. Registering untagged units automatically (E2) is still open |
| 4 | **Composition check is inconsistent** (resolved by the finding 9 fix: all 7 streams now flagged). The workbook's "mol %" columns hold fractions (1 = 100%). FlowValue flagged streams 5–7 ("sum to 0.01, not 1") but not streams 1–4, which have the same issue | **P2** (validation) | E2 | Open |
| 5 | **The workbook's own Balance Check sheet is not recognised.** All FlowValue mass and energy checks are "unresolved" because no boundary is declared | **P2/P6** (supported formats) | E2 | Open (limitation) |
| 6 | **Matcher prompt version missing from the AI decision log.** The matcher uses the key `task`. The revenue call carries no version key in its request; its instructions fingerprint still pins the prompt | **P5** (M5.6) | E1 | **Fixed** (`task` recognised); revenue: minor, open |
| 7 | **The AI under-staffs continuous operation again:** 4 operator FTEs for 24 h × 314 days, the same as Charlie's F2. This is a systematic tendency of the operating adviser | **P4/P5** | E1 | Open |
| 8 | The AI added an RO and balance-of-plant electricity allowance (0.5 kWh/kg) that the workbook explicitly excludes. **Disclosed** in its rationale | P4/P5 (boundary behaviour) | Founder review | Review item, not a defect |

| 9 | **Unstable AI input routing; root cause in the parser.** EL-101 was priced in one run and unpriced in the next. The router said only oxygen and RO-feed measurements were available. **Cause:** the deterministic parser read no flows for streams 1–4, because a stray partial "Component" row sat above the real subheader of that block. The hydrogen stream's flow existed only when the AI workbook review happened to recover it | **P2** (parser robustness), seen as **P5** variance | E1 (fixed in E2's parser area) | **Fixed:** `repeated_stream_blocks.py` picks the candidate header with the most recognised property columns. All 7 streams parse; streams 1–4 also now get the mol% check (finding 4 resolved). Verified: a fresh run priced EL-101, and 3 uncached repeats agreed on both items, including whether they are priced (share identical 1.0). Test: `test_stray_partial_component_row_does_not_hide_stream_flows` |

**Workbook-side issues** for the workbook's author: the "mol %" columns contain fractions, and the coolant streams' h column shows hydrogen HHV values.

**Correct behaviour observed:**

- EL-101 identification, sizing and model choice;
- heat duty agreeing with the workbook;
- hot-side temperatures (not in the workbook) labelled as assumptions;
- revenue and finance refusing to proceed without a Revenue Box;
- a stable AI across runs;
- double-count checks and reconciliation passing.

## Gate consequences

- **G3, R3 (held-out coverage): not met.** The run shows 100% coverage, but against an incomplete register (finding 3). Fix finding 3, then re-run.
- **G5:** the guard suite holds and variance is stable. One grounded-accuracy failure (finding 2) traces to the parser, not the model. **Critical approval-bypass failures: 0.** Thresholds for noncritical errors are still to be set by engineering experts.

## Post-fix verification run (not the held-out evaluation)

After fixing findings 2 and 3, the workbook was run again on a fresh scratch database. This run verifies the fixes; it is not counted as held-out evidence.

- **Design basis:** the AI cites Mass Balance 1!C9 and uses 55.5 kWh/kg; the RO electricity it had added is gone.
- **Register completeness:** the RO unit is flagged, coverage is not complete, and the Basis of Estimate shows the open item.
- **New finding 9:** EL-101 was unpriced in this run because of unstable input routing.

Tests: `test_heldout_fixes.py` (6), `test_workbook_missing_dimension.py` (2), and the variance test updated. Full backend suite: 4,353 passed, 3 skipped.

## Second verification run (after the parser fix)

- All stages behave as expected. EL-101 is priced at 2,400 kg/day, and the AI cites 55.5 kWh/kg from Mass Balance 1!C9.
- The RO unit is flagged.
- Variance: 3 uncached repeats, 2 of 2 items identical, including whether they are priced.
- **Remaining variance:** across separate full runs, HE-101 matched different valid exchanger types: plate-and-frame in the held-out run, shell-and-tube here. Both fit the duty; the choice should be confirmed per item by the user (M5.7 per-item confirmation).

## Founder decision on the RO unit and G3 evidence

- **Decision (founder, 12 Nov 2026):** RO pretreatment is out of scope for this estimate. It is recorded in `plan.register_review` with that basis; no engineering reason is recorded yet. The Basis of Estimate lists it under "Units excluded by decision".
- **G3 checks on the second verification study:**
  - 2 of 2 units priced and in range, 0 unpriced;
  - register complete (RO excluded by decision);
  - 4 of 4 double-count checks pass, and the breakdown reconciles;
  - tiers: 1 source supported (99% of value), 1 assumption based;
  - Class 5 proposed.
- **R3 status: PARTIAL.** Coverage holds on a project not used for matcher tuning. However, this workbook's findings drove three general fixes (parser header choice, design basis to the AI, register completeness). A reviewer may reasonably treat it as no longer held out. Recommendation: confirm R3 on one more unseen workbook, run once on the current code.
