# Reversible duplicate equipment review

Founder rule: repeated normalized tags represent one register entry; if both
`FT-201` and `FT-201AB` exist, keep `FT-201AB` and exclude `FT-201` from pricing.
The existing AB quantity policy prices the retained pair as two identical units.
This is an explicit product convention, not independent verification of the
physical plant or duty/standby arrangement. Similar equipment names alone do
not establish duplicates. Different A and B suffixes are not collapsed.

`duplicates.reconcile()` creates a scenario view before canonical equipment
sizing/pricing. It preserves the original report, excludes redundant entities,
retains observations and stream references on the survivor, and marks redirected
references as user-convention interpretations with their original equipment key.
The plan retains dropped records and their pricing assumptions for restoration.
The Equipment result contains `duplicate_review` with tag, retained tag, reason,
source, original stream keys and dropped/restored status.

The Equipment page's “Review drops & removals” control displays this audit and
uses the existing revisioned equipment edit endpoint to set
`duplicate_action: restore` or `auto`. It reruns only Equipment, without AI.
Restored entries remain separate on later runs, so adding one back may increase
costs. Existing manual prices/quantities remain editable and preserved. Other
stages become stale under existing stage dependency rules and need recalculation.

Tests cover normalized repeated tags, AB preference, source immutability,
retained references, duplicate AB records, unrelated/A/B tags, restoration,
re-exclusion and override preservation. Charlie's local rerun excluded T-101,
FT-201 and PD-201, reducing 32 records to 29. Original study snapshots are kept.
Private audit outputs remain under ignored `outputs/charlie-duplicate-review/`.
