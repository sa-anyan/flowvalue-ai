# Deterministic matching assessment and integration — 16 November 2026

## Evidence examined

The earlier matcher introduced in `bb60b41` (PR #51, followed by the quick-match
workflow in PR #52) is byte-for-byte identical to the deterministic matcher in
this checkout. It has already been integrated as the Autopilot first pass.
No second copy or replacement costing engine is needed.

An offline comparison used Charlie assessment
`251e8b572d354533bb013edd18f74135` and the same locally loaded catalogue.
The complete effective register contained 31 equipment records, before physical
identity/alias reconciliation. Both copies returned 4 `auto`, 25 `choose` and 2
`prefix_only` outcomes. Repeating the current matcher returned identical output.
One local measurement was approximately 0.34 seconds with catalogue preparation,
and 0.03 seconds warm. These are local measurements, not production latency
promises. The saved AI conceptual-matching phase made four sequential requests
and took approximately 78 seconds. This is a speed comparison, not an independent
accuracy evaluation or a guarantee that all 31 records represent distinct assets.

No general accuracy superiority is established. An `auto` ion-exchanger match can
still require unsupported removal/construction assumptions. A tag-only pump
suggestion cannot establish equipment function. Family identification, specific
configuration, size domain and cost scope are separate decisions. Neither the
lowest price nor number of priced items is an accuracy criterion.

## Integration

- Publish this run's instant proposals after initial Python extraction, before
  long AI workbook review. Keep their provisional identity and price status.
- Supply the deterministic, stable candidate order to AI conceptual review,
  without using prior projects/user choices, numeric confidence or price ranking.
  AI may depart from it using this run's evidence. It is not an approved shortlist
  of mechanically interchangeable equipment.
- Continue canonical validation of scope, coordinates, physical sizing and source
  model domains. Keep the domain-review safeguards and user-override protection.
- Execute independent conceptual-matching and sizing request batches using a
  bounded three-worker prefetch, then validate/apply results in source order.
  Workbook region reviews remain ordered because later regions read the updated
  identity register. Calculated numbers still come only from canonical Python.
- Stop retrying explicit, valid `unresolved` decisions without new evidence.
  Malformed or invalid proposals retain the existing bounded correction paths.
- Expose completed background research separately from pending application, and
  apply completed proposals at safe boundaries while the launch owns its lock.
  Fingerprint checks reject stale drafts; user values/locks and canonical stage
  receipts stay authoritative. Duplicate boundary/worker saves are idempotent.

## Verification and limits

Offline tests exercise actual concurrent overlap, bounded worker count, source
order, propagated run context and isolated request failure. Existing matching,
conversion, fallback, domain, launch and analyst tests are rerun. A locked-stage
handoff test confirms that a completed proposal is visible as research-finished,
can be applied at the owner's safe boundary, and is not saved twice.

The live Charlie run was allowed to finish without restart. Its saved equipment
phase took 707.884 seconds and produced 21 priced records out of 28, with a known
priced equipment subtotal of USD 4,753,666.533900196 at 2026-09. Its completed
results have not been repriced or replaced during this assessment. No fresh paid
AI comparison was launched. Fresh AI-generated assumptions may still differ;
reproducibility of a saved plan and Monte Carlo draw remains a separate guarantee.
Pending records remain in the worker's memory until a safe save; this change does
not introduce a crash-durable distributed job queue or a distributed stage lock.

## Follow-up: unpriced equipment reference and floor handling

The next Charlie run (`1177fae8325c4b5d85b33448cf27f2f0`) exposed two
independent failures. The conceptual reviewer returned identity references of
`equipment-evidence:equipment:<id>` instead of the supplied
`equipment-evidence:<id>`. The matcher now repairs only that exact redundant
namespace when it resolves to this same item's actual supplied identity, and
records the correction. Unknown, foreign and otherwise malformed IDs still
withhold selection; the original explanation and invalid references are retained.
There is no fuzzy matching or global evidence lookup.

P-102AB's later sizing response first used an unavailable measurement ID, then
corrected it but declined solely because its flow was below a model minimum.
The input contract now explicitly distinguishes physical size from pricing size:
a compatible proposed model retains the real measurement/recipe, and canonical
Python applies and discloses its existing minimum-price floor. A refusal referring
to the lower bound can receive one policy clarification within the existing
three-attempt cap; it never creates a model, measurement or physical assumption.
Other genuine unresolved responses remain terminal. Upper limits, service/scope
checks, secondary coordinates and user input protection are unchanged.

Offline replay of this run's corrected source binding and saved density assumption
produced a physical flow of 0.02844534511040308 L/s, priced at the published
0.2 L/s minimum: USD 16,112.76341853645 for the run's saved quantity of two,
using its saved target-price basis. This is a regression preview, not a new vendor
quote or an independently established pump design; the live study was not altered.
PD-201AB still lacks a supported equipment function and is not assigned an
arbitrary pump, press or pellet-mill model.
