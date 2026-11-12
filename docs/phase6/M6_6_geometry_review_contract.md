# P6 M6.6 — Reviewed 3D geometry evidence contract (proposal)

**Status:** specification only; no 3D implementation or verified plant layout is claimed. **Ownership:** Engineer 2. **Baseline:** Engineer 2 development, pending PR #36 integration decisions.

## Purpose and trust boundary

A 3D scene is not automatically a verified engineering drawing. Keep three distinct categories: **source-verified** (geometry and topology supported by cited engineering evidence and reviewed), **reviewed conceptual** (explicitly approved simplifications with stated limits), and **illustrative** (non-engineering placeholder). Never promote illustrative shapes or AI-proposed connections to as-built geometry or verified pipework.

## Minimum asset record

Every displayed asset must retain canonical physical equipment key (not display tag alone), case/version, equipment class, dimensions with units and dimension basis, coordinate/reference-frame convention, geometry source and source location, geometry revision, review status/reviewer/time, and any explicit simplifying assumptions. Unavailable dimensions remain absent, not zero. A default glyph or schematic symbol must be labelled illustrative. Geometry revisions must not overwrite the original engineering source.

## Connectivity contract

Draw verified process links only from accepted source-backed endpoints, with evidence IDs and explicit direction. Mentions, directional-text proposals, unresolved endpoints, conflicts and inferred topology must be rendered differently or omitted, never as solid verified piping. Keep distinct same-tag assets separate. 2D and 3D representations must refer to the same canonical stream/equipment identities; neither may silently edit the engineering model.

## Validation fixtures

1. Equipment with complete reviewed dimensions and source-linked connection.
2. Missing dimensions and no coordinates: illustrative placeholder only.
3. Two physical units sharing a display tag: two independent assets.
4. Contradictory stream endpoints: no verified pipe.
5. Text-only equipment mention: no verified physical connection.
6. Changed source revision: geometry review becomes stale pending reassessment.
7. Unsupported units or unknown coordinate frame: reject verified positioning.

## Acceptance before implementation

Reviewers approve supported asset classes, dimensional tolerances, visual distinction of status, geometry export format, performance/security limits and source/version reconciliation. Test that a scene can be reproduced from the same reviewed source and canonical project version. No user-uploaded scripts or model-generated executable geometry are permitted.

**Dependencies:** M6.4 mapping review, M6.5 connectivity contract, P2 provenance/versioning and approved integration baseline. **Out of scope:** CAD certification, P&ID generation, piping stress/layout verification, digital twin, or G6 acceptance.
