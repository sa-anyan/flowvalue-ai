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
