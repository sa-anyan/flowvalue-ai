# Coordinated economic execution

CAPEX, Revenue and OPEX are now one user-facing execution group. The three existing stage API routes all submit the same coordinated workflow: CAPEX → Revenue → OPEX → Financial model. This is dependency order rather than unsafe parallel execution. Fresh equipment outputs are reused; missing/stale equipment runs first. Full Run all stages continues to include equipment explicitly.

Engineering Data presents one Economics option instead of three independent economic options. CAPEX/OPEX remain result-exploration dashboards without Run buttons. The shared deterministic stage runners and financial ledger remain canonical.

Approved Revenue assumptions are calculated without another AI proposal so a grouped run does not silently invalidate or replace commercial approval. New or changed Revenue assumptions still need review. Missing data and unsupported cost models remain explicit; coordination cannot legitimately fabricate prices, buyers or contracts. Partial receipts keep the group in needs_review rather than falsely complete.

Validation covers all three API triggers routing to one group, fresh-equipment reuse, complete downstream calculation and existing stage isolation/approval behavior. No new external research or paid AI run was needed for these routing tests.
