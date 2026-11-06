# Revenue Box authority

For application assessments, the Revenue Box defines the permitted payment sources. Process descriptions, equipment names and workbook outlets supply engineering context, not permission to create income. The interpreter receives the Revenue Box separately and must cite it for each interpreted mechanism. Missing prices remain null and generate clarification questions.

The Revenue page lets the user save the Revenue Box, review saved commercial assumptions, and explicitly approve them. Python validates their revenue contracts and source mappings before recording an approval. The financial path checks that approval before using revenue. CAPEX and independent OPEX cells remain available when commercial inputs are pending.

**Save & interpret with AI** now queues a fresh revenue-only AI interpretation on
each explicit save, bypassing the proposal cache. Typing alone does not call the
provider. The current parsed workbook is reused; equipment, CAPEX, OPEX and finance
are not rerun. The saved operating schedule, price basis and unrelated cost inputs
are preserved. Previous inputs are retained in interpretation history. Failure
retains the saved text and prior inputs and reports a retryable interpretation
error. New AI commercial inputs remain drafts requiring explicit approval.
This action incurs normal API usage charges; ordinary Python recalculation and
approval do not request another interpretation or external research.

Revenue-only drafts retain conditional/incomplete opportunities in `pending_inputs`
with exact quotations, stated rates/denominators and missing-input questions.
Pending revenue IDs must match interpreted mechanisms and cannot also appear as
calculated payments. Pending savings use `avoided_cost` and never become income.
These entries block approval until clarified; they are displayed separately on
the Revenue page and are not silently discarded or assigned invented prices.

Approval is stored outside editable calculation assumptions. Its fingerprint includes the Revenue Box, sales/service terms, source stream observations, price basis, operating hours and production ramp. Changes to those inputs require fresh approval. Unrelated equipment-cost or OPEX edits do not approve, replace or invalidate otherwise unchanged revenue assumptions. JSON save/reload preserves the fingerprint.

For a single product sale, changing only an explicit price such as `$15/kg` to
`$20/kg` updates the saved selling price and its exact Revenue Box quotations
together. Product identity, stream, category, currency, unit and the rest of the
statement must stay the same. Multiple products, currency/unit changes and changes
to the payment mechanism still need interpretation/review. Price edits are recorded
and invalidate approval. The Revenue editor also provides a dedicated selling-price
field; structured price edits retain the original source quotation and need fresh
approval before recalculation.

The same check is applied before deterministic FX/escalation, in partial-result fallbacks, current-price views and uncertainty-plan preparation. Changing sampled commercial inputs is not automatically treated as an approved revenue scenario. Saved historical baselines are not rewritten or silently approved; older active assessments with no Revenue Box must supply and approve their commercial basis.

Lower-level standalone calculation functions remain reusable with explicitly supplied contracts. Application lifecycle boundaries bind the server-owned Revenue Box policy; editable assumptions and AI proposals cannot approve themselves.

Acceptance tests: product sales only, service fees only, both together, empty/contradictory context, missing prices and source mappings, changed production/prices/source data, explicit revision-bound approval, partial fallback, historical output masking, uncertainty handoff and saved edit/replay. These tests do not establish market prices, offtake contracts or independent validation of workbook balances.


## Explicit manual MECE routing

The revenue drawer lets users select any of the six MECE types and supply quantities, rates and descriptions directly. Drawer saves use the manual_revenue flag. The server validates category names and records exact user-selection statements in the Revenue Box, rebuilds commercial intent and invalidates approval. Save, approve & calculate performs canonical validation and a Python-only run; it never invokes AI. Unknown quantities and required contract terms still block calculation. Reclassifying a physical product into a commercial payment requires fresh billing quantities/rates rather than silently copying production into a contract.


## Method-specific revenue forms

Add Revenue now chooses a MECE method and payment basis before showing required and optional fields. The shared backend catalogue is backend/revenue/method_forms.py. The preview endpoint validates forms without saving or invoking AI, then builds the existing canonical commercial input. Eight variants cover sold quantities, processing, reserved capacity, annual usage, monthly reserved infrastructure, eligible credits, fixed contractual payments and variable contracts. Capacity requires period and availability; credits require eligibility and ownership; additional fixed fees require a distinct scope. Monthly invoicing alone does not multiply annual usage by twelve. User inputs are explicit assumptions, not verified contracts or extracted workbook quantities.

Typed lines must match the validated form on save. Existing product-stream records retain their physical-product workflow. Legacy commercial lines are unchanged until explicitly edited; conversion refuses annual variations, minimum-payment terms or unsupported availability adjustments so they are not silently erased. Advanced editors retain those established inputs. All new flat schedules explicitly apply the entered terms to each operating year; approval and Python calculation remain separate from preview.
