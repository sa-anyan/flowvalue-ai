# Shared equipment resolution

This package reconciles explicit user-reviewed physical scope and describes canonical sizing/costing outcomes. It does not contain a second costing or TEA engine.

- `scope`: confirmed alias chains and source-preserving split asset views.
- `knowledge`: live canonical model/sizing metadata; no invented defaults.
- `review`: common resolution/coverage register.
- `comparison`: canonical before/after values.

See [implementation and acceptance report](../../docs/equipment-resolution.md). Manual prices live in the existing equipment costing package, engineering arithmetic in `engineering_sizing`, and uncertainty in the existing two-page Monte Carlo module.
