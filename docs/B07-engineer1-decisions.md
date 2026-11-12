# B07 · Engineer 1 decisions on engineering identities

**Date:** 11 November 2026 · **Decided by:** Engineer 1 · **Responds to:** `docs/B07-engineering-identities.md` on `engineer-2/development` (commit `719a26c`), section "Engineer 1 approval pending"

All four items are approved, with the rules below. They feed roadmap Phase 2 milestones M2.2 (equipment identity and alias resolution) and M2.4 (recalculation).

## 1. Costing reconciliation stays as it is — APPROVED

The identity register is a **read-only projection**. It explains how source rows became calculation records; it does not change what is priced.

- Existing explicit aliases, splits, exclusions, restorations and quantities keep controlling calculation inputs.
- A change to the register alone must leave every equipment line, quantity and total byte-identical.

**Acceptance:** run equipment costing with and without the register attached; line amounts, quantities and totals are identical.

## 2. Authority for identity to affect calculation — APPROVED with these rules

An identity record grants **no** calculation authority by itself. Only a **user-confirmed** decision changes what is priced: `alias_confirmation` or `scope_confirmation` with status `user_confirmed`, `user_confirmed_for_simulation` or `user_confirmed_distinct` and a non-empty rationale (the existing `equipment_resolution.scope.confirmed` rule). AI-proposed identities stay advisory and are shown as `ambiguous` or `unresolved`.

The four review cases:

| Case | Rule |
|---|---|
| **Same printed tag, different service** (for example `T-104` on two sheets with different chemicals) | Two distinct records, status `ambiguous`, both priced, until the user confirms them as an alias or as distinct. Never merged automatically. |
| **Alias chain** (A → B → C) | Resolve to the single root asset C; A and B carry `physical_asset_id = C` and are excluded from pricing once confirmed. A cycle (A → B → A) is rejected with an error naming the tags. |
| **AB pair** (`P-101AB`) | One record, **quantity 2** under the founder convention (duty plus installed spare). Each unit is sized for the **full duty**, because a spare must carry the whole load. Flow sharing between A and B applies only if the user records it. The register shows the pair as one record with `quantity: 2`, not two physical asset IDs, unless the user splits them. |
| **Multi-unit group with no per-asset mapping** | One record with the stated quantity and `physical_asset_id: null`, status `unresolved`. It is priced once at that quantity, never expanded into guessed individual assets. |

**Acceptance:** one fixture per case above; each checks priced quantity, inclusion and register status, before and after a user confirmation.

## 3. Key scenario equipment costs by record, not tag — APPROVED, and needed

This fixes a real defect. `backend/scenarios_and_uncertainty/monte_carlo/engine.py` builds `equipment_costs`, `equipment_cost_scopes`, `equipment_installation_costs` and `equipment_models` as dictionaries keyed by `equipment_tag` (lines 61–68 and 133–145). Two distinct priced records with the same printed tag overwrite each other, so the scenario **undercounts** equipment cost while the stage total counts both.

**Decision:**

- Replace these with an **ordered list keyed by the effective costing record key**, each entry carrying display tag, physical asset ID (where resolved), quantity, scope and price coverage.
- Every priced record is preserved; the inclusion policy is unchanged.
- **Compatibility:** exports and the UI keep a display-tag column so existing views still read naturally. Saved scenario results in the old tag-keyed shape are read as-is and labelled legacy; they are not rewritten.

**Acceptance:** two priced records sharing tag `T-104` (10,000 and 5,000) give a scenario equipment total of 15,000, equal to the stage total. Before the change the same fixture gives 5,000, which is the regression this test locks in.

## 4. Stage-to-scenario parity before replacing the projection — APPROVED

The projection change in item 3 lands only with parity tests. For a deterministic scenario (every sampled parameter at its central value), the scenario must reproduce the saved stage results **exactly, in decimal arithmetic**, for:

- each equipment line amount and included quantity
- capital scope subtotals and total CAPEX
- OPEX, revenue and the financial totals (NPV, IRR status, payback)

Required fixtures:

- restored same-tag records (item 2, first case)
- confirmed alias exclusions (item 2, second case)
- a priced record and an unpriced split of the same tag
- an AB pair (quantity 2)

Any intentional difference between stage and scenario must be named in the test with its reason.

## Phase 2 position

| Milestone | Status after these approvals |
|---|---|
| M2.1 Canonical project and stream schema | Partial: B07 observation identity and B08 monetary and timeline contracts; integration pending |
| M2.2 Equipment identity and alias resolution | Ready to complete: B07 plus these rules and item 3's fix |
| M2.3 Source provenance and assumption register | Partial: observation IDs exist; the single provenance list (Extracted, Calculated, Assumed, User-overridden) is still open |
| M2.4 Dependency graph and recalculation | Partial: stage freshness and stale marking exist; no explicit dependency graph yet |
| M2.5 Migration and version compatibility | Partial: B07 legacy read path; T-04 reopen evidence (G0 record) |
