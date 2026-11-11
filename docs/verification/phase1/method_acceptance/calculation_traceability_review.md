# Calculation traceability review — METHOD-001

**Result: PARTIAL, with a specific FAIL against G1 paragraph120.**
No Engineer-2 schema, ingestion, API, frontend or persistence code was modified.

## Observed native route

`orchestration/sizing.py:derive_size` dispatches registered method IDs to
`engineering_sizing/adapter.py:derive`. The adapter reads an unambiguous
normalized source observation and retains its evidence ID, method ID, original
sizing/assumption specification, parameter-unit conversion traces, calculated
formula/details and conditional endpoint envelope. `calculate()` returns the
result and native unit. Original records are available through the retained
canonical report rather than copied into every native return tuple.

`evidence/trace_probes.json` contains one isolated source-linked reference per
registered ID, including inputs, units, returned values and audit objects. These
are synthetic critical-reference records, not an ingestion test or project run.
Each nominal result agrees with the independently specified existing fixture.

The equipment block at `blocks/equipment/calculation.py` obtains this return and
places the audit in its sizing evidence; it carries a fuller copy under the
OpenPyTEA `input_provenance.sizing` path. The enabled bridge route uses
`unit_conversion/bridges/service.py:evaluate`, with source_measurements,
original_user_inputs, user_inputs, derived_inputs, parameter_unit_conversions,
intermediate value/unit and final conversion evidence. It retains source rows
and explicit context better than a bare native call, but has the same missing
engineering-method software-version binding.

## Exact gaps

**METHOD-TRACE01 — runtime method version missing (Engineer 1 / shared schema integration).**
Neither `engineering_sizing.registry.calculate` nor the adapter return includes
an engineering method implementation version/hash. The adapter's `method` is a
name; its `calculation.formula` can stay identical while code/guards change.
The source IDs and original assumptions survive, but they are not a binding to
the exact engineering executable. The three supplemental helper results likewise
return formula/scope but no immutable implementation version. A costing model ID,
source publication year, assessment ID, or Monte Carlo-wide source fingerprint
is not a demonstrated per-engineering-calculation version record.

The exact loss point is the native result construction/adapter audit dictionary:
no version is generated there, so the equipment caller cannot preserve one from
that object. METHOD-001's external `implementation_manifest.json` supplies hashes
for this verification packet only. It does **not** repair existing production
assessment lineage or retroactively version historic calculations. This is why
G1 paragraph120 is FAIL rather than being marked PASS from a source hash saved
next to a test report.

**METHOD-TRACE02 — compact source references need their immutable input snapshot (Engineer 2/shared contract).**
Native `source_evidence` contains report-local IDs; the normalized primary value
and original workbook coordinates are recovered through the canonical report.
That is adequate within an intact matching report, but a native audit copied by
itself is not a standalone immutable input snapshot. The review did not establish
that every save/export/reopen path pins the correct report revision with those
IDs. That requires shared integration evidence, not a change to extraction here.

**METHOD-APP01 — physical applicability and warning presentation (shared).**
The new compressor warnings survive the existing adapter path in focused tests.
The gross/design mixing-volume basis is now explicit in its audit. Rendering
these nested warnings in every user view/export was not tested or changed. The
raw native methods cannot verify phase, resin performance, qualified U/loading,
EOS property provenance or professional design acceptance from scalar inputs.
Some legitimate shortcuts are supplied assumptions, not workbook facts. In
particular omitted sensible enthalpy currently means zero in phase_change_duty;
that is a no-sensible-change/saturation assumption and must be disclosed in the
project basis, not presented as a full process energy balance.

**LEGACY-TRACE/VALIDITY — reachable legacy routes remain distinct (Engineer 2 integration).**
`derive_size` still has legacy mass_residence, volume_residence,
mass_to_volume_flow, stream_property and supplied-dimension branches outside the
12-ID registry. They are existing contextual derivations/pass-through routes,
not deprecated merely because they lack registered IDs. They do not receive the
same complete native validation/version/provenance contract. A direct proposal
size can return with no sizing audit; stream_property is a pass-through, not a
validated equipment design. These require shared dispatch/lineage reconciliation
before claiming every supported route has the canonical native safeguards.
No legacy branch or schema was modified under this assignment.

## Review packet versus production traceability

For reproducibility, this packet records exact source hashes (including dirty
working-tree content), original reference fixture hashes, explicit inputs,
expected values, output units, method-specific tolerances and validity limits.
`evidence/reproduce.py` refuses a mismatched source tree and independently checks
all20 designated examples. It does not generate expected values from production
functions. It ran successfully in the recorded Python environment.

This permits an independent reviewer to reproduce the designated reference
calculations from the matching source tree. It is not an external reviewer's
signed acceptance, an immutable historical assessment migration or a blanket
UI/persistence gate pass. Commit HEAD alone cannot reproduce the current dirty
working tree; the manifest and matching source content must accompany review.
