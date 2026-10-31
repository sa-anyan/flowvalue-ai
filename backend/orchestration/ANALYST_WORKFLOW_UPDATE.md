# Analyst-workflow additions — 31 October 2026

This update extends the controlled-rebuild workflow for founder proposals 1–8. It does not introduce later scenario/Monte Carlo, presentation or financial-methodology features. Numerical correlations and the sole annual financial engine remain the calculation owners. The legacy economic workbook was not used as a source of formulas, data or expected outcomes.

## Calculation view of the workbook

`workbook_scope.py` consumes the process specialist's explicit worksheet classifications. Active process records form the calculation view. Named supporting records may supply missing properties only to a unique existing identity/case. Conflicting supporting observations remain outside the calculation with a review note. Reference records remain in the original extraction, not in the calculation view. Exact repeated source identities are coalesced and stream/equipment references remapped; equal names in different cases are not merged. Scope selection never verifies a physical balance.

Whole delivered feeds and their component or alternate-unit observations cannot both be charged. This complements canonical duplicate equipment-tag checks and source-observation checks. It does not prove that every semantically similar cost in arbitrary source documents has been detected.

## Independent specialist reviews

`analyst_team.py` runs three engineering specialists (process/equipment, materials/hygiene, health/safety), followed by three operating specialists (operations, project manager, commercial cost challenger). Each is a separate bounded, cached LLM request. The existing equipment/CAPEX and operating-model proposals consume their findings and perform consolidation; a second numerical engine is not introduced.

Reviews document relevant assets, recommendations, reasoning, alternatives, challenges, source IDs, uncertainty and proposed cost owners. Unsupported source/equipment references remain explicitly unresolved and never enter the accepted source-ID list. Matching cost-owner names surface ownership overlaps. No agent consensus certifies a material, hygiene specification or design.

User agree/challenge/defer decisions and comments are saved separately from numerical inputs and feed subsequent AI review. Applying a model/material alternative still uses the existing editable equipment configuration and recalculation controls. Approved baselines and named versions are not overwritten.

## Purchased versus installed costs

Conflicting installation/module alternatives previously made an otherwise valid purchased component unavailable. `equipment_costing/component_scope.py` provides an explicit orchestration-only path: retain supported material/pressure choices and calculate the purchased component through the existing registry; defer both conflicting scope alternatives. Installation and combined costs remain null, with the requested factors and warning retained. The original strict registry/total behaviour remains the default outside this explicit adapter. Bounded LLM correction still receives these conflicts.

Selected detailed CAPEX rejects `nottingham_lang`. A separate screening comparison is returned outside the selected CAPEX calculation. It requires an appropriate delivered-cost basis; a missing basis is disclosed. Working capital is excluded from this fixed-capital screening cross-check. A screening value is never added to detailed costs.

## Explicit research and commercial assumptions

`deep_research.py` and the research API perform scoped equipment or product research only after an explicit consent-bearing user action. Equipment research compares the local catalogue, published correlations/papers and comparable prices; market research distinguishes grade, location, commercial quantity/delivery basis and source dates. Hosted web search is bounded, and candidate URLs must be present in actual web-search source metadata. Listings and extracted candidates are review drafts, not verified quotations. Unknown prices/capacities/exponents remain null. Discovered formula descriptions are never executed as code.

Research does not change the plan. Source inspection and the comparable/observed-price forms are separate. `equipment_costing/quotes.py` converts units and applies the justified comparable cost-size relation. A contemporary price retains its own date; no automatic escalation is applied. Explicit period/index/currency alignment is required before combining unlike bases. Purchased cost and unresolved installation stay distinct.

`commercial_pricing.py` retains observed price, observation type, date, URL and an explicit commercial-discount rationale. There is no automatic 20–50% discount. Python calculates the adjustment; commodity/listing prices are not relabelled as supplier quotations. Currency, price period and quantity unit must match the study. The same assumption feeds source-based consumption costs or sales and then the existing financial ledger.

## Test scope and limits

The private before/after study, source archive and source hashes are under `outputs/analyst-workflow-upgrade/` (ignored by Git). The original M&E 8 assessment remains unchanged. The corrected after case uses the same uploaded bytes and description. A separate original-input calculation check confirms all four original model results are unchanged. Another diagnostic holds the original financial policy fixed when applying the new engineering/OPEX proposals.

Live specialist/proposal generation was exercised on M&E 8. Research source validation, explicit consent, draft isolation, comparable scaling, price adjustment, reference exclusion, ownership and financial handoffs have automated tests. Live external equipment/market searches were not invoked during the automatic rerun: they remain an explicit user action. These checks establish plumbing and calculation behaviour, not completeness, material suitability, supplier acceptance or industrial estimate accuracy.

Official API contract consulted: https://developers.openai.com/api/docs/guides/tools-web-search

### Zero separate headcount and factor ownership

The live review exposed zero-FTE rows explicitly intended to leave supervision, maintenance and laboratory costs with Garrett. Such a row is now retained as a workforce decision but does not replace its documented percentage category with a zero salary. Nonzero itemized staffing still replaces its overlapping factor. This preserves the specialist's stated ownership and avoids silently deleting maintenance/materials/testing scope.
