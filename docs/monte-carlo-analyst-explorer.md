# Analyst Monte Carlo explorer

This extends the existing canonical Monte Carlo pipeline; it does not introduce
new engineering equations, cost correlations, probability calibration, or a
second financial ledger. Frontend components and API records are separate so
Seyram can integrate the functionality into his UX.

New requests run exactly **200 variations**, with a reproducible seed. Historical
studies keep their recorded counts and outputs. Cancellation can finish early
and retains its cancelled status. The statistical outputs are conditional on
reviewed ranges/distributions and dependencies, not certified confidence bounds.

## Analyst controls

The condensed parameter matrix groups inputs from Equipment through CAPEX,
OPEX, Revenue, operating schedule, and Financial. It displays baseline values,
units, bounds, distributions, evidence, and rationale. Configuration choices
show real saved/candidate catalogue model IDs and descriptions, including
OpenPyTEA, Garrett, Nottingham, and additional implemented models. A single
choice fixes a configuration; multiple choices have explicit weights. Existing
unit, target, scope, and applicability validation still applies. Incompatible
configurations remain visible as invalid/partial calculations; selection does
not assert mechanical equivalence. No AI or external research runs per draw.

## Traceability

Each new draw stores a fingerprint of its applied plan. The study stores the
frozen baseline plan, effective fixed plan, original source report, process
brief, settings, sampling seed, and source version audit. Inspection reconstructs
inputs from that frozen copy and the saved samples, checks the fingerprint,
and returns the complete configuration without recalculation or baseline edits.
All registered selected inputs show baseline versus applied values. The full
record includes fixed equipment, CAPEX, OPEX, Revenue, schedule, financial,
price/index, and source context. Earlier saved results without a draw fingerprint
are identified as historical, rather than falsely reported as verified.

Sensitivity buttons expose the actual low/high or categorical group members.
The inspector shows an actual draw, never a fictional configuration claimed to
produce a group median. Histogram bins filter eligible runs using the same
metric-scope rules as summaries. The searchable/sortable variation table retains
failed and partial runs and supports inspecting every variation.

JSON exports retain the full reproducible study. Individual variations can be
downloaded with their full configuration. Excel includes chunked Configurations
records in addition to existing results, exact values, scope and audit sheets.

## Verification

Focused synthetic tests cover the 200-count contract; exact canonical replay;
fixed-input/baseline isolation; fingerprint tamper rejection; group membership;
metric eligibility and bin edges; ownership/parent checks; and configuration
exports. Browser acceptance exercises selection, a 200-draw study, sensitivity
inspection, histogram filtering, and fixed configuration records. No baseline
assumptions are silently changed during this workflow.

## Compact interaction layout

The results workspace separates Overview, Sensitivities, Variations, and Audit
views. Overview shows one selected financial/equipment distribution and the
cash-flow outlook. Hover and keyboard-focus summaries explain chart bins and
sensitivity rows. Clicking opens a right-side native-dialog drawer, with the
selected group/variation and complete frozen configuration. Closing or pressing
Escape restores focus without moving the analysis page. Run tables scroll
within their panel rather than extending the entire page.

Setup categories start collapsed. Input names open a range/configuration editor
in the same drawer component; advanced input coverage, dependencies, and scope
checks remain optional disclosures. No scenario or baseline calculations are
changed by these layout controls.

### Per-variation calculation breakdown

The variation drawer now has Equipment, CAPEX, OPEX and Revenue sections. These
show canonical equipment unit estimates and quantity-extended costs; CAPEX
factor fractions, named bases, formulas and successive capital subtotals; OPEX
annual quantities, rates and percentage bases with cash/noncash classification;
and revenue quantities sold, net prices and commercial payments. Source and
rationale disclosures sit beside each cost line. Tables scroll within the drawer.
The CAPEX category coverage view distinguishes counted, combined and embedded
costs, so category disclosures are not mistaken for additional charges.

New simulations save a compact `calculation_trace` alongside each draw. For
historical studies with frozen source inputs, individual inspection can replay
the canonical pipeline without saving anything. It displays replayed calculation
rows only if metrics, cash flow, equipment records, CAPEX lines and OPEX lines
match the original draw exactly. Failed/missing-source or mismatching replays
retain saved inputs and totals with an explanation; new amounts never replace
historical results. The JSON variation download includes these same rows and
their saved/replayed verification status. No external research is performed.
