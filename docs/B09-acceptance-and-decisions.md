# B09 · Engineer 1 decision and acceptance review

**B09 status: PARTIAL.** Baseline reviewed: `1bce1d1` on `engineer-2/b09-versioning`, [Draft PR #10](https://github.com/sa-anyan/flowvalue-ai/pull/10), stacked on PR #9. Every default below is a proposal. Legacy freshness remains authoritative.

The [standalone contract](B09-calculation-receipts-and-invalidation.md) covers scoped immutable receipts, digest and lineage validation, and separate numerical freshness, provenance and approval states. [4A](../backend/blocks/execution_observation.py) is an opt-in in-memory observation after the normal write, with no production caller enabling it. [4B](../backend/tests/test_receipt_journal.py) demonstrates atomicity in a temporary SQLite fixture. [4C](../backend/tests/test_shadow_freshness.py) compares frozen fixtures without changing results or manufacturing receipts. See the [integration plan](B09-production-integration-plan.md) for commands and the full disagreement matrix.

## Decision register

The order below follows the four 4C disagreements. The six interfaces in the integration plan map to sections 4 (consumed inputs), 1 (semantic output), 5 (append and retention), 5 (fork lineage), 2 and 3 (failed and partial consumption), and 6 (read, export and approval).

### 1. Equivalent numerical output and changed method provenance

- **Proposed default:** Keep the numerical state current when the upstream handoff digest matches and all other inputs are current. Flag changed provenance. Require review before reusing the result in an approved workflow. Define separate authoritative handoff and displayed-result digests per stage.
- **Evidence:** 4A Financial exposed prepared-input, result and ledger digests separately. In 4C, an equal-digest upstream rerun with a different executed method left both numerical checks current, with B09 provenance changed.
- **Alternative and impact:** Require every downstream consumer to rerun on a method change. This increases reruns even when the handoff is equal. Reuse can preserve current totals but must not imply equivalent engineering validity or inherit approval.
- **Acceptance fixture:** Rerun with equal payload and a changed method version/fingerprint, then with a changed payload. Verify unchanged numerical state plus a review flag in the first case, transitive stale in the second, and no implicit approval in either.
- **Engineer 1 — pending:** Approve the digest basis and consumers eligible for equal-output reuse. **Engineer 2 boundary:** Capture executed tuples and expose separate states. Do not decide numerical equivalence or approval policy.

### 2. Failed or blocked attempt retaining an earlier output

- **Proposed default:** Retain the earlier output and show the latest failure independently. Evaluate retained freshness against current inputs and independent method evidence. Preserve the legacy gate for downstream consumption until a specific consumer rule is approved.
- **Evidence:** 4A store writes matched across both failed and blocked outcomes. 4B retained the prior payload. In 4C, legacy was not fresh while B09 found the retained output current with independently matching evidence.
- **Alternative and impact:** Mark all retained output unavailable to consumers, or allow explicitly approved consumers to reuse verified retained output. The former delays downstream runs. The latter can preserve totals but must expose the failed attempt and review state.
- **Acceptance fixture:** After a complete run, inject both failure types with matching evidence, a changed input, and missing current-method evidence. Keep stored values identical. Assert current/stale/unknown respectively and enforce the approved consumer gate.
- **Engineer 1 — pending:** Name consumers allowed to reuse retained results and the evidence each needs. **Engineer 2 boundary:** Keep immutable history and separate pointers. Do not promote retained output into a baseline.

### 3. Complete-to-partial replacement

- **Proposed default:** Keep the new output explicitly partial and the earlier complete payload retrievable. Treat a consumer that previously used a complete handoff as unknown until coverage is verified, even with an equal digest.
- **Evidence:** 4A captured completeness without changing results. 4B retrieved the previous complete payload after a partial attempt. In 4C, legacy was fresh and B09's dependent state was unknown after an equal-digest partial replacement.
- **Alternative and impact:** Pin consumers to the older complete output, or permit the new partial output for approved consumers. Pinning risks mixing revisions. Partial use can omit cost or revenue lines and change downstream completeness or totals.
- **Acceptance fixture:** Replace a complete prerequisite with an equal-digest partial. Preserve both results, show partial status, and verify the agreed coverage gate for CAPEX, OPEX and Finance without presenting missing amounts as zero.
- **Engineer 1 — pending:** Set minimum coverage and partial eligibility per consumer. **Engineer 2 boundary:** Expose completeness and receipt references. Do not choose which lines enter a total.

### 4. Consumed inputs, method capture and newly available optional OPEX bases

- **Proposed default:** Keep legacy whole-stage invalidation until executed consumption is captured. Record optional supply separately from actual use and leave evidence gaps unknown. Prefer explicit dependency binding when the factor or input builder proves consumption.
- **Evidence:** 4A observed optional Revenue supplied to OPEX without claiming consumption. In 4C, newly available Revenue made legacy OPEX not fresh while B09 stayed current on the supplied digest. A changed basis with a captured edge made both stale.
- **Alternative and impact:** Invalidate on optional availability alone, or use consumption-only dependencies once capture is complete. Availability-based invalidation reruns more cases. Consumption-only invalidation could miss newly applicable sales costs or avoided costs if the binder is incomplete.
- **Acceptance fixture:** Cover absent-to-available unused Revenue/CAPEX, consumed basis change, shared observation edits, and missing bindings. Verify stage totals, actual factor/source references and the approved freshness transition.
- **Engineer 1 — pending:** Approve whether availability alone invalidates, which normalized inputs and B07 observations count as consumed, and which executed layers must be recorded. **Engineer 2 boundary:** Instrument observed supply/use and method tuples. Keep coarse legacy behavior when evidence is incomplete.

### 5. Append conflicts, retention and fork lineage

- **Proposed default:** Assemble and validate before the final write. Commit result, receipt, revision and pointer atomically. Replay only the exact immutable delivery. Surface revision conflicts without automatic re-execution. Preserve referenced complete outputs and original scopes in snapshots and frozen scenarios.
- **Evidence:** 4A observation runs after the result write and cannot guarantee atomicity. 4B verified duplicate replay, conflict, SQL rollback, abrupt exit and byte-identical named-version history. 4C kept the frozen scenario reference, bytes and saved total intact after a baseline edit.
- **Alternative and impact:** Re-execute or retry after revision conflicts under a reviewed policy, or archive historical artifacts with stable references. Silent retry can publish against different inputs. Premature pruning can break reproducibility and exports.
- **Acceptance fixture:** Race two completions, interrupt a write, retry an exact delivery, then reopen a named version and a frozen scenario after baseline edits. Verify one winning commit, preserved historical results and no inherited active receipt in a new scope. Repeat the storage contract against an approved isolated cloud transaction path.
- **Engineer 1 — pending:** Approve retry/re-execution and conflicted-attempt retention, output retention lifetime, fork inheritance and scenario rerun conditions. **Engineer 2 boundary:** Design revision checks, transaction and scope validation. Do not activate persistence or prune history without review.

### 6. Read/export labels and approval boundaries

- **Proposed default:** Display saved numerical state, provenance, completeness and latest attempt separately. Show legacy or missing method evidence as unknown. Preserve approval references independently. Matching digests or lineage grant no approval.
- **Evidence:** 4A did not infer missing evidence. 4B preserved saved values and scope. In 4C, legacy output without an immutable receipt could be fresh under legacy checks and unknown under B09 without an invented fingerprint.
- **Alternative and impact:** Suppress unknown or stale outputs from approved exports, or allow clearly labelled historical views. Eligibility affects what analysts can rely on, while the saved ledger and snapshot should remain intact.
- **Acceptance fixture:** Reopen current, stale, partial, failed-retained and legacy cases. Compare JSON/HTML/CSV/XLSX against stored values and recorded methods. Verify labels, no read-time writes or execution, and approved eligibility and reapproval triggers.
- **Engineer 1 — pending:** Approve consumer/export eligibility, stale and unknown labels, approval scope, expiry and reapproval triggers. **Engineer 2 boundary:** Project saved evidence and keep authority separate. Do not backfill fingerprints or infer approval.

## Completion criteria

| Gate | Status and acceptance evidence |
|---|---|
| Standalone contract, Increments 1–3 | Complete for standalone scope. Scoped immutable receipt, deterministic digest, history/cycle validation and independent method evidence tests exist. |
| Test-only prototypes, 4A–4C | Complete for prototype scope. Opt-in in-memory observer, temporary atomic journal and pure shadow fixtures have passed. Production receipt writes remain absent. |
| Production capture and persistence | Pending. Verify pre-dispatch and effective inputs, actual method evidence, atomic publish in SQLite and cloud, replay, revision conflicts and interrupted writes. |
| Shadow-to-live invalidation | Pending. Resolve the four disagreements above, prove coarse fallback for evidence gaps, then approve any change to authority or consumer gates. |
| Scenario and named-version lineage | Pending production adoption. Keep original scope, frozen baseline and stored snapshot bytes. Verify reopen/fork isolation with live receipt metadata and no implicit recalculation. |
| Read and export provenance | Pending. Reconcile labels and eligibility across saved reads and exports with approved authority rules. |
| End-to-end numerical and snapshot parity | Pending. With production integration enabled/disabled, compare exact equipment costs, annual economics, ledger, NPV and existing snapshot bytes. Include partial and retained outcomes, equivalent reruns and frozen scenarios. |
| Engineer 1 acceptance and closure | Pending. Record decisions and fixture results, obtain sign-off and verify the adopted paths before changing B09 from PARTIAL. |

Recommended order after review: pre-commit capture and atomic persistence, production shadow comparison including scenario/version lineage, then read/export projection. Change freshness authority only after parity and explicit approval.

## Review verification

Checked five repository links, six pending decision sections, eight completion gates, and the staged diff. Re-ran the focused receipt, observation, journal and shadow suites on Windows 11 / Python 3.12.14 with isolated SQLite and AI/cloud disabled. Result: **63 passed, 0 failed, 0 skipped, 0 warnings** in 17.08 seconds. The prior 4C affected selection returned 107 passed, one private-snapshot skip and one existing warning. This change adds only review documentation.
