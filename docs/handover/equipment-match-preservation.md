# Preserve saved configurations during family-only AI reviews

A new conceptual matching response may recognise a family and return no selected
configuration. Previously `apply_matches` treated that blank as a model change,
archiving the previous coordinate and conversion inputs and clearing the model.

The matcher now retains a saved model plus existing sizing/conversion inputs when
that model remains in the proposed candidate list and the review has not rejected
its suitability. The new proposal is stored as `matching_attempt`, with a
preservation reason. An explicitly selected different model still invalidates the
old coordinate. Rejected or incompatible candidates are not retained by this rule.
This is scenario preservation, not independent engineering validation.

Charlie recovery experiment (local, 5 November 2026): replayed prior FlowValue
assumptions for P-103AB, R-201 and HE-201 against the same workbook fingerprint and
current parsed evidence. No prior price was copied; canonical Python recalculated
all prices. A separate review assessment preserves the user's original baseline.
T-301 and PD-201AB remain unresolved: prior discussion did not establish working
costing configurations for them. The full-code PD matching experiment was reverted
at the founder's request and is not reintroduced.

Local private diagnostics: `outputs/five-equipment-recovery/`. These are excluded
from Git and must not be published with private engineering data.

## Raw-source word assistance experiment, 5 November 2026

Saved source ZIP, working-tree patch and SQLite checkpoint before testing. Tested
in `/tmp` with a separate database first. Raw source name/type/description text is
now passed alongside normalised equipment labels to lexical matching and the
conceptual reviewer. Exact equipment nouns are evidence, not automatic approval.
No tag-specific pricing, fixed costs or forced blower interpretation was added.

The experiment priced the packaging holding tank using G303-144 and provisionally
selected a fluid-bed dryer, G277-060, for PD. The reviewer rejected the proposed
blower interpretation against the available food-solids service. Tank volume and
dryer sizing use explicit AI assumptions, not measured dimensions. The estimates
do not establish the actual dryer technology or a complete packaging-line price.

The isolated experiment reached 29/29, with identical repeated Python outputs.
After promotion, a separate main-pipeline review assessment also reached 29/29 on
two identical Python-only reruns using those saved assumptions. This demonstrates
calculation coverage, not design validation or deterministic fresh AI decisions.
Previous assessments remain intact. Private result files are in ignored
`outputs/tank-pd-lexical-experiment/`.
