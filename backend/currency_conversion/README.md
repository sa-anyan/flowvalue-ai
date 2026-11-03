# Currency conversion backbone

`currency_converter.py` is the canonical Decimal FX implementation. Use
`convert_currency(amount, source_currency, target_currency)` for a scalar or
`convert_price(record, target_currency, amount_field="unit_price")` for a quote,
manual assumption or research estimate. Prices must supply ISO currency codes;
ambiguous symbols are rejected. Original quotes, units, uncertainty, citations
and price periods are preserved in the conversion audit. FX does not turn an
unverified estimate into a verified price. No third-party dependency was added.

The packaged `rates.json` is a pinned **2 November 2026 ECB** reference snapshot
with EUR as its common base. Cross rates use target-per-EUR / source-per-EUR.
These informational reference rates exclude bank spreads/fees. They are not a
live feed or a future exchange-rate forecast. Supply a sourced snapshot to the
pure converter to use another date; an explicitly requested absent date fails.
Update the catalogue only from a dated official source; never overwrite a saved
conversion audit. Unsupported currencies fail explicitly rather than guessing.

## Calculation and UI

- TEA overview → Reporting currency selector. Preference persists in this browser
  and applies across equipment, CAPEX, OPEX, revenue and finance pages.
- Assessment, HTML report and JSON snapshot accept `?currency=GBP` (or another
  supported ISO code). Existing authentication and assessment access checks apply.
- Python's `assessment.py` converts explicit monetary result fields; it never
  multiplies all numeric values. Physical quantities, fractions, factor values,
  IRR and payback are not currency amounts. The canonical financial Money inputs
  are converted and the existing deterministic financial engine recalculates its
  ledger and investment metrics. Same FX reference is used across every year.
- The original saved plan and source evidence retain their currencies. Editing
  inputs uses that original basis; selecting a reporting currency does not
  silently rewrite quotes, taxes, tariffs, or the saved project baseline.
- Inflation/price-year escalation runs first in the source currency. FX then
  changes the reporting denomination without changing the price year or adding
  another inflation factor. This is a reporting view, not local plant repricing.
- `GET /api/currency/rates` returns the snapshot. `POST /api/currency/convert`
  accepts `amount` as a decimal string, `source_currency`, `target_currency`, and
  optional `rate_date`. Quote/agent adapters can call the same Python functions;
  no external research or AI request occurs during conversion.

## Boundaries

Mixed-currency upstream results require explicit normalization first. Source
currency is not inferred from a location, model name or currency symbol. A
financial result without its canonical inputs is rejected for full-study
conversion. Source evidence/index audits are deliberately left in their original
currency and labeled as such in the UI. Future result schemas must add their
monetary fields to the reporting adapter and reconciliation tests. Browser
preference is not a change to a saved financial baseline or its FX policy.

## Verification

Automated tests cover cross/inverse rates, signed/zero values, unsupported codes,
invalid amounts, absent dates, invalid rates, quote provenance, unchanged physical
quantities/percentages, preserved baselines, canonical ledger recalculation and
currency-invariant IRR/payback. Browser QA switches GBP/EUR/USD through the real
Next.js proxy and compares report/snapshot values with the selected assessment.
