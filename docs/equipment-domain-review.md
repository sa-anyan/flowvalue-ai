# Cost-model domain review

This policy addresses the November 2026 comparison of two runs of the same
workbook with different provisional tank/settler model selections. It does not
hardcode their tags, sizes, prices, chemicals or model IDs.

During an explicit AI Equipment run, the existing bounded pricing review also
examines priced items carrying the canonical `BELOW-RANGE FLOOR` evidence. It
considers only the conceptual candidates already supplied for that item, within
the same library, category, quantity/coordinate role and cost scope. The existing
physical recipe must evaluate successfully for each candidate. Primary and
secondary published domains are checked in native units. Candidates in range
precede below-range candidates. If none covers the physical size, a strictly
closer minimum bound may be reviewed. Unknown contracts and upper-range failures
do not become automatic extrapolations.

Candidate order never uses price. Same units/category are not engineering
approval: the specialist must review service, configuration, material,
pressure/temperature and included/excluded scope. A suitable candidate is checked
again through the canonical cost engine before acceptance. Quantity, physical
source bindings, recipe, inputs and unit context must remain unchanged. The
selected model and reason are saved as `domain_selection`, with input-resolution
records explaining selection or retention of the original minimum-price floor.
All physical size and financial arithmetic remains in the existing engines.

User-selected models, user-edited sizing, explicit prices/quotes and scope
exclusions are protected. A declined, invalid, unavailable or out-of-scope review
retains the existing estimate. There is no universal price multiplier or rule to
select the cheapest alternative. Deterministic recalculation and Monte Carlo
never invoke this review or silently replace frozen configurations. Existing
saved results are not rewritten; a fresh AI run can create different provisional
assumptions, which remain subject to review and recorded ranges.

The input-resolution prompt version is bumped to prevent old cached instructions
from being reused for new reviews. Existing review batching and bounded retry
limits remain in place; this can add a specialist review for a floor-priced item
that previously bypassed pricing repair. No external market research is added.

Tests in `backend/tests/test_equipment_domain_review.py` use real cost models and
mocked specialist responses, without paid/network AI calls. They cover in-domain
and closer-floor alternatives, unchanged physical inputs and quantity, explicit
user choices, quote/scope protection, missing alternatives, unavailable reviewers,
unknown/incompatible contracts, secondary coordinates and upper-range rejection.
Existing tests cover Garrett fallback, conversion bridges, heat-exchanger and
other recipe inputs, proposal handoff and estimate anchoring.
