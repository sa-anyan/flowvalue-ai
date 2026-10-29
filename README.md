# FlowValue AI — controlled rebuild

This branch is a deliberate clean start for the **entire application**, authorised by the founder on 29 October 2026. It contains product requirements, repository instructions and licence records. There is currently no runnable frontend, backend, parser, costing engine, database migration or deployment configuration in this branch.

## Recovery checkpoint

- Repository: https://github.com/sa-anyan/flowvalue-ai
- Checkpoint commit: `a6c0a471ba1669ed10abbceeae80fa3a9006f612`
- Checkpoint branch: `codex/checkpoint-before-costing-rebuild-2026-10-29`
- Annotated tag: `checkpoint-before-costing-rebuild-2026-10-29`
- New working branch: `codex/controlled-rebuild`

The complete earlier application remains in the checkpoint. Recover individual files/features only when required, reviewing dependencies, licences and tests before bringing them into this rebuild. Do not merge the entire checkpoint by default.

```sh
# Inspect a previous file without restoring it:
git show checkpoint-before-costing-rebuild-2026-10-29:path/to/file

# Restore a specifically agreed file into the rebuild:
git restore --source checkpoint-before-costing-rebuild-2026-10-29 -- path/to/file
```

## Build together, one agreed increment at a time

1. Agree the next feature and minimal folder structure with the founder.
2. Review existing checkpoint code before deciding whether to reuse it.
3. Add only files needed for that increment; do not create speculative future modules.
4. Keep one canonical implementation per calculation, with traceable sources and tests.
5. Preserve explicit unknowns; neither an AI suggestion nor a textbook name proves a valid cost method.

The full founder vision remains in `docs/analyst-workflow-specification.md` and `docs/product-build-roadmap.md`. Historical implementation/acceptance records under `docs/` describe the previous application and are not claims about this clean branch. References to old source paths or parser scaffolds can be inspected in the checkpoint; they are not active implementations here. `frontend/AGENTS.md` is retained as repository guidance, not a frontend implementation.

## Local-only archive

Ignored environment files, dependency/build caches, outputs and private references have been moved outside this Git repository to:

`/Users/user/Documents/ChatGPT/FlowValue-local-archive-2026-10-29/`

Do not commit that archive. It may contain credentials and private material. Hosted Supabase data, provider configuration and the existing production deployment are unchanged; this source reset does not reset cloud systems. Local development servers were stopped deliberately.

Original FlowValue code remains proprietary under `LICENSE`. Preserve `THIRD_PARTY_NOTICES.md` when assessing reuse; it documents historical dependencies and does not imply they are installed in this new branch.
