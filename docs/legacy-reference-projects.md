# Private workbook reference projects

The founder requested that actual legacy workbook data populate the software during container development. Reference mode preserves cached original values, native GBP presentation and source-cell addresses across the existing pages. It does not execute or copy workbook formulas into the calculation engine.

Data is imported as a private project JSON snapshot, not bundled in public frontend assets or committed as financial fixtures. Existing account ownership, project versioning and RLS apply. No new access is granted. Snapshots can be saved, reloaded and downloaded as JSON.

Main dashboard and Scenario show source Summary metrics and NPV Calculation cash-flow records. CAPEX children show equipment and source direct/indirect/working-capital records. OPEX and Revenue show scenario-specific source blocks. Sensitivity shows original sensitivity/ROI records. Entry and design/evidence expose source inventory. Process view shows actual equipment, without inventing connectivity or geometry. All thirteen source sheets remain inspectable.

Scenario 3 contains differing investment figures between source Summary and Capex sheets; the viewer retains both and reports the discrepancy. Cached zero/error/text values remain source records, not validated results. GBP figures are not silently converted to USD.

Edited placeholders retain their original values and can be restored. Dependent charts/headline metrics stay labelled as the original snapshot rather than falsely recalculated from unsupported formulas. Reconciliation with validated engineering/economics remains future work.

Reference mode does not invoke assessment, Monte Carlo, AI research or engineering inference. Assessment and normal financial exports reject reference snapshots so inactive schema scaffolding cannot become financial outputs. Source JSON export remains available. The original workbook stays unchanged.

### Account startup project

In **Accounts & saved projects**, load a private saved revision and choose **Use as startup project**. FlowValue stores only that revision ID in the signed-in user's Supabase `flowvalue_startup_version` preference. New tabs load it through the existing authenticated project endpoint; the preference grants no access and does not bypass project ownership/RLS. Existing valid browser drafts take precedence. A failed startup load leaves the current workspace available and displays the error. **Clear startup project** restores the normal new-tab behavior. Startup selection points to a specific revision; saving a later revision does not silently move the preference.
