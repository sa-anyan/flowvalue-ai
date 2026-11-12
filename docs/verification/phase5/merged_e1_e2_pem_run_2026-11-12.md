# PEM workbook on merged E1 + E2 code — 12 November 2026

**Owner:** Engineer 1, on the founder's instruction · **Workbook:** the founder's PEM hydrogen QA workbook (SHA-256 prefix `2e8b33f2ea54c693`) · **Integration:** a local, temporary branch `tmp/e1-e2-integration-2026-11-12` in a scratch worktree. Not pushed, and no PR was merged.

## What was merged

- **Engineer 1:** `e1/p5-audit` at `ec1e244`. It contains the full stacked line: #8, #14, #16, #18–20, #25, #29 and #35.
- **Engineer 2:** `engineer-2/development` plus all 26 open PR branches:
  - B07: #21;
  - P2 tests and evidence: #22–24, #26–28, #30–34;
  - P6 contracts, specifications, preview and integration candidate: #37–49.
- **Excluded:** #36 (marked "do not merge") and the governance-document PRs #11 and #12.

| Integration check | Result |
|---|---|
| Merge | All 27 merges clean: no text conflicts |
| Backend suite | **4,457 passed**, 3 skipped, 0 failed. Engineer 2's work adds 100 tests, and all pass with Engineer 1's |
| Frontend type check | Passes, on both the merged code and E1 alone |
| PEM run | Engineering data, equipment, CAPEX and OPEX ready; revenue and finance correctly ask for a Revenue Box |

**Note on branch hygiene (M0.6):** none of Engineer 2's 26 PR branches is an ancestor of his "integration candidate" (#49), which was built separately. The integration cadence (roadmap 9.6) is still undecided.

## Errors found, by phase

| # | Error | Phase (milestone) | Owner | Status |
|---|---|---|---|---|
| M1 | **An RO unit was priced at US$0.90.** OpenPyTEA's Seider RO models compute cost = 3.1 × flow (MGD) for brackish water and 3.988 × flow for seawater. That gives a few dollars per MGD, so the printed coefficient is almost certainly in $ million. The unit was also floored at 0.2 MGD (35× its size). The upstream parity check could not catch a unit-scale error; only a check against the printed source can | **P3** (M3.2 catalogue; G3 A1 source checks) | E1 | **Fixed (held):** both models are disabled with a stated reason until checked against Seider Table 16.32. The upstream CSV is unchanged. Replay: RO is now visibly unpriced and listed in CAPEX open items |
| M2 | **False "No supported material stream table" warning.** The AI placed the RO unit on the Cover Page, so that sheet's own validation found equipment but no streams, although the balance sheet has 7. This was latent on E1 too, and appears only when AI-identified equipment sits on a stream-free sheet | **P2** (validation scoping) | E1 (fixed) | **Fixed:** suppressed when the workbook has streams elsewhere. Test added |
| M3 | **RO is unpriced after the hold.** The remaining candidate, a Nottingham packaged RO model, lacks a usable sizing input, so a price needs a supplier quote or a checked Seider coefficient | **P3** | Founder (Seider table or quote), E1 | Open; visible, not zero |
| M4 | **Equipment identification varies between runs.** In this run the AI review registered the RO unit; on E1 alone it did not, and the completeness flag caught it. HE-101 again matched a different valid exchanger type (shell-and-tube rather than plate-and-frame) | **P5** (M5.7 repeatability) with **P2** (M2.6 identification) | E1 (P5), E2 (P2) | Open. The completeness guard covers the "missed unit" case; type choice needs per-item user confirmation |
| M5 | **The founder's "RO out of scope" decision did not carry over.** It was recorded on an earlier study; a new upload of the same workbook starts without it, so RO was included and priced | **P2** (M2.5 versioning / re-import of decisions) | E2, with E1 | Open: decide whether register decisions follow a re-uploaded workbook |
| M6 | **The AI still under-staffs continuous operation** (4 operator FTE for 24/7) | **P4/P5** | E1 | Open (same as earlier finding 7) |

**Correct behaviour, not errors:**

- **RO type conflict.** The AI review recorded conflicting type observations for RO and chose none automatically ("conflicting values"): a correct flag.
- **Contractor fee and contingency.** The RO model's installed-cost scope means these purchased-equipment factors are not applied to it. They are reported as scope gaps (M3.4): correct, and it disappears once RO is priced on a purchased basis.
- **OPEX "partial".** Four Garrett allowances are percentages of revenue, and no Revenue Box was given.
- **Fixes held on the merged code:** the electrolyser cited 55.5 kWh/kg from Mass Balance 1!C9, all 7 streams parsed, and stream 4 read 100 kg/h.

## Verification after the fixes

Engineer 1's two fixes were merged into the integration worktree and the merged study was replayed on a copy; the AI's earlier answers were reused where the context was unchanged.

- **Engineering data:** the false warning is gone.
- **Equipment:** EL-101 and HE-101 priced; RO unpriced, "source required".
- **CAPEX:** lists RO as unpriced.
- **E1 branch suite:** 4,357 passed.
