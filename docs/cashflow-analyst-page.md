# Cashflow

Local implementation: 8 November 2026.

The standalone route `/cashflow` (legacy `/revenue/cashflow` redirects with query parameters preserved) displays the canonical saved financial ledger,
not a separate finance calculator. The project calendar includes construction;
year 0 remains visible for reconciliation. Entry selects total analysis years
and construction years; Engineering Data can change them later.

New Entry schedules use two construction years and a 20%, 40%, 60%, 80%
operating ramp, holding at 80%. Annual steps are FlowValue planning assumptions,
**not a published Garrett schedule**. Garrett printed p.45 (PDF57) separates
on-stream availability (90–95% preliminary design) from historical industry
utilization near 80%; p.76 (PDF88) discusses gradual market uptake; p.104
(PDF116) discusses prolonged partial-capacity startup and historical utilization.
The 80% plateau is contextual historical guidance, not a present-day universal
limit. These fractions apply to throughput during independently scheduled
operating hours; no additional availability multiplier is introduced. Existing projects
retain their saved calendars. Construction revenue is zero under this calendar.

Each annual drawer edits physical production utilization and independent factors
for existing Revenue Box sources. Product factors scale the sold fraction;
commercial factors scale rate, fixed and minimum payment terms, never create
new income sources or alter workbook quantities. Fixed contract fees do not
implicitly follow the production ramp. Percentages are constrained to 0–100%.

Save-only preserves a version, clears commercial approval unless explicitly
reapproved, and marks affected saved results stale. Save & update economics
requires explicit approval and uses the existing coordinated Python economic
stages, without LLM calls. Missing inputs remain explicit. Extending the horizon
repeats final commercial terms as provisional planning assumptions; this does
not extend a contract. Construction spending defaults to equal annual shares
when construction length changes. Other financial policies remain canonical.

Verification: backend calendar, bounds, source identity, approval fingerprints,
construction rows, canonical ledger mapping, individual product/commercial
factors and horizon extension tests; existing stage/economics regressions;
TypeScript and production build. Local browser test on synthetic assessment
`cefe829747664eb2960a771d9e4b748c`: year 3 water realization 100% → 60%
changed revenue 5,425,920 → 3,255,552 USD and recalculated OPEX/tax/cashflow;
adjacent years retained their revenue. No user project was edited for this test.

Limitations: no selectable alternative methodology library on this page;
construction revenue/commissioning contracts need a future explicit model.
Saved stale amounts remain visible with a recalculation warning. Commercial
assumptions require Revenue Box data; no research prices are invented here.

## Cash break-even marker — 9 November 2026
The chart now annotates the canonical financial engine's project_payback metric
at the cumulative project-cash zero crossing, with a dashed vertical guide,
intersection marker and project-year label. A summary distinguishes first
undiscounted investment recovery, no recovery within the horizon, no cumulative
investment deficit, pending inputs and stale results. Stale or invalid metrics do
not produce a marker. The existing financial engine owns the interpolation;
JavaScript only positions its saved result on the graph. Later losses may reverse
the first recovery; this is not an operating break-even price/volume calculation.
Backend and frontend tests cover fractional recovery, year-zero investment,
no recovery, no investment, invalid values and stale output suppression. Browser
verification on the synthetic batch study displayed year 1.01 from canonical
payback 1.005511836463198...; no project assumptions were changed.

## Capital and operating-cost phasing

The schedule now owns separate project-year maps for `capital_spend_fractions`
(fixed capital) and `startup_spend_fractions` (the existing CAPEX start-up
allowance). Each must sum to 100%; invalid totals are rejected rather than
normalized. Initial-capital payments may overlap production through an explicit
`capital_payment_end_year` in the canonical financial assumptions. This does not
move commissioning or depreciation automatically. Existing studies keep their
saved financial timing until the analyst saves a changed schedule.

For new two-year pre-operation schedules, the editable planning example spends
30%/50%/20% fixed capital over project years 1/2/3, with start-up and working
capital funded at first operation. Other construction durations retain equal
construction shares. The Cashflow calendar offers this example explicitly for
existing studies. It is **not a Garrett-prescribed percentage schedule**.
Garrett, *Chemical Engineering Economics*, printed p.87 (PDF p.99), describes
one-to-three-year construction and a typically S-shaped cumulative spending
curve; p.41 (PDF p.53) separates start-up expenditure and working capital;
pp.44–45 (PDF pp.56–57) distinguishes fixed costs, operating hours and utilization.
The model does not force a particular graph shape or guarantee profitability.

Variable physical consumption is annualized with the production ramp upstream,
exactly once. Fixed cash OPEX defaults to the full applicable annual estimate
from first operation; it is not automatically multiplied by capacity utilization.
An explicit `fixed_opex_factors` project-year map can reduce fixed-cost
mobilization with a recorded rationale. This is an annual cash-timing adjustment
after cost-factor estimation, not a change to the underlying factor bases; each
adjusted line retains its unphased amount and multiplier in its rationale.
Non-cash depreciation, financing and variable costs are unchanged. Both the stage
runner and coupled-study path apply this same adjustment and hand the resulting
annual OPEX lines to the canonical financial ledger.

The year drawer exposes capital/start-up shares, production utilization and
fixed-cost mobilization. Working-capital timing is in Calendar & interpretation.
Pre-operation commissioning costs use the separate start-up allowance; recurring
operating OPEX is not fabricated during construction. More detailed pre-start
staffing must be scoped explicitly, excluding amounts already in that allowance.
Capital/start-up shares outside a shortened horizon must be explicitly moved;
they are never silently dropped. Annual rates, quantities and tariffs remain
editable on their owning pages. No LLM is called for schedule recalculation.

## Financial-model dashboard presentation

The Financial Model route now presents one visual workspace over the saved
canonical financial result: NPV, IRR, discounted payback and profitability index;
cumulative project cash; revenue/EBITDA/net income; selected-year cash allocation;
accounting earnings; and annual versus discounted project cashflow. A shared year
selector and chart inspection control the selected-year panels. Missing results
remain pending and stale outputs retain their recalculation warning. Profit bars
are labelled non-additive; project cash and accounting income tax stay distinct.

Financial inputs, full investment metrics, annual cash/P&L ledgers, source basis
and checks are in keyboard-accessible drawers. The inputs drawer uses the existing
versioned assumption-save pathway, retains the other operating-study assumptions,
and links to Engineering Data for recalculation. Annual phasing remains owned by
Cashflow. The dashboard does not calculate finance, invoke AI or mutate inputs
when exploring charts. Existing report/snapshot exports remain available.
