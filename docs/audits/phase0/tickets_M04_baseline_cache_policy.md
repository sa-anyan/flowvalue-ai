# FV-G0-M04 — Align baseline CI environment with cache-contract tests

Status OPEN, documentation-only corrective ticket. Owner Engineer2. Severity Medium. Related M0.4/IW-06 and R-17.

The draft `.github/workflows/backend-baseline.yml` added during initial Phase0 globally sets `FLOWVALUE_AI_RESPONSE_CACHE=false`. Four existing tests expect the documented cache-on behaviour using their own synthetic providers/temporary stores:

- test_analyst_workflow.py::SpecialistTests::test_independent_roles_are_cached_and_ownership_disclosed
- test_automatic_equipment_inputs.py::test_llm_routes_input_then_python_derives_size_and_caches
- test_equipment_matching.py::test_only_equipment_names_and_separate_non_numeric_context
- test_orchestration.py::OrchestrationTests::test_ai_cache_failure_and_manual_priority

The first clean environment run faithfully reproduced that conflict:5 failed/1714 passed/3 skipped,367 passing subtests. The fifth failure is separate R-01. Cache-off may be correct for an actual fresh-assessment campaign, but is not the baseline contract of these four cache tests. A repeat run with the variable absent uses the application's baseline default, only synthetic test-owned cache entries, no real stored project results or live provider calls.

Proposed repair for separate review: remove the global override or explicitly scope cache-on for cache-contract tests, while preserving dedicated cache-off behaviour tests. No test assertion should be weakened; do not turn real AI caching back on in unrelated fresh-pricing campaigns. Keep credentials and production assessment databases absent.

Closure: four cache tests pass with intended controlled setup; cache-off tests still verify no reads/writes; full suite exposes only legitimately unresolved application failures; hosted workflow runs on a reviewed commit; logs contain no secrets. No GitHub issue or CI change was made during this reconciliation task.
