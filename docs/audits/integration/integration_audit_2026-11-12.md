# FlowValue AI integration audit · 2026-11-12

**Scope.** Compare the onboarding vision and G0–G4 evidence at main `84800be` with all requested work combined, E1-only, and E2-only. The integrated tree connects engineering evidence, sizing and pricing, CAPEX, Revenue/OPEX, and saved financial exports. Independent source validation and consistent stale-result presentation still limit the vision of an auditable study. This is an audit branch for review. Gate authority remains with Engineer 1 and the founder. No private workbooks, study values, or live services were used.

## Reproducible branch assembly

Integrated test tip `4769049`, E1-only `f51adee`, E2-only `2824358`. E2-only includes E1 #4 and #5 as inherited parents of #11 and #12. The control contains the requested E2 heads with their published ancestry. E1-only includes the two E1 decision documents. Only the integrated branch is published.

The following PR heads were merged locally in this order. The only conflicts were in #9, in both integrated and E2-only. Retained the existing governance version of `docs/phase-0/02-capability-register.md` (CI runs Python and both Node test formats) and `docs/phase-0/08-requirements-register.md` (retain R20/R21). The other hunks auto-merged. Resolutions `dd1563d` and `56f348f`. No numerical or policy conflict required a side to be selected.

| PR | Head branch | Pinned head |
|---|---|---|
| #4 | `e1/g0-gate-decision` | `96ad7fc3` |
| #11 | `engineer-2/g0-governance` | `18d2bbcd` |
| #5 | `e1/p1-g1-completion` | `410671ea` |
| #12 | `engineer-2/g1-scope-agreement` | `0fd04a4b` |
| #3 | `e1/b08-decisions` | `470ed4ae` |
| #6 | `e1/b07-decisions` | `25bdd30c` |
| #9 | `engineer-2/development` | `95144943` |
| #21 | `engineer-2/b07-costing-parity` | `5840d781` |
| #10 | `engineer-2/b09-versioning` | `cf4d32ed` |
| #24 | `engineer-2/p2-stream-schema-evidence` | `20c939e6` |
| #23 | `engineer-2/p2-assumption-provenance-evidence` | `44d881cf` |
| #22 | `engineer-2/p2-g2-fixture` | `2791e703` |
| #26 | `engineer-2/p2-m23-provenance-tests` | `787b732b` |
| #27 | `engineer-2/p2-m24-dependency-regressions` | `d1644da5` |
| #28 | `engineer-2/p2-m21-stream-contract-tests` | `8f936f2b` |
| #30 | `engineer-2/p2-g2-integration-fixture` | `338f021b` |
| #31 | `engineer-2/p2-m25-version-isolation-tests` | `ed3c8b4d` |
| #32 | `engineer-2/p2-g2-acceptance-matrix` | `727c7818` |
| #33 | `engineer-2/p2-g2-numerical-finance-mutation` | `2a833838` |
| #34 | `engineer-2/p2-m25-historical-read-tests` | `e782466f` |
| #8 | `e1/prefer-openpytea` | `d1e776e0` |
| #7 | `e1/p3-garrett-source-check` | `65d311ec` |
| #14 | `e1/below-range-floor` | `3fb7b45e` |
| #15 | `e1/r101-electrolyser-review` | `7408a8e4` |
| #17 | `e1/charlie-pipeline-fixes` | `66cfa6b5` |
| #16 | `e1/m3-capex-scope` | `b7af0eb7` |
| #18 | `e1/m3-estimate-class` | `587b0219` |
| #19 | `e1/m3-basis-of-estimate` | `fcf78988` |
| #20 | `e1/g3-review-pack` | `4aec61d5` |
| #25 | `e1/m3-7-assumption-tier` | `25b2a963` |
| #29 | `e1/p4-audit` | `5332e3bf` |
| #13 | `e1/ux-guided-flow` | `72514bcc` |

## Verification

Windows, Python 3.12.14 test venv, Node 24.22.1, AI/cloud disabled, isolated SQLite and temporary directories. Frontend checks used the installed packages from an identical lockfile. Full backend command was `python -m pytest backend -q -ra --tb=short --basetemp <unique>`. Frontend commands were `tsc --noEmit --incremental false`, `node --test` and `next build --webpack`. G3/G4 reproducers ran their public fixture paths. The private-study arguments were omitted.

