# Revenue Box authority

For application assessments, the Revenue Box defines the permitted payment sources. Process descriptions, equipment names and workbook outlets supply engineering context, not permission to create income. The interpreter receives the Revenue Box separately and must cite it for each interpreted mechanism. Missing prices remain null and generate clarification questions.

The Revenue page lets the user save the Revenue Box, review saved commercial assumptions, and explicitly approve them. Python validates their revenue contracts and source mappings before recording an approval. The financial path checks that approval before using revenue. CAPEX and independent OPEX cells remain available when commercial inputs are pending.

Approval is stored outside editable calculation assumptions. Its fingerprint includes the Revenue Box, sales/service terms, source stream observations, price basis, operating hours and production ramp. Changes to those inputs require fresh approval. Unrelated equipment-cost or OPEX edits do not approve, replace or invalidate otherwise unchanged revenue assumptions. JSON save/reload preserves the fingerprint.

The same check is applied before deterministic FX/escalation, in partial-result fallbacks, current-price views and uncertainty-plan preparation. Changing sampled commercial inputs is not automatically treated as an approved revenue scenario. Saved historical baselines are not rewritten or silently approved; older active assessments with no Revenue Box must supply and approve their commercial basis.

Lower-level standalone calculation functions remain reusable with explicitly supplied contracts. Application lifecycle boundaries bind the server-owned Revenue Box policy; editable assumptions and AI proposals cannot approve themselves.

Acceptance tests: product sales only, service fees only, both together, empty/contradictory context, missing prices and source mappings, changed production/prices/source data, explicit revision-bound approval, partial fallback, historical output masking, uncertainty handoff and saved edit/replay. These tests do not establish market prices, offtake contracts or independent validation of workbook balances.
