# B07 · Source, record and physical asset identity

## Implemented contract

- The workbook SHA-256 identifies the exact uploaded bytes and serves as the content revision key. A rename preserves identity. Resaving can create a new revision even when the visible data is unchanged. `previous_source_sha256` records a caller-supplied predecessor. The parser validates hash syntax and rejects self-links. The upload workflow does not establish ancestry, verify that the predecessor exists, or match records across revisions.
- The workbook pipeline retains report-local evidence IDs for existing references. `observation_id` uses the existing stable-key function over the source hash, parser version, sheet, cell, headers, property, component and local extraction ID. It is reproducible for identical bytes and the same extraction implementation. Original value and unit and normalized value and unit remain on the evidence record. A changed extraction method must update its parser version.
- Existing stream and equipment `Entity.key` values remain the record keys. Stream keys use the source hash, kind, sheet, table, case and identifier cell. The equipment register groups source observations by revision, sheet, case and normalized tag as before. Multiple rows folded by that register remain observations on one calculation record. The grouping has no physical-asset authority.
- Equipment-stage `identity_register` carries the record key, display tag, source evidence references and optional physical asset ID. An accepted single-unit alias uses its reviewed target key as the asset ID. An existing reviewed split uses its qualified child key. Status is resolved for those mappings, ambiguous where competing tag or grouping evidence remains, and unresolved where no mapping or conflict is established. Asset IDs are scoped to the current source and plan, with no cross-revision continuity implied.
- SQLite persists the existing JSON. The assessment GET and named-version open APIs project identity into the response. The historical GET and named-version open paths use saved results without calculating. They retain stored keys, quantities, prices and totals. A missing register is reconstructed from saved engineering records and costing rows with persistent keys. Matching tags and recorded duplicate conflicts can mark records ambiguous. Otherwise they are unresolved. Only a previously stored reviewed mapping can establish physical identity in the legacy read path. The register is attached to the existing equipment result or stage. A response without an equipment stage carries the register at the assessment level, preserving the existing results field. Opening a named version creates the normal editable copy without writing projected metadata into either snapshot.

Example of an equipment calculation record and its additional identity projection:

```json
{"equipment_key":"equipment:abc","equipment_tag":"P-101","quantity":2}
```

```json
{"equipment_key":"equipment:abc","display_tag":"P-101","physical_asset_id":null,"status":"ambiguous","aliases":[],"observation_ids":["observation:def"],"legacy_evidence_ids":["v7"],"review":null}
```

## Engineer 1 approval pending

1. Preserve current costing reconciliation. The register folds rows within sheet/case/tag scope. Equipment execution can exclude repeated normalized tags or plain tags represented by an AB pair, with restoration through the existing plan. Existing explicit aliases, splits and quantity handling continue to control calculation inputs. The identity register makes the source and resulting asset interpretation visible.
2. Agree on the review authority and the conditions under which physical identity may influence exclusions, distinct assets, grouped quantities and duty/standby scope. An identity record alone grants no calculation authority. Review a same-tag distinct case, an alias chain, an AB pair and a multi-unit group with no per-asset mapping.
3. The scenario equipment-cost dictionary currently uses display tags as keys. Approve an ordered collection keyed by the effective costing record key with display tag, physical asset ID where available, quantity, scope and price coverage. Preserve every priced record and preserve the existing inclusion policy. Approve the export/UI compatibility approach before replacing the tag-keyed projection.
4. Require stage-to-scenario parity using the same approved inputs for line amount, included quantity, capital scope, CAPEX, OPEX, revenue and financial totals. Include restored same-tag records, alias exclusions, priced and unpriced splits, and deterministic scenario runs. Reconcile scenario line totals against stage totals before approving a projection or aggregation change.



## Recovered and manual evidence

- Numeric recovery and workbook review retain the existing evidence key and assign an observation ID over the source SHA-256 and that evidence key. A changed source hash creates a different observation identity. The originating recovery method is recorded for new observations. Historical recovery records with both keys reconstruct the same ID in the response even if workbook coordinates or method version were omitted. No coordinate or method is inferred.
- Historical records without a recognized stable evidence key or source hash retain their local IDs and expose an identity limitation. This includes pre-B07 manual observations whose original random IDs cannot be matched across historical edits. Existing workbook observation IDs pass through unchanged.
- Manual engineering-register evidence uses the persistent equipment record key and the field role (identifier, name or type). The resulting observation ID survives label changes and deterministic replay. A unique historical local key is preserved when the field is explicitly edited. Its observation ID is assigned independently. Revision starts at 1 for a newly tracked field and advances when its value changes. Identical updates preserve the revision. The saved edit log records assigned observation IDs and revisions so replay preserves them. Earlier untracked revision counts are unknown. The User input, User register and manual strings are existing display markers for a non-workbook source.
- Other project-plan assumptions, commercial inputs and calculated values remain in their existing domain contracts. They are outside the engineering-register Evidence model.

Legacy response example:

```json
{"equipment_key":"equipment:abc","display_tag":"P-101","physical_asset_id":null,"status":"unresolved","review":null}
```

Manual evidence example after a rename:

```json
{"id":"user-input:abc","observation_id":"user-input:abc","observation_revision":2,"observation_method":"manual-engineering-register-1","workbook":"User input","sheet":"User register","cell":"manual","property":"name","original_value":"Feed pump"}
```

## Coverage limits

The register does not split same-scope grouped workbook rows into independent costing records or infer asset continuity across revised workbooks. If a historical costing line has neither an equipment key nor a keyed source record, the identity response marks it unresolved with a missing-key limitation and leaves the key null. The worker output limit is unchanged. Large uploads near that limit need separate coverage.

The identity register is response and stage-result metadata. The costing payload does not consume it. An explicit workbook reparse or engineering edit can change an engineering receipt fingerprint because the engineering payload includes the new observation metadata.


## Verification and acceptance

Engineer 2 B07 acceptance is satisfied for the engineering identity paths above. Numerical reconciliation policy and the scenario interface decisions remain with Engineer 1.

Windows Python 3.12, the Phase 0 test environment and an isolated SQLite database:

- Full backend: `python -X utf8 -m pytest backend/tests -q -ra --tb=short -p no:cacheprovider` — 1,718 passed, 0 failed, 9 skipped, 367 subtests passed, 1 warning in 1,222.17 seconds.
- Focused backend: `python -X utf8 -m pytest backend/tests/test_engineering_identity.py backend/tests/test_engineering_review.py backend/tests/test_review_before_calculation.py backend/tests/test_shared_pipeline.py backend/tests/test_equipment_resolution.py backend/tests/test_orchestration.py -q -ra --tb=short -p no:cacheprovider` — 70 passed, 0 failed, 7 skipped, 1 warning in 278.84 seconds.
- Frontend: `node --test` — 45 passed, 0 failed, 0 skipped, with a Node module-type warning. `node node_modules/typescript/bin/tsc --noEmit --incremental false` exited 0.

The full suite skips eight private fixture cases and one optional pinned OpenPyTEA reference. The focused skips are all private fixture cases. Both backend runs emit the Starlette TestClient/httpx deprecation warning.

The history regression checks the original snapshot JSON, a saved two-unit equipment total of $20,000 and a saved CAPEX total of $32,000. The equipment stage regression still calculates two units at $20,000. The existing manual-price Monte Carlo reconciliation test passes. Its separate same-tag collision case remains an Engineer 1 interface decision.
