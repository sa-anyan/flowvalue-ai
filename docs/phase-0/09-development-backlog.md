# Phase 0 · Prioritised development backlog

The work below starts only after the audit is accepted. Existing failures need a reproduced reference case and an owner before any implementation. Shared decisions are flagged separately from tasks that can proceed with fixtures or existing interfaces.

| ID · group | Priority · owner · coordination | Work and dependencies | Acceptance evidence | Suggested issue title |
|---|---|---|---|---|
| B01 · Critical defect / test baseline | Critical · E2 with E1 · independent setup | Define an audited Python test environment with declared test-only dependencies, including pandas for OpenPyTEA reference tests. Diagnose fixture/engine failures individually. R01. | Fresh isolated run collects all tests. Fixture-only skips explain availability. Every remaining failure has exact command, case and owner. | Declare and reproduce the Python test environment |
| B02 · P1 prerequisite | Critical · E1 · independent | Catalogue enabled sizing/cost/economic methods and applicability. Separate provisional digits, executable correlations and unavailable models. R02. | Registry listing reconciles to reviewed inventory with one row per executable method and source/rights fields populated. | Inventory enabled methods and establish independent oracles |
| B03 · P1 prerequisite | Critical · E1 · independent after B02 | Produce sizing and conversion oracles, with pressure basis, duty, density and normalized unit cases. R03. | Each selected method passes hand-verified nominal, boundary and invalid-input cases within recorded tolerances. | Benchmark sizing methods and dimensional boundaries |
| B04 · Critical numerical risk | Critical · E1 · independent fixture; B08 for contract changes | Triage the 14 non-scenario equipment, conversion, translation and CAPEX failures, starting with HX-1. Identify unsupported chart inputs versus valid physical conversions. Exercise explicit quantity, supported factors and multiple cost scopes. R04. | Diagnose failure against source applicability. Regression asserts quantity extension, purchase-only basis and unresolved/out-of-domain behavior. | Resolve HX-1 handoff discrepancy using the source basis |
| B05 · P1 prerequisite | High · E1 · independent oracle work; B08 for integration | Build independent CAPEX/OPEX/revenue/savings/finance calculations on a redistributable small fixture. R04–R07. | Signed arithmetic ledger, dated basis, line coverage, cash and noncash, six revenue methods, NPV/IRR/payback edge cases. | Establish the reference economics and cashflow ledger |
| B06 · Critical integration risk | Critical · shared; E1 numerical lead · shared decision | Reproduce the manual-price scenario that returned partial, then compare stage and scenario central cases, including approvals and calendar differences. B05, B08, B09. R08. | Same central inputs reconcile annually to cent precision and use matching metric labels and coverage. Any intentionally distinct field is documented and tested. | Reconcile the Monte Carlo central case with the saved stage ledger |
| B07 · P2 prerequisite | Critical · E2 · shared contract | Specify stable source, entity, physical asset and alias identities. B02 for required engineering fields. R09. | Agreed JSON examples round-trip evidence and distinguish identical printed tags from confirmed aliases. | Define stable source, stream and physical equipment identities |
| B08 · Shared architecture decision | Critical · E2 with E1 · shared | Agree monetary basis, operating timeline, typed missing/zero/excluded, scoped costing and adapter compatibility. B07. R10/R11. | Contract fixtures for mixed basis, positive/zero closure, CAPEX factors, fixed revenue and ramp. Both engineers approve one set of examples. | Agree the price basis and project timeline contracts |
| B09 · P2 prerequisite | High · E2 · shared contract | Inventory all approval/invalidation/write paths and propose schema/engine receipt versioning with legacy-read tests. B07/B08. R12. | Edit/freshness matrix, conflict-retry test, backward-read fixtures and stamped outputs. | Specify revision and calculation provenance contracts |
| B10 · Testing infrastructure | Critical · E2 · independent CI implementation | Add Python matrix, all Node tests, typecheck/build and a registry-backed clean setup check. B01. R01. | Actions executes .mjs and .cjs plus Python, reports summaries and blocks merge on regressions under agreed protection. | Gate main on complete local and CI test coverage |
| B11 · Critical approval risk | Critical · E2 · shared policy with E1 | Trace and separate provisional AI calculations from approved baselines. Include CAPEX/OPEX and derived scenario Revenue authority. B09. R13/R14. | All save/run paths tested with approved, unapproved, stale and injected input. Zero auto-promotions in agreed cases. | Enforce review boundaries for AI-origin assumptions |
| B12 · Documentation | High · E2 · independent | Align onboarding/Entry input matrix, stage run labels and test setup with current code. Include historical adapters and generated frontend files. B01/B07. R01/R19. | Every declared format and route has linked evidence and supported/unsupported scope. Document reproducible commands. | Align the support matrix and developer setup with the active routes |
| B13 · Later P4 | High · E1 · shared contract | Validate annual cash, per-output fixed/variable production costs and commercial authorities in saved UI. B05/B08/B11. R05–R07. | Same denominator and monetary basis across values, pending scope displayed and one reconciliation fixture per edit class. | Reconcile operating cost per output and six-category income |
| B14 · Later P5 | High · E2 · independent evaluation after B11 | Construct source grounding and refusal corpus with simulated provider failures, injected cells and consent toggles. R14. | Quantitative metrics, exact evidence IDs, model/prompt versions and zero prohibited calls. | Benchmark specialist proposals and research permissions |
| B15 · Later P6 | Medium · E2 · shared contract | Prove first simulator adapter in isolated fixtures before advertising it. B07/B08/B12. R15/R19. | Fixtures cover supported, incomplete and rejected inputs with lineage. Source format version documented. | Validate the first supported native simulator adapter |
| B16 · Later P7 | High · shared · shared | Browser journey and export reconciliation using B05 fixture. B06/B09/B10. R16. | Upload, approve, run, save/reopen, invalidate and export. All amounts and revision IDs agree. | Add a browser acceptance ledger and export reconciliation |
| B17 · Later P8 | Critical for production · E2 · independent staging with approval | Owner/RLS two-user negative tests, restore drill, resource/rate limits, dependency scanning and job restart behavior. B10/B12. R17. | Staging evidence, measured restore objective, package advisories triaged, no production changes required for acceptance. | Verify tenant isolation and operational recovery in staging |
| B18 · Later P9 | High · shared · shared | Agree three external representative industrial benchmarks and reviewer independence. B16/B17. R18. | Signed reports, provenance, deviations and closure record on all agreed methods and studies. | Validate FlowValue against independent industrial studies |

### Engineer 1 · First five

1. **B02** · Inventory methods and establish reference sources.
2. **B04** · Reproduce and explain the HX-1 pricing handoff discrepancy.
3. **B03** · Benchmark sizing and dimensional boundaries.
4. **B05** · Build the independent economics and finance ledger.
5. **B06** · Reconcile the deterministic scenario central case with the saved stages alongside Engineer 2.

### Engineer 2 · First five

1. **B01** · Make the Python baseline collectible with declared dependencies.
2. **B10** · Establish CI coverage once the test environment is reproducible.
3. **B07** · Agree stable source and physical asset identities with Engineer 1.
4. **B08** · Agree monetary and timeline contracts with Engineer 1.
5. **B09** · Specify receipt versioning and invalidation tests.

[Requirements](08-requirements-register.md) · [Completion decision](10-phase-0-completion-report.md)
