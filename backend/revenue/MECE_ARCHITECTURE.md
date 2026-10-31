# Canonical multi-mechanism revenue

Implemented 31 October 2026. Garrett Chapter 5 remains the existing product-sales and market-research policy. The six commercial categories are FlowValue's accounting/routing architecture, not a claim that Garrett publishes specific tariffs for them. No textbook tables, workbook formulas or new third-party code were incorporated.

## Routing and calculation

`engine.calculate_revenue(RevenueProject)` is the single aggregation boundary. Existing `Product` records retain the established production, allocation, saleability, sales, net-price/deduction and market calculations. Additional `CommercialLine` records route through the six independent `categories/*.py` calculators registered by `registry.get_category()`.

A payment is assigned once using a unique payment_id; IDs cannot duplicate an existing product payment. Several payments can use one category and several categories can coexist. Sharing a physical stream is allowed for genuinely different payments (for example a treatment fee and recovered-product sale); the analyst must confirm that these are distinct arrangements. Identity validation cannot prove two differently named contracts are economically distinct.

Each line has explicit annual `PaymentYear` assumptions, currency-bearing rate units, billing quantity units, provenance, rationale, evidence date, uncertainty and arrangement status. All arithmetic uses Decimal with the canonical precision. Unknown applicable numbers remain None and produce unresolved issues, not zero income. Conditional LLM estimates are labelled and do not establish an agreement, market price or eligibility.

- Product sales: actual sold quantity × net price; gross-price deductions remain in the established Product path. Generic product-sale lines use an already-net price and cannot add contract floors/fixed payments.
- Processing services / infrastructure: billable usage × tariff, plus explicitly distinct fixed scope where applicable.
- Capacity: contracted quantity × annual/monthly reservation rate × qualifying availability. Monthly rates require 12 billing periods. Contracted capacity must be a commercial/design input, not annual throughput mislabelled as capacity.
- Environmental attributes: eligible credits sold × realised price; an explicit ownership/eligibility assumption is required. This is not automatic regulatory verification.
- Other income: fixed annual/milestone payments or explicit variable contract terms.

For non-product contracts the general annual formula is:
`max(minimum_payment, fixed_payment + max(quantity, minimum_quantity) × rate × billing_periods × availability) × (1 + escalation) ** (operating_year - 1)`.
Fixed and variable components require explicit distinct-scope confirmation. Minimum payments are floors, not extra income. Annual schedules already contain the desired quantity and rate for that year; set escalation to zero if rates were already escalated. No implicit inflation or production ramp is applied to an explicit contract schedule. Flow-linked quantities are independently computed from canonical source observations and the common operating schedule.

Inapplicable contract clauses may be explicitly set to neutral values as disclosed scenario assumptions. Missing actual tariffs/quantities are never replaced by a neutral number. Fixed-only income uses quantity/rate=0 and a currency/year fixed payment, not an invented physical product quantity.

## Integration

The existing coupled operating advisor uses `llm/commercial_interpreter.py`'s structured schema and instructions. It keeps physical product sales in `sales`, other payments in `commercial_lines`, and cost reductions in `avoided_costs`. The process-description connector verifies quoted user arrangements; source-backed quantities use `mass_energy_balance.py` and the canonical converter. No LLM-generated code or formulas execute.

The coupled operating engine aggregates product and other income before revenue-dependent OPEX factors and the existing one-product cost-plus solve. Other income offsets the cost-plus recovery target. Avoided costs reduce one identified, existing, non-percentage OPEX input before its downstream labour/other percentage dependencies are recalculated. Repeated targets, already-applied savings and savings exceeding the original expense are rejected. Unpriced savings or missing counterfactuals are unresolved; an M&E balance alone is not proof of a saving.

Financial Modelling consumes the same annual schedule. Its existing income row has a backwards-compatible `revenue_category` discriminator so contractual cash income with zero physical quantity is valid while product revenue without sales remains invalid. OPEX savings must have matching application provenance before finance handoff. No second sales ramp, quantity estimate or LLM arithmetic occurs in finance.

The local Revenue page exposes annual payment inputs, categories and billing terms, add/remove, product reclassification, and the existing full structured editor for every field (including savings and legacy product details). Reclassification copies the last calculated product annual schedule into an explicit user-assumption payment; it does not recalculate tariffs or infer a new contract. Users must inspect quantities/terms. Save invalidates results; Run Python again uses no LLM calls. Existing named versions/reopen/comparison and section locks preserve overrides and baseline history.

Explicit market research now accepts commercial payments as well as products. It uses the existing consent-gated, bounded web research endpoint and creates source-linked drafts only. No research was automatically run during this build. No buyer contact, guaranteed sales or contract probabilities are inferred.

## Compatibility and limits

Existing product-only projects and older revenue snapshots remain readable. New snapshots carry commercial lines and avoided costs. Old saved assessments are not silently migrated from water sales to treatment services: those are different commercial strategies, requiring a user decision.

Billing units must match exactly in direct canonical inputs; stream adapters use the established converter. No automatic currency conversion, tariff research, legal eligibility certification, seasonal/monthly proration, stochastic contract-winning probability, or automatic interpretation of arbitrary contract wording is claimed. Annual/monthly billing supports explicit whole-year schedules; partial periods require explicit adjusted assumptions. Avoided-cost semantic overlap and differently named duplicate payments still need analyst review.

This package is implemented and integration-tested, not independently industry-certified. See `outputs/revenue-mece/REPORT.md` for this build's measured checks and private local artifacts.
