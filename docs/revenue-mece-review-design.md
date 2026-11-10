# Revenue MECE review — implementation note

User Revenue Box → existing LLM category/stream interpretation → review all income
methods together → explicit user approval → canonical Python revenue ledger.
Products and co-products share stream/custom rate × operating time × price, with
allocation, quality, sold fractions and annual ramp applied once. Other methods
reuse the six-category payment/form catalogue: capacity reservation, usage,
processing, environmental attributes and fixed/variable contractual payments.
Their contract counts and billing periods are not physical production rates.

Keep main/co-product role, selected stream and observed rate, price period,
selected price, low/high evidence range, rationale and dated references editable
and versioned. A range means comparable observations, not a verified market-wide
interval. Missing prices trigger an explicit opt-in research action; research
selects only returned, compatible cited candidates and never fabricates a price.
Research proposals do not overwrite an approved baseline. Numerical price bounds,
quantities, unit conversions and revenue remain Python-owned. Unknown quantities,
insufficient evidence and incompatible units stay visible. Saved annual contracts
retain their existing advanced editor rather than being flattened silently.

## Implemented review controls (10 November 2026)

The Revenue assistant opens one centred review popup containing all income cards.
A saved unapproved Entry AI interpretation opens this review automatically on the
Revenue page. The Revenue Box/reinterpretation controls are collapsible so the
identified methods come first. Each card has a MECE selector; product/co-product
roles share the same canonical rate-based product engine. Other methods reuse
`backend/revenue/method_forms.py` and the existing commercial payment engines.
Year-varying/minimum-payment legacy contracts retain their detailed annual editor
rather than being flattened by the simple form. The shared editable operating
horizon is passed through the canonical Cashflow schedule adapter.

`price_review` stores selected price, lower/upper bounds, rationale, source
references and period/unit/currency basis in saved plan JSON. User-entered bounds
are labelled scenario assumptions. An explicit per-line or all-missing-prices
research action authorizes external search and AI usage. Existing sourced
research is reused; an additional bounded LLM selection chooses one compatible
returned observation and explains its applicability. Python derives bounds from
comparable observations in one currency/unit/price period. Unknown dates,
incompatible observations and unsupported selections remain unresolved. No price
or range is generated when supporting observations are absent. A proposed price
is not applied until the user accepts it into the draft and saves/calculates.
The prior version remains recoverable. No supplier contact is performed.

Backend verification covers all six MECE categories, main/co-product shared
calculation, calendar edits, source-bound price recommendations, invalid ranges,
missing evidence, explicit research consent/refusal and unchanged plans during
research. Browser verification on a separate synthetic assessment exercised
product sales + processing fees + fixed annual licence income (USD 130,576/year),
then a co-product stream/range edit with deterministic recalculation and JSON
persistence. Test amounts are not market estimates or user-project valuations.
No live external price research was used in development verification.
This scoped delivery does not claim the wider R39 buyer, scenario, export or
process-visualization acceptance gates are complete.

## Simple input presentation

The default review now uses plain-language payment choices, larger controls and
only the essential name/stream/price fields. Time settings, product role,
calculation details, evidence and price ranges remain available on demand.
Existing contracts show a compact payment summary and expand for editing. Notes
are optional in the simple contract form; the canonical input retains a labelled
user-entry basis when no note is supplied. Availability and escalation appear as
percentages and are converted back to canonical fractions at the UI boundary.
Eight frontend tests, production build and desktop browser checks passed for
this presentation change; no backend revenue calculation was changed.
