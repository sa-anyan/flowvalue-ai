# B09 · Engineer 1 decision and acceptance review

**B09 status: PARTIAL.** Baseline reviewed: `1bce1d1` on `engineer-2/b09-versioning`, [Draft PR #10](https://github.com/sa-anyan/flowvalue-ai/pull/10), stacked on PR #9. [Engineer 1 accepted the six policies below](https://github.com/sa-anyan/flowvalue-ai/pull/10#issuecomment-6808571447). Production integration is parked under the newer instruction. Legacy freshness remains authoritative.

The [standalone contract](B09-calculation-receipts-and-invalidation.md) covers scoped immutable receipts, digest and lineage validation, and separate numerical freshness, provenance and approval states. [4A](../backend/blocks/execution_observation.py) is an opt-in in-memory observation after the normal write, with no production caller enabling it. [4B](../backend/tests/test_receipt_journal.py) demonstrates atomicity in a temporary SQLite fixture. [4C](../backend/tests/test_shadow_freshness.py) compares frozen fixtures without changing results or manufacturing receipts. See the [integration plan](B09-production-integration-plan.md) for commands and the full disagreement matrix.

## Decision register

The numbers match the interfaces and review gates in the integration plan. Accepted policy describes future behavior. The standalone contract and 4A–4C prototypes establish only the evidence described here.

### 1. Equivalent numerical output and changed method provenance

**Agreed policy**

- **Digests:** each stage gets a "handoff" digest of the canonical payload that downstream stages actually use. Financial also gets a separate digest of the displayed ledger. Downstream freshness uses only the handoff digest.
- **Evidence:** 4A Financial exposed prepared-input, result and ledger digests separately. In 4C, an equal-digest upstream rerun with a different executed method left both numerical checks current, with B09 provenance changed.
- **Acceptance fixture:** Rerun with equal payload and a changed method version/fingerprint, then with a changed payload. Verify unchanged numerical state plus a review flag in the first case, transitive stale in the second, and no implicit approval in either.

### 2. Failed or blocked attempt retaining an earlier output

**Agreed policy**

- Keep the earlier output and show the latest failure separately. The existing rule for downstream use stays as it is.
- **Evidence:** 4A store writes matched across both failed and blocked outcomes. 4B retained the prior payload. In 4C, legacy was not fresh while B09 found the retained output current with independently matching evidence.
- **Acceptance fixture:** After a complete run, inject both failure types with matching evidence, a changed input, and missing current-method evidence. Keep stored values identical. Assert current/stale/unknown respectively and enforce the approved consumer gate.

### 3. Complete-to-partial replacement

**Agreed policy**

- **Financial:** needs complete CAPEX and OPEX, which matches what Financial already does. Partial Revenue is allowed only if the result is labelled partial and the missing lines are listed.
- **Evidence:** 4A captured completeness without changing results. 4B retrieved the previous complete payload after a partial attempt. In 4C, legacy was fresh and B09's dependent state was unknown after an equal-digest partial replacement.
- **Acceptance fixture:** Replace a complete prerequisite with an equal-digest partial. Preserve both results, show partial status, and verify the agreed coverage gate for CAPEX, OPEX and Finance without presenting missing amounts as zero.

### 4. Consumed inputs, method capture and newly available optional OPEX bases

**Agreed policy**

- Newly available Revenue or CAPEX **must** invalidate OPEX. In `backend/blocks/opex/runner.py`, OPEX's result changes as soon as Revenue is present: a currency/price-period mismatch raises `DataRequired`, avoided costs are applied whenever Revenue has any, and annual sales revenue is passed into `_opex` for every year. Include which optional inputs were supplied, and their digests, in OPEX's B09 input identity.
- **Evidence:** 4A observed optional Revenue supplied to OPEX without claiming consumption. In 4C, newly available Revenue made legacy OPEX not fresh while B09 stayed current on the supplied digest. A changed basis with a captured edge made both stale.
- **Acceptance fixture:** Cover absent-to-available unused Revenue/CAPEX, consumed basis change, shared observation edits, and missing bindings. Verify stage totals, actual factor/source references and the approved freshness transition.

### 5. Append conflicts, retention and fork lineage

**Agreed policy**

- No automatic re-execution. Only an exact byte-for-byte resend may be retried. A conflicted attempt stays in history with outcome `conflict` and doesn't produce an output.
- **Evidence:** 4A observation runs after the result write and cannot guarantee atomicity. 4B verified duplicate replay, conflict, SQL rollback, abrupt exit and byte-identical named-version history. 4C kept the frozen scenario reference, bytes and saved total intact after a baseline edit.
- **Acceptance fixture:** Race two completions, interrupt a write, retry an exact delivery, then reopen a named version and a frozen scenario after baseline edits. Verify one winning commit, preserved historical results and no inherited active receipt in a new scope. Repeat the storage contract against an approved isolated cloud transaction path.

### 6. Read/export labels and approval boundaries

**Agreed policy**

- **Labels:** Current · Stale (inputs changed) · Unknown (no calculation record, for legacy results) · Partial (N lines missing) · Latest attempt failed (showing last successful result).
- **Evidence:** 4A did not infer missing evidence. 4B preserved saved values and scope. In 4C, legacy output without an immutable receipt could be fresh under legacy checks and unknown under B09 without an invented fingerprint.
- **Acceptance fixture:** Reopen current, stale, partial, failed-retained and legacy cases. Compare JSON/HTML/CSV/XLSX against stored values and recorded methods. Verify labels, no read-time writes or execution, and approved eligibility and reapproval triggers.

## Completion criteria

| Gate | Status and acceptance evidence |
|---|---|
| Standalone contract, Increments 1–3 | Complete for standalone scope. Scoped immutable receipt, deterministic digest, history/cycle validation and independent method evidence tests exist. |
| Test-only prototypes, 4A–4C | Complete for prototype scope. Opt-in in-memory observer, temporary atomic journal and pure shadow fixtures have passed. Production receipt writes remain absent. |
| Production capture and persistence | Parked. Verify pre-dispatch and effective inputs, actual method evidence, atomic publish in SQLite and cloud, replay, revision conflicts and interrupted writes. |
| Shadow-to-live invalidation | Parked. Verify the accepted policy against all four fixture disagreements, prove coarse fallback for evidence gaps and obtain explicit approval before changing authority or consumer gates. |
| Scenario and named-version lineage | Parked for production adoption. Keep original scope, frozen baseline and stored snapshot bytes. Verify reopen/fork isolation with live receipt metadata and no implicit recalculation. |
| Read and export provenance | Parked. Reconcile labels and eligibility across saved reads and exports with approved authority rules. |
| End-to-end numerical and snapshot parity | Parked. With production integration enabled/disabled, compare exact equipment costs, annual economics, ledger, NPV and existing snapshot bytes. Include partial and retained outcomes, equivalent reruns and frozen scenarios. |
| Engineer 1 acceptance and closure | Policy agreed. Production fixture results and Engineer 1 activation and closure sign-off remain outstanding. |

If production work is formally resumed, the accepted sequence is pre-commit capture and atomic persistence, production shadow comparison including scenario/version lineage, then read/export projection. Change freshness authority only after parity and explicit approval.

## Review verification

The original review checked five repository links, six decision proposals, eight completion gates and the staged diff. Re-ran the focused receipt, observation, journal and shadow suites on Windows 11 / Python 3.12.14 with isolated SQLite and AI/cloud disabled. Result: **63 passed, 0 failed, 0 skipped, 0 warnings** in 17.08 seconds. The prior 4C affected selection returned 107 passed, one private-snapshot skip and one existing warning. This change adds only review documentation.
