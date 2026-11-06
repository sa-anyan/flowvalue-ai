# Fresh equipment pricing reliability investigation — 5 November 2026

This investigation does not establish universal workbook compatibility or a
validated design/cost estimate. The old 29/29 demonstration reused accepted
engineering assumptions. It was not a cold-run reproducibility test.

## Failures addressed

- Reconcile duplicate tags before matching so model selection sees the same
  merged stream evidence as sizing. Preserve excluded rows for restoration.
- Bind source-word hints to the target tag. An upstream centrifuge named in the
  same sentence is not an exact-word match for the downstream unit.
- Bound matching batches. Restrict conversion model IDs, source IDs, parameter
  names and derivation names to the actual request. Validate each equipment
  decision independently; retry unavailable conversion batches item by item once.
- Retry a workbook-review timeout once for that region; retain other regions.
- Let the thermal adapter own LMTD; retain redundant AI bindings in the audit
  rather than executing an incomplete second thermal calculation.
- Supply source composition as context, with component identity and cell lineage;
  do not substitute component quantities for total-stream calculation inputs.
- Enumerate bounded temperature-only feasibility hypotheses using canonical
  Python derivations. These are not confirmed topology, fluid pairing or duties.
  Equal outlet temperatures can still permit countercurrent heat transfer.
- Convert Nottingham inputs to native units at the canonical equipment handoff.
  Do not pass Garrett-style conversion context into a native Nottingham equation.
  Keep that context in source/sizing evidence. Manual prices are unaffected.
- Report a missing sizing coordinate explicitly rather than a misleading boolean
  numerical-validation error. Missing one cost must not discard its neighbors.

## Additional conversion and evidence safeguards

- Expose canonical model input quantities, units and unresolved coordinate issues
  to matching. A name match alone does not establish an executable cost model.
- Preserve original workbook names alongside interpreted labels so an earlier
  “unclassified” label does not suppress contextual identification.
- Connect gas compression sizing to the existing deterministic engineering sizing
  calculator. Standard-volume costing coordinates require explicit reference
  temperature, absolute pressure and compressibility; carry that reference through
  to the costing handoff. These are distinct from actual volumetric flow.
- Reject gas-reactant feed as bulk fermentation-liquid throughput for vessel-volume
  or mixing-power conversions. This targeted safeguard is not universal process
  validation and does not replace an actual broth/design basis.
- Provide thermal parameter contracts for sensible, phase-change, enthalpy and
  explicitly assumed-duty paths. Missing data stays explicit.

## Verification boundary

The targeted current-code regression suite passed 107 tests. Local backend health
and frontend entry returned successful responses after restarting the backend.
This is not a claim of complete browser-driven upload verification, fresh AI
repeatability, universal workbook support or engineering validation. Development
runs with evolving code must not be presented as identical-version replicates.

## Cold-run protocol

`tools/audit_fresh_equipment.py` accepts an arbitrary workbook and user context.
Each run starts a new private database and empty plan, reparses the raw file,
uses fresh AI calls, and bypasses all AI-response cache reads/writes. No previous
project prices, guesses, manual overrides or demonstration templates seed a run.
Output is private engineering data and must remain outside public source control.
Optional `--python-ingestion` skips workbook-wide AI review while still performing
fresh source parsing, AI matching and AI sizing; do not describe those runs as
full workbook-AI-review tests.

Example (configured AI environment, repository root):

    PYTHONPATH=. python tools/audit_fresh_equipment.py INPUT.xlsx \
      --description-file project-context.txt --output outputs/fresh-audit --runs 2

The local development-loop harness also retained per-call source context and
response traces in ignored `outputs/fresh-consistency/`. Read the local final
report for measured counts, evolving versions, remaining uncertainty and the
acceptance result. Do not equate passing unit tests with fresh AI consistency.

## Remaining limits

Recognising a family is different from having a complete equipment design or a
supported cost model. AI can propose explicit preliminary assumptions when an
operation is understood; missing functions, incompatible source conditions and
absent models remain exceptions. The engine must not rewrite a source pressure,
use oxygen feed as broth throughput, or price a whole electrochemical package as
a vessel merely to reach a coverage target. Independent fresh AI proposals may
still choose different assumptions. No claim of deterministic fresh AI decisions
is made by these fixes.

