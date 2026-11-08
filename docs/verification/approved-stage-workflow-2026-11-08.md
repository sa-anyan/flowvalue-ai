# Approved stages and restored dashboards

Founder correction: Equipment retains its original cards and drawers; the editable register belongs to Engineering Data. CAPEX and OPEX lead with their original CapexStudio and EconomicsExplorer dashboards/graphs. Their assumption workbenches are available inside Assumptions & methods, not in place of the dashboards.

Engineering Data now has an explicit approval action, tied to the canonical extraction payload. Editing the register or changing source/context invalidates approval. Save all table edits before approving. Approval does not verify engineering accuracy or approve Revenue assumptions.

Each downstream page offers Run stage and Run all stages. Batch execution reuses backend.blocks.execution.run_stage in dependency order: equipment, capex, revenue, opex, financial. It does not re-extract the workbook, fabricate missing inputs, bypass Revenue approval, or use a second calculator. Partial/blocked stages retain their receipts; other stages are still attempted. The default uses saved inputs and Python; AI proposals require explicitly selecting the checkbox.

Tests: 14 backend workflow/stage-isolation tests passed, including source-bound approval, stale-revision rejection, complete deterministic batch, partial batch without Revenue approval, no extraction rerun and polling between stages. Frontend production compilation and TypeScript passed. Existing Revenue implementation and calculation engines were not replaced.

Browser verification: a separate synthetic assessment was approved through the Engineering Data UI, then Run all stages completed all five downstream stages with AI disabled. CAPEX rendered its original dashboard with SVG charts and the assumption editor collapsed. No source workbook or user baseline was modified.
