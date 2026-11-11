# FV-P1-TRACE01 — Engineering method version traceability

**Date:** 11 November 2026  
**Engineer 1 decision: PASS within the owned calculation/audit boundaries.**
Shared orchestration/storage/reporting retention remains unaccepted. **G1 is not
passed; METHOD-LEGACY01 remains open.** No scientific review was reopened.

## Change

All **12 registered sizing IDs** and **three supplemental estimators** now emit
an additive `engineering_method` object in their applicable audits:

```json
{
  "method_id": "vessel_hold_up",
  "method_version": "1.0.0",
  "implementation_fingerprint": "sha256:<64 hexadecimal characters>",
  "fingerprint_scheme": "flowvalue-loaded-engineering-v1",
  "execution_layer": "native"
}
```

The complete fixed15-ID version map is in `engineering_sizing/versioning.py`.
Each starts at1.0.0 as the first explicit versioned contract; this does not imply
new equation validation or invent a version for earlier saved calculations.
Reviewed changes to equations, assumptions or input/output meaning require an
explicit version bump. The fingerprint also changes with relevant loaded code
or helper/constant changes even if a version bump is accidentally omitted.

The implementation hashes **loaded Python code**, defaults, relevant owned
helper/global definitions and constants, method contracts and versioning logic.
It does not label newly edited on-disk source as already executed. Nested code,
input-preparation helpers and declared native dependencies are included. Source
filenames, debug line positions, timestamps, machine paths, object addresses,
Git HEAD and random IDs are excluded. Identical installation relocations and
hash seeds were checked. Python bytecode/runtime changes may legitimately
change the digest; it is not a binary-environment/SBOM attestation.

Only immutable code-object digests are memoized. Referenced globals and dependency
bindings are inspected afresh for each snapshot; no engineering result, project
input or assumption is cached. The finite owned dependency contract must be
maintained when new dynamic helper routes are introduced. Closure input data is
not an implementation version and remains in input provenance. Concurrent live
code mutation during a calculation is not a supported execution mode.

## Boundaries and compatibility

- `registry.calculate`: all12 canonical method IDs; existing result tuple and
  numerical kernel audits retained, with additive version metadata. Raw internal
  mathematical helpers remain kernels; callers needing a registered method
  identity use this canonical dispatch boundary.
- `adapter.derive`: top-level `engineering_method` identifies the sizing/input-
  preparation layer; `calculation.engineering_method` retains the native layer.
- Mechanical shell mass, productivity-based vessel volume and mixing-power
  helpers: versioned supplemental audits with existing formulas/scope unchanged.
- The existing equipment bridge: applicable recipes expose top-level version
  metadata and retain nested calculation metadata. Recipe aliases map explicitly
  to the registered engineering family. Unit-only recipes are not assigned a
  fabricated engineering method.

Different execution layers intentionally have different fingerprints. Identity
is the complete method/version/fingerprint/scheme/layer tuple, not the version
string alone. A fingerprint identifies implementation, not calculation inputs
or scientific suitability. Existing assumptions, source IDs/rows, original user
inputs, conversion evidence, warnings, ranges and numerical results are retained.
No kernel equation, coefficient, public signature or tuple shape was changed.

Changed production files:

- New `backend/engineering_sizing/versioning.py`.
- `backend/engineering_sizing/registry.py` and `adapter.py`.
- `backend/equipment_costing/unit_conversion/bridges/`:
  `mechanical.py`, `production_sizing.py`, `liquid.py`, `service.py`.

New focused tests: `backend/tests/test_engineering_method_versions.py`.
No Engineer2 orchestration, schema, API, persistence, frontend, costing equation
or project data was changed. The exact pre-task hash comparison is retained in
`evidence/TRACE01/summary.json`; pre-existing work and historical evidence remain.

## Verification

**96 passed,0 failed,0 skipped** in the final affected selection: **45 new identity/
provenance checks** plus51 existing affected method/bridge regressions. Tests
cover all15 mappings, unchanged numerical references, repeatability, changed
loaded code/helpers/constants, explicit version changes, nested preparators,
path/debug-line independence, two hash-seed subprocesses, unchanged loaded code
after an unexecuted disk edit, native/adapter/bridge outputs, ranges and lineage.

The existing304 native numerical checks and prior compressor/heat-duty/pump/
Boolean/unit/R-01 evidence are reused; the numerical kernels are unchanged.
No full-suite rerun, new external research or dependency installation occurred.
The focused runner disables AI/cloud, blocks network sockets and isolates storage.
Exact files, JUnit XML, runtime and an example audit are under `evidence/TRACE01/`.

## Engineer 2 handoff contract — required, not yet accepted

1. Retain `engineering_method` **verbatim from the executed result** in the saved
   sizing audit. Preserve both top-level preparation/bridge and nested native or
   supplemental metadata where present. Do not regenerate it at save/render time
   using a newer worker, Git HEAD, model year or caller-supplied label.
2. Bind it to the same immutable input/report revision, assumptions, normalization
   evidence, output value/unit and existing source lineage. Implementation
   identity alone is not a sufficient calculation-cache key.
3. Retain all five fields through recalculation, version history, exports and
   reporting. Compare the complete identity tuple when reconciling results;
   different fingerprints must not be merged merely because both say1.0.0.
4. Missing metadata in historical or legacy results stays explicitly missing/
   unversioned. Never backfill a current fingerprint as proof of an earlier run.
5. Verify save/reopen/export preservation and user-visible applicability warnings
   in Engineer2's integration scope. This ticket does not certify those paths.

**METHOD-LEGACY01 remains unchanged:** legacy volume_residence returned-25m3
and mass_residence returned-3.125m3 for the recorded negative-flow examples.
Their failing evidence is preserved byte-for-byte; shared orchestration was not
changed or silently assigned native method versions. Source-snapshot integration
and the earlier XLS Boolean/L/s findings also remain separate dependencies.

**Stop after TRACE01.** Engineer1's version-metadata emission is accepted for the
15 owned method boundaries; combined G1 and downstream retention remain open.
No push, merge, deployment or P3 implementation occurred.