| Check | Integrated | E1-only | E2-only |
|---|---|---|---|
| Full backend | 4,520 passed, 0 failed, 9 skipped, 367 subtests passed | 4,370 passed, 5 failed, 9 skipped, 367 subtests passed | 4,370 passed, 0 failed, 9 skipped, 367 subtests passed |
| TypeScript / production build | Both exit 0 | Both exit 0 | Both exit 0 |
| Node tests | 56 passed, 0 failed/skipped | 55 passed, 0 failed/skipped | 46 passed, 0 failed/skipped |
| P2 matrix (five selections) | 21 passed, 0 failed/skipped | Matrix and selections absent | 21 passed, 0 failed/skipped |
| G3 public reproduction | 165 passes across ten groups, 0 failures/skips | Same | Script absent |
| G4 public reproduction | 172 passes across eight groups, 6 subtests, 0 failures/skips | Same | Script absent |

The first G3/G4 attempts had setup errors when pytest subprocesses shared a temporary base. The rerun used a fresh pytest temp root per script sequence and exited 0 on both trees. The public catalogue check found 594 models with required fields and no 2025/26 CEPCI observation. The check verifies catalogue metadata. Independent correlation validation remains open. Private-study replay and browser verification were outside these results.

Each backend run emitted one Starlette TestClient deprecation warning. The nine skips on each tree were one private equipment workbook, one private scenario snapshot, six private workbook cases and one optional pinned OpenPyTEA comparison. E1’s first run reached 100% but stalled at teardown. Its completed rerun used `-p no:cacheprovider`. A focused rerun with `pytest backend/tests/test_unit003_active_conversions.py -k prior_alias_bindings_unchanged` reproduced the five failing cases (557 passed, 5 failed). The same selection on the integrated tree passed all 562. All are in `backend/tests/test_unit003_active_conversions.py::test_prior_alias_bindings_unchanged`, parameter IDs `ALIASES-delta_\\xc2\\xb0C`, `ALIASES-delta_\\xc2\\xb0F`, `ALIASES-\\xc2\\xb0C`, `ALIASES-\\xc2\\xb0F`, and `ALIASES-\\xc2\\xb0R`. Failure output was `UnitResolutionError: Unsupported or unrecognized unit` followed by the misdecoded alias (e.g. `delta_Â°C`). PR #9’s `9bec52d` explicitly reads the UTF-8 fixture and the failures are absent on both trees containing it. No production unit rules changed in the audit.

## Behaviour overlaps

