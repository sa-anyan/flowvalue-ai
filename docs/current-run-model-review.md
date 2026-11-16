# Current-run model review — 16 November 2026

Founder request: new runs must not inherit prior decisions or misleading user
confirmations, while retaining a responsive Save-and-go workflow.

* Upload no longer calls the same-workbook scope-decision carry-over helper. Even
  byte-identical re-uploads start with new model choices, scope reviews and locks.
  The retired helper is a no-op for compatibility. Existing projects and versions
  remain intact; intentionally opening an existing project still opens its inputs.
* Stage execution wraps persistence with `blocks/run_store.py`. AI responses are
  memoized in memory only for that execution; persistent AI cache is neither read
  nor written. A new execution receives fresh responses, even for identical
  inputs. Identical requests within one execution can reuse their response. This
  also applies to background analysts launched from that execution. Deterministic
  catalogue/index caching is unchanged: it contains methods, not project choices.
* Quick matching remains deterministic and immediate. Tag-prefix-only suggestions
  do not select a model. Other Autopilot picks are provisional, not confirmations.
* With AI enabled and the current equipment section unlocked, equipment matching
  runs in the existing batches of at most eight using current process and stream
  descriptions. Having Autopilot/user choices does not assert all are confirmed
  or suppress this review. Current explicit user models/sizing stay active, with
  proposed alternatives recorded for review; locked sections remain protected.
* Library preference ranks OpenPyTEA alternatives for sizing review but never
  silently swaps configurations just because the category matches. The reviewer
  and sizing specialist must consider function, configuration, capacity and scope.
* Sizing, source unit conversion, strict ranges, scoped cost calculations,
  extrapolation evidence and price-date translation stay in canonical Python.
  These changes do not establish independent engineering validity or guarantee
  live AI judgement. They remove bypasses and stale-response reuse.

Verification uses offline providers and real catalogue/registry/persistence paths.
Cases cover gas compression with a misleading P tag, batched review of Autopilot
choices, agitated vs non-agitated reactors, current user-input preservation,
byte-identical re-upload isolation, persistent-cache isolation, within-execution
memoization, and Save returning while a background review is deliberately blocked.
No customer baseline is modified and no paid provider call is required by tests.

The browser check also exposed CAPEX values labelled “Selected by you” without
origin evidence. Presentation now attributes selections, overrides and exclusions
to the user only with an explicit user-origin register entry. Unknown legacy
origins use neutral review labels rather than inventing a human or AI decision.
