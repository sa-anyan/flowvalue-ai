# Stream-centred Excel parser v3 — engineering review

This is a bounded software extraction validation, not industrial process certification or a universal-compatibility claim. Production deployment is expressly excluded from this task. Work is isolated on `codex/stream-parser-performance`.

## Baseline and root causes

Baseline source: `a4db295` (`workbook-pipeline-2.0`). The audit's four criteria were not completely met. A description-table hit selected an adapter for an entire worksheet, hiding other layouts on that sheet. Description-first numeric stream detection lost component bases for alphanumeric-ID tables. Equipment grouping by tag merged unrelated sheets, then the second register builder created duplicate units. Equipment records copied numerical stream evidence and sometimes referenced a nonexistent `description-tags` table. Inlet/outlet strings were not scoped foreign keys. XLSM read-only loading omitted merged-header metadata. Formulas and cached values required two full library opens. Repeated unit-regex searches dominated extraction CPU.

## Architecture and compatibility

1. Retain the existing preflight: extension/signature, ZIP expansion/entry encryption/duplicate limits, XML entity rejection, worksheet/dimension/merge/style limits, upload/body limits, formula/text bounds and killable constrained-worker deadline. No AI, macros, script execution or external-link refresh.
2. Reuse the validated OOXML scan for formula caches and merge metadata. One read-only openpyxl pass retains formulas (including library-expanded shared formulas), styles and ordinary cell values. XLS stays on the existing bounded xlrd path. Unsupported shared-string formula caches are flagged; never replaced with an index as if it were engineering data.
3. Detect labelled table regions. The grouped stream adapter handles explicit stream IDs and component/description headers; the canonical row/column/long-form adapters handle other regions on the same sheet. Numeric/alphanumeric IDs and streams without descriptions or tags remain records. Explicit merged stream headers define subcolumn groups. Units determine component mass/volume/molar/fraction basis; component names come from source labels, not numeric guesses.
4. Build authoritative stream entities. Workbook digest, source sheet/table/ID cell and case scope stable keys. Preserve raw values, units, cell/header references, formulas, caches and statuses. Missing/invalid fields remain explicit. Hard output limits reject rather than truncate a successful report.
5. Construct one scoped equipment register and source-backed connection records. `stream_keys` reference authoritative stream entities; equipment does not receive copies of numerical stream rows. Connection roles distinguish mention/source/destination, with basis, evidence IDs and status. Explicit unit-ledger inlet/outlet lists are resolved only to a unique stream key in the same worksheet/case; unknown or duplicate references remain unresolved. Ambiguous/conflicting endpoints remain unresolved; absent endpoints have no fabricated equipment key. Same tags across different sheets/cases remain separate.
6. Run deterministic review after mapping. Validate scoped duplicates/conflicts, missing fields, units, formulas, endpoint gaps and component totals. Validate all entity/table/evidence/connection references before returning the report. Component-volume sums are worksheet-arithmetic observations, not proof of physical volumetric additivity. Physical process balances still require declared regimes and boundaries.

The legacy `parse_xlsm` function now delegates to this same engine; its former property copier is no longer an active parsing path.

The response retains `flowvalue-balance-v1`, existing fields, endpoint and import workflow, adding defaulted `stream_keys` and `connections`. The current Data tables resolve new scoped references and retain a legacy-reading path for saved reports with copied observations. Dedicated HYSYS export extraction, CSV/JSON, native DWSIM and trusted BioSTEAM remain on their existing paths. This does not implement the other adapter stubs.

## Reference evidence and completeness

The available original is `Mass Balance Team 8.xlsm`. A file named `Mass Balance Team 8(1).xlsm` was not found; no claim is made that an unseen revision is identical. The unchanged available file is retained as `backend/tests/fixtures/parser_v3/team8-reference.xlsm`; see the benchmark record for its SHA-256.

V2 and v3 both retain 14 identified main-sheet streams and 18 streams on the separate Energy calculation sheet. These are separate process contexts, not one combined physical model. V3 tests independently specify all fourteen main-sheet IDs, total flows, T/P/enthalpy, component mass values/names and key source cells. Untagged streams 13/14 remain present without invented equipment. All seven named equipment tags are retained. New tests close mixed-layout, missing-unit/component, repeated-ID/case, formula-cache and shared-reference defects; counts alone are not an accuracy test.

The workbook itself causes the two 100 kg/h differences:

- `Mass and Energy Balance!AD37 = SUM(AD28:AH35)` excludes Biomass at `AD36` (100 kg/h). Reported total 125927.625 versus component sum 126027.625 kg/h.
- `Mass and Energy Balance!AX37 = SUM(AX28:BB35)` excludes Biomass at `AX36` (100 kg/h). Reported total 900 versus component sum 1000 kg/h.