## Follow-up: explicit user clarifications and production sizing

The founder confirmed a separately tagged bioreactor remains separate, the PD
operation is a pump, and the reported gas-unit pressure must be preserved. Fresh
follow-up inputs include these user clarifications, not prior AI estimates. Matching
now explicitly carries names across occurrences of the same tag.

`bridges/production_sizing.py` adds an independently tested production/productivity
volume scenario. It requires explicit product rate, allocation, volumetric
productivity and working fraction. It creates no broth flow or physical connection,
and does not validate fermentation kinetics or gas transfer. Assumptions remain
editable and distinct from workbook measurements. The drawer omits the source-flow
selector for this route because no stream flow is being converted.

Current follow-up checks: 112 targeted tests passed and frontend production build
passed. Private follow-up run evidence remains under ignored outputs.

### Signed thermal arithmetic and source precedence

Python now supplies bounded signed enthalpy-pairing hypotheses before AI selects a
thermal basis. They are not confirmed topology or common-reference duties. The
canonical thermal calculation uses the same signed-difference helper.

For multiple thermal observations, a direct source-cell reading takes precedence
over a conflicting inferred interpretation. The selected observation and every
alternative are retained in `source_selections`, and a warning is surfaced.
Equivalent duplicate readings may share one calculation basis; conflicting direct
readings remain unresolved unless a provisional source-cell basis is explicitly selected with rationale. No source observation is overwritten.

The final targeted regression suite passed 117 tests. Follow-up focused cold runs
26 and 27 each priced 28 of 29 active tags, leaving only the electrolyser. These
two runs skipped workbook-wide AI review; the subsequent full-review runs are
reported separately in the private audit. Prices remain assumption-based; stable
coverage is not proof of identical fresh AI assumptions or industrial validation.

### Explicit thermal source-cell choices

`thermal_basis.source_choices` carries role, property, measurement ID and rationale
into the canonical thermal calculation. Python checks the observation belongs to
the selected stream and property, rejects malformed or duplicate selections, and
records alternatives without changing the workbook data. The drawer provides
source-cell dropdowns for conflicting readings, and clears dependent choices when
a role's stream changes. Older saved inputs without this field normalize to an
empty list; no source is invented by that migration.

The bounded repair pass now has an independent preliminary-estimate review role.
It distinguishes missing ordinary design assumptions from unavailable models or
physical incompatibility, while retaining genuine blockers. Conditional sizing at
reported gas pressure must preserve that pressure and disclose unvalidated
pressure-rated package/thermal-design scope.

### Bounded completion of omitted thermal inputs

The canonical thermal module declares the numerical parameters required by each
duty method. After source derivations, a proposal with omitted required inputs
gets one bounded completion request that can return only those missing names,
values, units, rationale and limitations. Existing inputs, model and stream/source
choices cannot be returned as replacements. Unsupported completion stays unresolved;
no numerical default is inserted by Python. Added inputs retain `llm_estimate`
status and `llm_input_contract_completion` origin. The same deterministic thermal
and costing paths then run. This does not run an LLM in Python-only recalculation
or change user-approved inputs.

## Final measured acceptance for this follow-up

Final full fresh backend runs 38 and 39 each priced 28 of 29 active tags, leaving
only the electrolyser. Each run used raw workbook ingestion, full AI workbook
review, empty initial plans and fresh matching/sizing calls. Both response-cache
tables were empty, all active AB quantities were 2, and every priced cost was
finite and positive. The targeted regression suite passed 134 tests; frontend
production build passed. A completed fresh result also rendered 29/28/1 counts in
the browser and the final result passed the frontend-proxy API checks.

This establishes repeated preliminary pricing coverage for the tested workbook,
not universal support, identical fresh AI assumptions/prices or industrial design
validation. Installation and unsupported package scope remain separately flagged.
Private run-by-run differences and historical failed development runs are retained
in ignored outputs/fresh-consistency; they are not public benchmark data.

Input repair is bounded to three attempts and includes the rejected proposal and
exact binding error/allowed source IDs. Only unresolved units enter repairs;
accepted neighbors remain unchanged. Local `FLOWVALUE_AI_RESPONSE_CACHE=false`
disables both response-cache reads and writes. The local response-cache table was
cleared without deleting project snapshots or approved assumptions.
