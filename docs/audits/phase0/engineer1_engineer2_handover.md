# Engineer1 and Engineer2 gate handover

Reconciliation record2026-11-10. Ownership follows the user's assignment. Named human acceptance/signatures have not been inferred from source code or prior demonstration runs. `evidence/g0_reconciliation/roadmap_milestone_ownership.csv` indexes all57 official milestone titles, owners and original acceptance-gate references; it is a proposed work allocation, not an implementation claim.

## Engineer1 ownership record

| Responsibility | Evidence/control | Immediate deliverable | Phase |
|---|---|---|---|
| Engineering equations and reference verification | Engineering/costing registers distinguish code, tests, source, independent numerical and industrial evidence | Define a source/equation/version/reference-case/tolerance approval template and prioritise critical methods; do not implement P1 here | P1/P3/P7 |
| Units and dimensions | Explicit assumptions, parser/bridge/native-coordinate contracts | Approve pressure, mass/volume, thermal, gas-condition and time-basis test oracles | P1 |
| Costing and escalation |594 synthetic default translation probes; all use CPI proxies when enabled with packaged data | Verify original cost basis and appropriate dated indices before a verified-current-equipment-price claim | P3 |
| CAPEX/OPEX/Revenue | Different factor bases, approved Revenue Box, annual schedules | Approve R-01 schedule/commercial boundary and independent dependent-factor expectations | P4/P7 |
| Finance | One ledger and timing conventions | Approve independent cash-flow/NPV/IRR/payback references and precision/tolerances | P4/P7 |
| Reference project | Team8 wastewater study remains proposed | Agree engineering scope, independent truth set, data permissions and acceptance criteria jointly | M0.5 |

## Engineer2 ownership record

| Responsibility | Evidence/control | Required handover/closure | Phase |
|---|---|---|---|
| Project schema/interfaces | CommercialLine15 fields vs unspecified logical13; multiple adapters | Obtain canonical named13-field definition; map nested/source/approval data and old snapshots without field deletion | P2/P4 |
| Dependencies/orchestration/AI | R-01 3-year fixture vs default20-year scenario | Trace caller/settings/prepare and agree the intended contract with E1; no unsupported contract extension | P2/P4/P7 |
| CI and development reliability | Fresh-environment evidence and existing local workflow definitions; R-17 cache-off conflict | Resolve FV-G0-M04 global cache-off conflict in a separate ticket; commit/review intended files deliberately, run hosted CI, retain R-01 assertion; dependency provenance/lock review | M0.3/M0.4/P8 |
| Authentication and isolation | Mocked tests executed; no live production credentials | Use a designated nonproduction tenant for adversarial owner/isolation tests; assess residual security risk, no claim of release-level assurance from mocks | P8 |
| Project recovery | Synthetic named-version forks and stale writes pass | Reopen permission-cleared historical revision copies and test cloud backup/restore in nonproduction | P0/P2/P8 |
| Deployment/infrastructure | No deployment performed | Establish safe release/recovery evidence and ownership; not part of this audit's execution | P8 |
| Reference project | No formal agreement located | Confirm dataset permissions, storage/access, immutable baseline and recoverable test setup jointly | M0.5 |

## Shared R-01 acceptance boundary

E1 approves meaning of operating/calendar years, authorised term coverage, billing quantities and financial expectations. E2 owns horizon propagation, settings/defaults, caller/adapter handling and immutable-copy behaviour. A shorter contract is not automatically an error in the Revenue engine. A caller must not silently change a3-year success study into20 years; an explicit20-year request must disclose missing17 years. See `tickets_R01_commercial_year_handoff.md` for the separate corrective ticket and exact acceptance tests.

## Reference and policy controls for agreement

These are **proposed review rules**, not approved engineering tolerances or software changes: deterministic Python owns arithmetic; units/condition/time/currency bases are explicit; missing is distinct from zero; facts, assumptions and inferred values retain source/version; unsupported/extrapolated outputs are visibly qualified; baseline edits require authority/version control; every exception has an owner, rationale and disposition. Use method-specific independently justified tolerances in P1; do not impose a universal percentage or infer validity from Decimal precision40.

The independent-reference policy is already explicit in repository instructions/audit: a study workbook cannot validate itself; the same production function cannot generate its own independent expected result. Pinned upstream parity is software agreement, not industrial validation. Independent source rechecking and plant/pilot validation are distinct later gates.

## Controlled progression

Roadmap phase windows explicitly overlap. E1 can prepare independent source/reference/tolerance work in an isolated branch under agreed scope, preserving baseline and known failures. This is not G0 acceptance, G1 completion, release approval or permission for new schema/engine implementation. No next task was started here.