The parser retains these formulas and stored source values and flags both discrepancies. It does not rewrite or recalculate the source workbook. Other sheets contain error cells and different project metadata; unsupported content remains flagged.

## Measurement protocol

`tools/benchmark_meb_parser.py` runs one profiled warm-up, 20 warm-process samples and 20 timed fresh constrained-worker samples plus a separately recorded first fresh-worker launch per workbook. Monotonic `perf_counter` timing includes upload-byte spooling, safe reading/extraction/mapping/review, JSON serialization/deserialization and canonical response validation for the worker measurements. Network transfer, multipart transport latency and hosted service wake-up are excluded. Fresh-process workers execute the same `app.parsers.excel_worker` entry point with its CPU/deadline/address-space policy; macOS has no Linux `RLIMIT_AS` ceiling. RSS comes from each worker's OS high-water mark. P95 uses nearest rank; raw samples and profiler output are retained. Warm-stage medians separate opening/preflight, extraction, mapping, validation and JSON serialization.

These are local macOS/Python 3.12 worker measurements, not a Render-hosted cold-start SLA or proof that every file within size limits parses successfully in ten seconds. Unsupported/resource-excess files are rejected, not counted as successful performance cases.

See the accompanying `parser-v3-benchmarks.json` for results and raw samples. Reproduce from `backend/`:

```sh
PYTHONPATH=. .venv/bin/python ../tools/benchmark_meb_parser.py tests/fixtures/parser_v3/team8-reference.xlsm --runs 20 --output ../outputs/parser-v3/reproduced-team8.json
```

For the baseline, extract `git archive a4db295 backend` into a separate directory and run the same harness with that backend as the working directory, the current backend virtual environment and an absolute fixture path. Do not switch or deploy the production branch to benchmark.

## Verification and limitations

Final checks: 239 backend tests and 38 frontend tests passed. Ruff and Python compilation/schema checks passed; frontend ESLint, TypeScript and production build passed. The local upload/API/Data-table smoke test passed with component names and source cells for Biomass at AD36/AX36, plus separately scoped untagged streams 13/14. Local ignored `.next` files repeatedly acquired duplicate generated type declarations; frontend lint/typecheck/tests were additionally run from a clean temporary copy, without adding source exclusions to hide errors. Backend static type checking is not configured in this repository; available gates include Ruff, Python compilation/schema validation, pytest, frontend ESLint/TypeScript/tests/build and a local browser upload into the Data properties view. No paid AI requests are used.

Known limits: supported labelled regions only; no OCR, embedded chart/table reconstruction, arbitrary simulator-native binaries, formula recalculation or semantic understanding of an unlabeled worksheet. Headers that cannot establish stream/component/unit roles remain unsupported. Phase-separated subcolumns and nonstandard composition bases need dedicated mappings; physical volume additivity is not assumed. Limits of 4 MiB upload, 40 sheets, 150k scanned cells, 5k extracted values and bounded entities/observations/issues remain. Real-world evaluation covers this one supplied project and synthetic regression/stress fixtures, not a broad independent industrial corpus. The separately named `(1)` workbook revision and actual hosted Linux performance remain untested.


## Final benchmark results

Fresh-worker end-to-end seconds, 20 timed samples per case; an extra first fresh launch is recorded separately in the JSON.

| Fixture | Before median / P95 | After median / P95 | After worst | After peak RSS MiB |
| --- | ---: | ---: | ---: | ---: |
| Team 8 | 3.000 / 3.353 | 1.610 / 1.639 | 1.844 | 50.8 |
| 500-stream vertical | 1.977 / 2.321 | 1.331 / 1.481 | 1.580 | 66.2 |
| Mixed merged/vertical | 0.793 / 0.815 | 0.769 / 0.851 | 1.124 | 42.5 |

Baseline measurements time the old response, which fails new component/reference checks; they are not an accuracy endorsement. The two larger fixtures improved substantially. The tiny mixed fixture is dominated by process startup; its P95 did not improve, while remaining far below ten seconds. All measured representative runs were below the target. This is not a guarantee for untested workbook structures or hosted service wake-up times. Raw warm/fresh distributions, first-launch observations, profiler call counts and stage medians are in the JSON.

Final disposition: implemented and checked for the stated supported cases, on a review branch only. The exact `(1)` revision and hosted Linux performance are not validated by these local tests. Production deployment was not requested and was not triggered.


Concurrent source updates through `351d3ea` were integrated into the review branch. The legacy CLI/property helpers retain those changes; the XLSM compatibility function continues delegating to the tested v3 engine. All 239 backend tests passed again after the integration. The baseline remains pinned to `a4db295`.

The optional existing AI dialogue remains tag-based; cross-scope tag disambiguation in that AI workflow is not part of this parser validation. Use the scoped deterministic registers and review ambiguous multi-case descriptions before relying on AI comparison.
