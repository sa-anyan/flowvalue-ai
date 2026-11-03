# Monte Carlo engineering and TEA

## Architecture

The optional `backend/scenarios_and_uncertainty/monte_carlo` package freezes a separate assessment snapshot and samples editable assumptions. Each draw uses the canonical orchestration pipeline, equipment catalogue, sizing, CAPEX, OPEX and financial ledger. The original assessment is not modified. The study defaults to 20 operating years; it does not invent contract extensions.

Modules: `models` defines contracts; `discovery` identifies saved inputs and unresolved scope; `sampling` implements seeded bounded distributions and Gaussian-copula correlations; `scenarios` applies reviewed assumptions and aliases; `engine` evaluates and aggregates draws; `service` persists jobs, progress and cancellation; `advisor` prepares optional disabled AI range proposals; `exports` produces frozen CSV/Excel results. The pipeline's range-calculation option defaults to its previous behaviour.

API routes are below `/api/assessments/{assessment}/monte-carlo`: discover, preflight, run, jobs, job details, representative runs, audit, exports, cancellation and optional preparation. Existing assessment access controls apply. Preparation requires an explicit user action, may incur provider charges, and makes no external research calls. No LLM runs inside simulation iterations.

Frontend routes: `/monte-carlo/setup` and `/monte-carlo/overview`. Setup exposes ranges, distribution constraints, source rationale, aliases, correlations, seed, count and coverage. Results expose distributions, financial denominators, equipment costs, conditional driver rankings, cash-flow bands, study comparison, representative draws and exports.

## Numerical and reporting conventions

Supported distributions are triangular, uniform, bounded normal, bounded lognormal and discrete. Lognormal location is its median and spread is log-space sigma. Correlations describe latent Gaussian variables, not guaranteed physical Pearson correlations. Correlation matrices must be positive semidefinite. Target paths, units, finite numbers and original physical limits are validated. Confirmed aliases cannot be charged twice.

P10/P50/P90 are ascending numerical quantiles, not exceedance probabilities. A complete draw requires all registered non-aliased equipment to be priced and the canonical financial ledger to calculate a finite NPV. Partial scope, invalid calculations and failed runs remain separate. Financial probabilities use complete draws only; missing IRR and unreached payback retain their own denominators. Known component costs can be shown despite unresolved plant scope.

The tornado uses conditional sampled-driver comparisons and rank associations. It is not a causal or Sobol attribution. Cash-flow bands are pointwise quantiles. Exports contain frozen simulation outputs and an assumption/audit register; spreadsheet edits do not rerun the simulator.

## Verification

Local acceptance: 435 backend tests and 367 subtests passed. Includes all 13 Charlie exceptions, seeded reproducibility, distributions, correlations, units, limits, aliases, frozen baselines, partial/invalid denominators, exports, API ownership and source fingerprints.

A real 1,000-draw Charlie study produced 19/32 priced records (59.375%), 1,000 partial draws, no complete draws and no financial risk probability. All 13 unresolved records remain visible. This is successful uncertainty execution, not resolution of all equipment models.

A separate explicitly synthetic complete 20-year study produced 1,000 complete draws. Five selected draws were independently replayed through the canonical pipeline; metrics and every cash-flow row matched exactly. Charlie's saved baseline remained unchanged. Local evidence is saved under `outputs/monte-carlo`.

## Limits

Unsupported models remain unsupported. AI proposals were tested with mocks, not paid live calls; their physical plausibility needs engineering review. Saved ranges, graph digitisation and model bias are not statistically calibrated. Completeness refers to registered equipment, not a certified exhaustive plant design.

Sampling is vectorised, but canonical engineering calculations run per distinct draw. Charlie's 1,000 draws took about four minutes locally. The selectable 5,000/10,000 counts have not been full-load benchmarked. Jobs use the existing local worker and persisted snapshots; distributed execution and automatic restart/resume are not implemented. Cancellation is checked in batches. Source changes during a study invalidate complete financial-risk reporting.

No stochastic annual commodity time-series model, automatic mechanical redesign, external pricing research or new currency-selector integration is included. Existing cost-translation disclosures remain applicable. This module has not been deployed by this task.
