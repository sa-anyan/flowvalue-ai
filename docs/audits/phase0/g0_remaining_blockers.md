# G0 remaining failures and blockers

Decision2026-11-10: **G0 FAIL** under the official detailed acceptance requirements. The short G0 exit summary permits documented known failures; it does not remove the separate requirement that supported modules pass their existing tests. The reproduced R-01 assertion therefore remains FAIL. Mandatory milestones also have missing evidence; no percentage/implicit waiver is used.

## Ranked closure queue

| Rank / severity | Finding and acceptance item | Existing evidence | Required closure | Accountable owner |
|---|---|---|---|---|
| 1 / High integration risk | R-01 / T-02: expected complete study is partial | Original test and current targeted/fresh reruns;3 approved years vs Monte Carlo default20, equipment pricing succeeds | Agree intended test/caller horizon, preserve no-invented-contract-years rule, repair adapter/default/fixture contract with complete assertion intact; rerun clean full suite | E2 adapter/orchestration; E1 calculation contract |
| 2 / Medium baseline-control risk | R-17 / M0.4: draft backend CI forces cache off while four existing tests verify caching | First clean run:5 failures, four cache expectations plus R-01; draft workflow `FLOWVALUE_AI_RESPONSE_CACHE: false` | Isolate cache-contract tests from fresh-assessment policy or remove job-wide override; test-owned synthetic caches only; then run hosted CI on reviewed commit | E2; no CI edit made in this assignment |
| 3 / Mandatory milestone BLOCKED | M0.5: reference candidate not formally agreed | Team8 wastewater remains explicitly PROPOSED; no agreement record found | Both engineers agree exact dataset/version/permissions/scope and independent reference pack; record named acceptance | Shared E1/E2 |
| 4 / Mandatory milestone PARTIAL | M0.3 / IW-05: controlled requirements publication and review | Current26 requirement groups updated with official references; original CSV snapshot retained; audit additions still uncommitted | Review and commit intended audit/reference/CI artefacts only; agree feature-level acceptance and ownership without staging127 duplicate files | Shared; E2 Git integration |
| 5 / Evidence PARTIAL | T-04: historical revision reopening/recovery | Two synthetic version tests and mocked cloud conflicts pass | Reopen a permission-cleared historical assessment copy and verify original hash unchanged; nonproduction cloud restore separately | E2 infrastructure/data; E1 checks numeric invariance |
| 6 / Planning/control PARTIAL | IW-02/IW-07/T-06: detailed feature mapping and agreed standard rules | Capability groups and57 official milestones are indexed; proposed unit/missing/precision/provenance/authority rules documented | Engineer review/acceptance of crosswalk and baseline policy; independently justified method tolerances are subsequent P1 work | Shared; E1 numerical policy, E2 contracts |

R-17 is a configuration defect demonstrated locally, **not evidence that GitHub Actions actually ran or failed**. The first fresh result is retained even after the corrected-environment recheck; neither original tests nor application code were modified.

## Evidence gaps clarified rather than promoted to new G0 barriers

- **R-02:** Full independent verification of all production methods is P1/G1, plus source/cost/benchmark/industrial work in P3/P7/P9. The P0 gap/reference policy is documented. Do not demand an industrial certificate to close G0, or claim one from tests.
- **R-03:** All594 catalogue configurations, when historical translation is enabled with packaged data/default2026-09 target, select a CPI purchasing-power proxy in the synthetic metadata probe. Actual project overrides/disabled translation may differ. Independent equipment-index/source verification remains P3; no logic/coefficients changed.
- **Revenue13-field contract:** Official paragraph213 does not enumerate all13 logical fields. All15 actual fields and six expressly named concepts are mapped; exact compatibility remains BLOCKED pending the named contract before schema work. Field count alone is not a demonstrated defect or a reason to delete data.
- **Security:** Known issues have owners and severity; no confirmed Critical exploit was found in scoped checks. Full live tenant, incident, backup objectives and external security assurance are P8. No production credentials/cloud services were used to manufacture evidence.
- **Official roadmap availability:** Closed. The exact user-designated DOCX is now copied byte-for-byte from Downloads to `docs/reference/`, with SHA256 and paragraph extraction recorded. Its presence does not establish project agreement or feature completion.
- **Clean environment:** The earlier offline-wheel blocker is closed by a fresh public-index Python install, fresh npm ci and clean checks. Source/transitive version provenance and clean **green** CI remain separate concerns. Read the run report for both cache-off and baseline-policy outcomes.

## Safe Phase1 preparation

The roadmap explicitly permits overlapping development. E1 may prepare independent source packs, method-specific oracles/tolerances and reviewer assignments on an isolated, agreed scope while G0 remains failed. This is not permission to change equations/schema, implement later-phase features, overwrite baselines or claim G1/industrial readiness. This task stops at documentation and verification; the next ticket is not started.
