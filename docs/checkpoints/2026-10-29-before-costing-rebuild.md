# FlowValue checkpoint before the controlled rebuild

Date: 29 October 2026.

This checkpoint preserves the current application source, engineering parser, equipment catalog, process-context LLM interpretation, existing financial/reporting features, tests and modular costing work before a controlled rebuild. It is a recovery reference, not a production-readiness or independent engineering-validation claim.

## Costing layout at the checkpoint

- `backend/app/engine/equipment_costing/garrett/`: 51 equipment/chart-group modules, explicitly unimplemented.
- `backend/app/engine/equipment_costing/turton_et_al/`: four existing screening correlation modules.
- `backend/app/engine/equipment_costing/legacy/`: retained prior combined engine and source snapshots.
- `backend/app/engine/price_escalation/`: separate price-index models, catalog and generic escalation function.
- `backend/app/engine/costing.py` and `indices.py`: compatibility facades preserving existing interfaces.

Last completed backend regression run: 269 tests passed. Earlier process-context UI work also passed 41 frontend tests, TypeScript/lint/build checks and a local browser check of P-001 match/rationale persistence. These are dated checks of this implementation, not certification. No production deployment was made for these pending changes.

## Recovery workflow

Keep this checkpoint branch unchanged. Work on a separate rebuild branch. Recover individual files using `git restore --source <checkpoint-ref> -- path/to/file`; inspect the resulting diff and test dependencies before committing. Recover a complete feature by reviewing its files/dependencies or cherry-picking an appropriate isolated commit; do not blindly merge all old code into a clean rebuild. The full checkpoint can be inspected in a separate worktree or checkout without replacing current work.

The checkpoint follows `.gitignore`: secrets/environment files, dependency/build caches, local outputs and ignored private references are not included. It does not back up hosted Supabase data, provider configuration, credentials or external original documents. Keep these in their existing secure locations. Original FlowValue licence and upstream notices remain unchanged.
