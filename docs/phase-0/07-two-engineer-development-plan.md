# Phase 0 · Two-engineer development plan

| Ownership | Primary directories and outputs |
|---|---|
| Engineer 1 · P1, P3, P4; numerical benchmarking in P7 | Engineering sizing, equipment cost indexes and economics engines under [backend](../../backend). Own reference equations, applicability domains, scopes, deterministic result tests and independent oracles. |
| Engineer 2 · P2, P5, P6, P8 | [Ingestion](../../backend/ingestion), [cloud](../../backend/cloud), [API](../../backend/api), orchestration contracts, provider and CI. Own evidence IDs, typed boundaries, approval infrastructure, simulator adapters and operational controls. |
| Shared · P0, P7, P9 | Agree acceptance fixtures and release gates. Engineer 1 signs numerical/model acceptance. Engineer 2 signs data, authority and runtime integration acceptance. Founder or designated reviewer decides exceptions and external industrial claims. |

Require review from the other engineer when a PR changes a shared contract or consumes it in a new way. The primary owner can lead implementation and code review on their own modules, but cannot approve their own contract-breaking change.

| Collision surface | Working agreement |
|---|---|
| [Stage runners and shared helpers](../../backend/blocks) and [connected adapter](../../backend/orchestration/pipeline.py) | Engineer 2 owns stage envelope, invalidation and source contracts. Engineer 1 owns calculator-facing adapters. Review changes to order, fallback basis, completeness and scenario parity together. |
| [Ingestion entities](../../backend/ingestion/balance/models.py) and [equipment resolution](../../backend/equipment_resolution) | Engineer 2 owns IDs and parser versioning. Engineer 1 owns how distinct physical scope and quantities enter sizing/costing. A new alias rule must be reviewed against fixture totals. |
| [Revenue authority](../../backend/revenue/authority.py), [rate workspace](../../backend/revenue/rate_workspace.py) and [Cashflow schedule](../../backend/blocks/cashflow/schedule.py) | Agree field and timeline semantics before editing. Engineer 1 owns revenue, expense and ledger semantics. Engineer 2 owns approval/version propagation and API versioning. |
| [API](../../backend/api/app.py), [shared frontend workspace](../../frontend/src/blocks/shared/project-workspace.tsx) and [scenario](../../backend/scenarios_and_uncertainty/monte_carlo) | Avoid concurrent edits to the same handler or top-level workspace. Define a thin route/draft contract first. Split downstream implementation by module and run a shared fixture at merge. |

### Proposed GitHub controls

1. Engineer 2 publishes verified increments to the long-lived `engineer-2/development` branch following the [repository instructions](../../AGENTS.md#engineer-2-github-checkpoint). Engineers use separate checkouts or worktrees and avoid sharing generated files, local settings or assessment databases.
2. Keep a contract note with example input/output, units, error semantics, revision compatibility, owner and test IDs before implementing both sides. Agree changes on a small contract PR first. Maintain backward-compatible reads for supported stored versions and record deprecation boundaries.
3. Each PR links its requirement and issue, names touched contracts, includes commands/results, documents numerical or authority changes, and attaches a synthetic or approved redistributable fixture. Keep failures visible. Any temporary waiver needs a named owner, specific failing check and expiry.
4. Protect main with a PR, another engineer's review for shared surfaces, resolved conversations and required checks. Require Python, all Node tests, typecheck, production build and a seeded smoke journey once B10 delivers these jobs. Use squash merge with correct authorship. Branch protection and hosted workflow status are proposed, not inspected.
5. Integrate at the versioned contract checkpoint, a shared end-to-end synthetic ledger, parity with scenarios and exports, and the external industrial validation release gate. Retain baseline and migration evidence. Update each other before changing a schema, expected numerical oracle, schedule mapping or fixture.

First five sequenced assignments for both engineers are in the [backlog](09-development-backlog.md). Inputs that need agreement are listed in the [data audit](04-data-and-dependency-audit.md).
