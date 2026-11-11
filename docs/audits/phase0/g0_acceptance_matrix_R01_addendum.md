# G0 acceptance addendum after FV-G0-R01

Date2026-11-10. This addendum updates only the R-01-dependent evidence in the historical `g0_acceptance_matrix.md`/reconciliation report. Original reports and original test failures remain unchanged; a before-copy of the acceptance matrix is retained with this ticket's evidence.

| Item | Earlier evidence | Current evidence | Current disposition |
|---|---|---|---|
| T-02 supported backend tests / R-01 | Original complete-vs-partial failure |1738 passed, 3 skipped, 1 warning, 367 subtests passed in 157.79s (0:02:37); original assertion unchanged and passes | PASS for executed canonical backend scope;3 unavailable/optional fixtures skipped, not passed |
| Corrective R-01 ticket | High open annual-horizon mismatch | Ticket-specific contract, independent synthetic financial reference and full regressions pass | CLOSED within tested scope |
| M0.4 / R-17 | Draft CI cache-off setting conflicts with four tests; no hosted proof | No CI setting changed here; baseline-cache full local tests pass | FAIL/PARTIAL CI closure still required; no hosted success claimed |
| M0.5 | Proposed wastewater reference only | No formal agreement added | BLOCKED |
| M0.3 / T-06 | Controlled publication and owner/criterion agreement pending | Scoped patch and evidence prepared, not committed/deployed | PARTIAL |
| Historical/cloud revision recovery | Synthetic checks only | New saved-study/temporary-store tests pass; no production/cloud exercise | PARTIAL/BLOCKED remaining evidence |

**Overall G0 remains FAIL under the last detailed gate interpretation**, because the draft CI configuration still has a demonstrated unresolved conflict and other mandatory milestones/evidence are incomplete. R-01 no longer supplies the reason for that failed decision. No automatic G0 PASS, industrial validation or subsequent phase completion is claimed.
