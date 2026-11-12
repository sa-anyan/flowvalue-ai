# G3 · R3 held-out run: Team 8

**Date:** 12 November 2026 · **Owner:** Engineer 1, with the founder's go-ahead · **Criterion:** roadmap rev 1.1 R3, "coverage shown on a reference project not used for tuning"; also A3 and T3-2 · **Code:** commit `069aab0` (PR #25)

## Why Team 8

Charlie shaped the Phase 3 matcher: the OpenPyTEA preference, the below-range prompt and the minimum-size floor. Team 8 was named the held-out project in the G0 sign-off (S1). Its workbook was used in October 2026 parser work, before Phase 3, but never in matcher or pricing tuning.

## Freeze

The matcher and pricing rules were frozen at commit `069aab0` before the run. No code changed between the freeze and the run.

| Area | Git tree at freeze |
|---|---|
| `backend/equipment_matching` | `7625dae35817` |
| `backend/equipment_resolution` | `aac73d4c55cf` |
| `backend/equipment_costing/unit_conversion/bridges` (AI sizing inputs) | `69cf2a62c8a3` |
| `backend/blocks/equipment` | `af5aba6c5c6d` |
| `backend/orchestration/planning_context.py` | `d75b63c6d752` |

## Run

- **Source:** `Mass Balance Team 8.xlsm`, SHA-256 prefix `f2d297f62d8b5a61`. The file is private and stays local.
- **Database:** a new scratch database, separate from the app's database. No process description was given, so nothing written for this run steered the AI.
- **Stages:** engineering data (AI on), then engineering approval, then equipment (AI on), then CAPEX. CAPEX used the Charlie check's settings: Garrett, delivered, mixed process, minimum factors.
- **Engineering approval was given by the script for this run.** The founder has not reviewed it.
- **Run once.** An earlier attempt could not reach the AI because of a TLS certificate problem in the scratch Python environment, not in FlowValue. The AI matching batch returned `unavailable`, and no item was priced. That attempt is not counted. The run below is the first one with the AI reachable.

## Results (counts and ratios only)

| Check | Result |
|---|---|
| Scope | The Mass and Energy Balance sheet is a 7-unit wastewater treatment plant. Three other sheets (sizing, enzyme, liquefaction CAPEX) belong to a separate bioethanol plant. **FlowValue's scope notes identified them as separate and did not merge them.** |
| Register | 7 of the 7 tagged units in the balance. The workbook has no other tags |
| Priced by a stated method | 7 / 7 (100%); 0 unpriced |
| AI matching | 1 batch, completed. Every match is flagged `ambiguous` for review, mostly because tank configuration (roof, material, pressure) is not stated. None is hidden |
| Library | OpenPyTEA 6, other 1 (an EPA pH-adjustment model) |
| **M3.7 tiers** | Source supported 1 (14% of items, 23% of value); assumption based 6 (86%, 77%) |
| Assumption reasons | Minimum-size floor 3; AI-estimated sizing inputs 6 (residence time, working fraction, hydraulic loading); AI inputs as the only reason 3 |
| Source caveats | Provisional model scope 7; CPI proxy 7 |
| Double-count checks | 4 / 4 pass; breakdown reconciles |
| Estimate class | Class 5 proposed. No design maturity was declared, so only derived evidence counts |
| Fixed capital ÷ purchased equipment | 2.80 (Garrett minimum factors) |
| Basis of Estimate | Generated, current; 5 open items |

## What this shows

- **R3 met.** Coverage is shown on a project not used for tuning: 100% priced by a stated method, no unpriced items, and nothing concealed.
- **The held-out project behaves like Charlie.** Coverage is complete by stated method, but most items rest on assumptions: 6 of 7 here, 26 of 28 on Charlie. The 95% target is reached only when assumption-based prices count.
- **Scope handling held.** The unrelated bioethanol sheets were recognised and kept out, so there was no false "missing equipment" and no double counting.
- **OpenPyTEA's weight grows.** 6 of 7 Team 8 items use OpenPyTEA, whose textbook sources are still unchecked (A1). This makes the Seider and Turton source checks more pressing.

## Reproduce

Copy the private workbook into a new study in the app, run engineering data and equipment with AI, approve, and set the CAPEX settings above. Then run:

```bash
python docs/verification/phase3/g3_review/reproduce_g3.py --study PATH.sqlite3 --assessment KEY
```

The script re-prices a temporary copy without AI from the saved matches.
