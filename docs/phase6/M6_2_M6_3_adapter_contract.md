# P6 M6.2–M6.3 — Simulator export adapter contract (proposal)

**Status:** specification only; no adapter is certified or activated by this document. **Ownership:** Engineer 2. **Baseline:** Engineer 2 development, pending PR #36 integration decisions.

## Supported claims and boundaries

The current `backend/ingestion/inputs/README.md` describes 17 input-method scaffolds, not implemented adapters. It documents an existing native DWSIM `.dwxml` route and generic Excel fallback for DWSIM/Aspen; these claims require confirmation against active API code and tests before advertising support. Generic Excel parsing is not evidence of simulator-specific fidelity. No Aspen native project execution or import is proposed.

## Versioned adapter declaration

Each adapter must publish an immutable identifier, adapter version, exact source application and export family, supported source versions (or a tested version range), supported file extensions and signatures, schema/column mappings, unit/property basis rules, feature coverage, known omissions, and evidence fixture hashes. Unknown source versions must be rejected or explicitly classified as unverified; never silently accepted as supported.

## Extraction and reconciliation contract

For every imported stream/property/equipment record, preserve original source name/tag, source file and location, original value/unit, phase/composition basis, normalized value/unit when safely convertible, interpretation status, and unresolved ambiguities. Preserve separate operating cases and physical equipment identities. A simulator tag is not a unique cross-file equipment key. Distinguish zero, missing, not applicable, formula-cache and conflicting observations. Do not infer mass/energy closure without complete declared boundaries and sign conventions. Do not run uploaded scripts, macros, native simulator code, or untrusted expressions.

## Independent fixture matrix

- DWSIM native export: one independently generated supported-version sample, one unsupported-version sample, malformed XML/oversize input, missing equipment endpoints, alternative unit systems, and multi-component stream with declared composition basis.
- DWSIM Excel export: a separately versioned report, including reordered columns, missing values, and duplicate display tags.
- Aspen Plus and HYSYS: exported tabular reports for explicitly declared source versions, separate formats if layouts differ; property bases, temperature/pressure conventions, component fractions, cases and disconnected units must be checked against original exports. Do not treat one generic Excel success as both products' acceptance.
- Each fixture records file hash, expected canonical observations, supported/unmapped fields, mass/energy reconciliation applicability, and expected reject/warn outcomes.

## Acceptance checklist

1. 100% of declared supported fixtures import and reconcile to independently prepared expected records.
2. Unsupported source versions and unmapped fields are visible.
3. Original files are unchanged; no invented equipment, properties or piping.
4. Original and normalized units/bases reconcile, with ambiguous cases unresolved.
5. A reviewer can reproduce the canonical result from the source export and adapter version.

**Dependencies:** P2 canonical model/identity and provenance review; approved G2 integration candidate; source exports with permission to use. **Out of scope:** proprietary simulator automation, native Aspen model execution, thermodynamic recomputation, 3D geometry, and declaring G6 passed.
