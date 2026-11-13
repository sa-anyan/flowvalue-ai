# Phase 6 delivery evidence register — 12 November 2026

**Status: working evidence ledger, not a gate approval.** Owner: Engineer 2. Baseline: `engineer-2/development`. Formal P2/G2 integration acceptance remains open. Integration audit PR #36 is draft; no P6 draft has been merged.

## Evidence by milestone

| Milestone | Draft evidence | Current verified scope | Outstanding for implementation and G6 |
| --- | --- | --- | --- |
| M6.1 validated Excel/CSV import | #37 | Source-linked Excel handoff regression tests; CI passed | Verify CSV-specific route, independently sourced workbook and CSV fixtures, unsupported columns and reproducibility |
| M6.2 DWSIM adapter | #39 | Adapter specification; CI passed | Verify whether native `.dwxml` parser is active, declare exact source versions, obtain permitted native/Excel exports, implement adapter with independent expected outputs |
| M6.3 Aspen export adapter | #39 | Aspen Plus/HYSYS export specification; CI passed | Obtain permitted exports and versions for each product; implement source-specific parser and reconciliation; no native Aspen model execution |
| M6.4 mapping/reconciliation | #41, #42, #43, #44 | Spec, active backend audit, pure read-only preview helper and UI component; #41–#44 CI passed | Review integration contract, connect preview to approved P2 model, reconcile conflicts and unit bases, add per-observation approval receipts, browser tests |
| M6.5 source-linked 2D process representation | #38 | No-fabricated-connectivity regression tests; CI passed | Inspect active schematic, verify source-backed vs mention/inferred rendering, independent visual tests and approved link status |
| M6.6 reviewed 3D | #40 | Geometry/connection contract; CI passed | Approved geometry evidence, permitted dimensions/coordinate frames, renderer, review workflow and tests; not implemented |

**Important:** Passing CI confirms repository checks, not simulator-specific fidelity, independent fixture reconciliation, approved project baseline, or formal G6 acceptance.

## G6 acceptance evidence required

1. **Fixture manifest** per declared supported import family: source software/version, export format/version, hash, permission to use, owner, independent expected observation set, accepted fields and declared omissions.
2. **Reconciliation reports**: 100% of *declared supported fixtures* imported and reconciled to expected outputs, with missing/conflicting/unsupported fields visible and no silent physical reinterpretation.
3. **Provenance and version tests**: source file unchanged, source cell/object evidence, canonical mapping decisions and reviewer receipt tied to source hash and project revision; deterministic replay from originals.
4. **2D/3D truth tests**: verified physical links require source-supported reviewed endpoints; inferred, mentioned, unresolved or illustrative geometry clearly distinguished; no invented piping or plant layout.
5. **Formal gate signoff**: P2 integration owner, engineering reviewer and designated G6 authority record approvals. CI is not a substitute.

## Blocking inputs and owners

| Dependency | Who supplies/approves | Can Engineer 2 continue without it? |
| --- | --- | --- |
| Approved P2/G2 canonical model and revision/approval integration baseline | P2 integration owner / formal reviewer | Yes: isolated pure helpers, synthetic tests, documentation; no production acceptance or merge |
| DWSIM native and Excel sample exports with exact version and expected results | User or licensed simulator operator | Yes: adapter scaffolds and negative tests only; no supported-version claim |
| Aspen Plus and HYSYS permitted tabular exports, source versions, expected results | User or licensed simulator operator | Yes: format research/specification only; no accepted adapter |
| Real independent import fixtures (including CSV), confidentiality clearance | User / engineering reviewer | Yes: synthetic coverage; not G6 fixture signoff |
| Reviewed equipment dimensions, geometry references and source-backed connections | Engineering design owner | Yes: illustrative visual concepts; not reviewed 3D |
| Formal G6 approval | Gate authority | No: G6 cannot be marked passed without this |

## Change discipline

- PRs #37–#44 remain drafts against `engineer-2/development` at time of writing.
- Do not merge to `main`, enable unsupported adapters, change P5 or financial/numerical policy, or turn AI proposals into approval.
- Keep separate `source-supported`, `inferred`, `unresolved`, `reviewed` and `illustrative` statuses.
- If source fixtures or review authority are unavailable, record the gap rather than asserting completion.

## Next independent work

1. Add a reusable simulator-export fixture manifest validator with synthetic negative cases.
2. Audit the existing schematic's status rendering and add evidence-preservation tests.
3. Test M6.4 UI accessibility and read-only behavior, then stage reviewed P2 integration proposal.
4. Request licensed source fixtures and formal approvals only at the point they are needed.
