# P6 M6.4 — Interactive import mapping and reconciliation contract (proposal)

**Status:** specification only, not a delivered interface or G6 acceptance. **Owner:** Engineer 2. **Base:** `engineer-2/development`; integration audit PR #36 is unmerged and is not an approved baseline.

## Goal

An analyst previews source observations and proposed canonical mappings before accepting them. Import is a reviewed, reproducible transformation, not silent source editing or an AI decision. The original workbook/export remains immutable.

## Required review surfaces

1. **Source identity:** filename, SHA-256, file format/signature, adapter ID/version, detected source version where available, worksheet/table/cell or export object location, case/scenario, parser warnings and supported-format statement.
2. **Proposed mapping:** source stream/equipment/property identifier, original value/unit/basis, proposed canonical key/property/value/unit, conversion method/version, confidence/status, evidence IDs, and mapping rationale. Distinguish physical asset key from repeated display tag.
3. **Unmapped and ambiguous:** show missing, unsupported, conflicting, duplicate, nonnumeric, stale formula-cache and unsupported unit/property-basis observations. Missing and not-applicable are not zero.
4. **Connection review:** explicit endpoint evidence, directional-text suggestions, mere mentions, contradictory endpoint candidates and missing endpoints. Only approved source-supported links may appear as verified connectivity.
5. **Reconciliation:** original-versus-canonical observations; compatible-unit parity, composition-basis and sum checks, case separation, declared boundary mass/energy closure where applicable, and unresolved residuals with evidence.
6. **Approval and revision:** reviewer identity, timestamp, selected mapping, evidence/source hash, canonical project revision, assumption register entry for any override, before/after diff, and stage invalidation/recalculation consequences.

## State model (conceptual, not a new production API)

`uploaded -> parsed -> previewed -> mapping_proposed -> reviewed -> accepted`, with `rejected` or `needs_clarification` outcomes. Every edit after preview requires renewed validation. An AI proposal can only reach `mapping_proposed`, never `accepted` without the authorised review pathway. Unsupported file versions cannot be silently upgraded to accepted.

## Negative and positive acceptance fixtures

| Case | Expected result |
|---|---|
| Source zero mass flow vs blank | Zero retained; blank unresolved |
| Two sheets reuse equipment tag T-104 for distinct physical assets | Separate keys; no automatic deduplication |
| Two source cells conflict on same stream flow | Both preserved; canonical selection blocked pending review |
| 1 t/h vs 1000 kg/h with declared basis | Equal after approved conversion; source values retained |
| Gauge pressure without reference atmosphere | No invented absolute pressure |
| Formula with missing/stale cache | Disclosed; no fabricated calculated result |
| Composition without mass/mole basis | Unresolved rather than assumed |
| Text says 'near P-101' | Mention only, not verified pipe |
| Contradictory source/destination fields | Competing evidence displayed; no verified connection |
| Changed workbook hash after approval | Prior approval not silently reused; downstream freshness evaluated |
| Unsupported Aspen/DWSIM export version | Unsupported/unverified warning; no declared-support claim |
| Valid, fully reviewed mapping | Deterministic canonical output and reproducible review record |

## Engineering and product boundaries

- Reuse the existing `backend/ingestion/balance/models.py` evidence/connection records and P2 canonical identity/provenance/versioning mechanisms rather than creating a parallel authoritative register.
- Reconcile the active upload path `backend/orchestration/ingest.py` with any existing UI import preview. The old `backend/ingestion/inputs/` modules are documented scaffolds; they do not establish implemented adapters.
- Maintain separate `source-supported`, `inferred/proposed`, `unresolved`, and `approved` meanings. A source-supported workbook value is not independently verified plant truth.
- No automatic price changes, economic assumptions, simulation reruns, pipe creation, or production receipt activation.
- Test with independently prepared exports and the P2 real-workbook evidence set; private workbooks and confidential source values must not be committed.

## Dependencies and gate evidence

Before implementation, confirm the approved G2 integration baseline, current API/UI route and project version contract, source permissions, and review authority. G6 requires all declared supported fixtures to import and reconcile as specified; unmapped fields and unsupported versions disclosed; no silent physical reinterpretation; diagrams distinguish verified from illustrative links; reproducibility from originals. This specification is **not** a claim those conditions have been met.

## Proposed implementation order

1. Inventory active preview and approval endpoints/components on the approved integration candidate.
2. Add synthetic tests for source/canonical diff, conflict and stale approval.
3. Introduce the smallest reviewed mapping interface compatible with existing P2 persistence.
4. Validate real files and browser-to-export parity, then seek G2/G6 reviewer signoff.