| Overlap | Combined result and remaining check |
|---|---|
| Optional CAPEX/Revenue → OPEX (#27/#30, #29) | `execution.input_fingerprint` still includes the available optional bases; the runner supplies only fresh optional outputs. #29's Revenue result no longer includes unrelated configuration, which removes the run-order input identified in G4. The public mutation cases are the evidence for staleness; receipt authority remains parked. |
| Equipment identity (#21 vs #14/#17) | Record-key duplicate guards and distinctness remain in the costing boundary. Floors operate on the chosen estimate's size, with quantity and scope tracked separately. Confirmed same-tag prices and a catalogue floor are different fixtures; require a real cross-case before accepting independent costing coverage. |
| Minimum-size floor and OpenPyTEA (#8/#14/#17) | User-selected models remain protected. Minimum-size checks verify pricing behaviour and disclose floor use. They cannot validate a correlation or turn a floor assumption into supported design evidence. |
| Stale equipment report (#9) and guided UX (#13) | API report projection and HTML report honour `result_is_stale`. Guided workspace reads that flag and shows a separate saved-but-stale status. Typecheck and Node tests cover the composed frontend; browser-to-export parity remains open. |
| Snapshots (#31/#34/#10) and financial workbook (#29) | Historical reads, named-version forks and receipt prototypes are separate from the financial workbook, which reads the saved financial ledger. **Conflicting presentation, already present in E1-only.** In both trees, a 24→48 h synthetic hold-up edit yielded `Stage stale True` while the exported Summary said `calculated_preliminary` and reconciliation was `True`. The route calls `view`, but `financial_workbook._result` discards the stage envelope and reads retained results. Workbook arithmetic reconciles the old ledger. There is no receipt lineage in this workbook. |

## Gate decision matrix

| Gate | Classification of the open items |
|---|---|
| G0 · [decision](../phase0/g0_gate_decision_2026-11-11.md) | **Needs sign-off only:** S2 requirements and S3 capability register have a recorded E2 choice in #11. **Still open:** S1 source permissions, hashes, confidentiality and independent truth set. S4 joint baseline and skip disposition, including T-05 log/fixture policy, remains open. Governance wording conflict was resolved in the audit, but an approved merge must retain it. |
| G1 · [acceptance matrix](../../verification/phase1/method_acceptance/G1_engineer1_acceptance_matrix.md) | **Resolved by integrated code:** METHOD-LEGACY01 and SIZE-XF01/XF02 were addressed in merged #2; #9 adds TRACE02 and APP01, which supplement TRACE01 from #2. The combined run covers `test_legacy_sizing_boundaries.py`, `test_sizing_cross_file.py` and `test_engineering_method_versions.py` at `4769049`. **Still open:** independent sign-off on the pinned reference set, physical applicability and source-snapshot trace beyond the covered exports. #12 records E2 agreement with the sizing/unit/bridge scope; obtain formal gate acknowledgement. |
| G2 · [acceptance matrix](../../p2-g2-acceptance-matrix.md) | **Resolved by integration for public fixture execution:** separated M2.1/M2.3/M2.4/M2.5 and synthetic G2 tests ran together at `4769049` (21 public matrix cases). **Still open:** three real workbook structures plus a manual process and conflicting-unit/schedule parity; E1 acceptance and browser/XLSX identity review; critical-field provenance and locked assumptions across consumers; full approved mutation with independent results through UI/export; historical conversion/rollback and isolated cloud transaction parity; receipt activation. #33 adds synthetic exact financial mutation evidence, separate from a signed study. |
| G3 · [gate review](../../verification/phase3/G3_gate_review_2026-11-12.md) | **Resolved in the branch record:** held-out Team 8 run (R3) and assumption tier/significance band (R1/A4) are already recorded by #25's stack at `fa212ca`. Public `reproduce_g3.py` passed, including coverage-tier tests. **Still open:** A1/T3-1/M3.1/M3.2 independent OpenPyTEA checks and remaining curve-source coverage; A3 ruling on 95% verified scope vs assumption-based prices; minimum-size engineering basis; published 2025/26 CEPCI or explicit CPI disposition; A5 AACE Table 3 and maturity confirmation; T3-3 factor/estimate basis, missing cost scope, and uncertainty linkage to quotes/Monte Carlo. **Needs sign-off only after evidence:** independent rerun and reviewers' decisions. |
| G4 · [gate review](../../verification/phase4/G4_gate_review_2026-11-12.md) | **Conflicting:** stale workbook label reproduced on E1-only and integrated; see overlap table. **Still open:** dedicated UI fields for contract term, shared-stream/overlap reviews, payment owner and escalation basis; line-specific escalation is recorded only; server restart after authorized integration; inherited G3 CAPEX accuracy. Discount and tax inputs are planning defaults. **Needs sign-off only within G4's stated scope after reproducibility is reviewed:** E2, independent reviewer and founder. |

## Recommended review and merge order

1. **G0/G1:** review #4 → #11 and #5 → #12 as governance stacks, #3/#6 as decision records and #9 as the shared development baseline. Preserve the two register resolutions. #2 is already in main.
2. **G2:** #21 then the independent contract/preflight and history evidence (#26–#28, #30–#34), retaining #24/#23/#22 where their tests provide distinct coverage. #10 remains prototype scope until explicitly authorized. Do not close a smaller draft solely because a later test overlaps; compare assertions and remove only demonstrated duplicates.
3. **G3:** #8/#7/#14/#15/#17, then #16 → #18 → #19 → #20 → #25. #17 contains #8 and #14 by ancestry, so those two can be closed as superseded if #17 is approved and integrated intact; #7 is not an ancestor and needs separate review. Review floor policy, source validity and escalation before gate closure.
4. **G4 and UX:** #29 after #25; #13 separately and last in the combined stack. Review saved-ledger reconciliation and browser/export parity on the actual integrated candidate.

**Needs Engineer 1.** Agree G0 S1/S4 and record remaining S2/S3 sign-offs; confirm G1 reference and trace scope; approve an independent G2 ledger and historical/cloud verification plan; rule on G3 floor/verified scope, source checks and CEPCI; decide whether to block or explicitly label stale XLSX, then coordinate independent G4 review and founder approval.
