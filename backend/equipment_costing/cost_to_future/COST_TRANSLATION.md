# Automatic price-period translation

Canonical implementation: `cost_translation.py`. Data: `index_catalogue.json`. Operating-price adapter: `operating_prices.py`. Existing explicit equipment-index escalation delegates to the same Decimal numerical ratio primitive.

## Selection and arithmetic

Every price carries its actual currency, period, index series and source index. A methodology name does not imply a year: Garrett, Samuel, Michael or a future provider all use the price metadata supplied by their calculation. No method-name lookup can manufacture a reference year.

1. Already in the target year: leave the amount **and its original within-year period** unchanged. This does not silently align different monthly bases.
2. If the catalogue has a target observation for the actual equipment index series, use that same-series ratio.
3. If authorised, use a registered currency-specific consumer inflation series and look up both dates in **that same series**. CEPCI 320 is never divided into CPI 336.940.
4. Missing source year, missing observation, missing source, currency mismatch or unsupported proxy remains unresolved. There is no nearest-year guessing, interpolation, FX conversion or invented index.

`translated price = source price × target index / source-period index`.

Equipment purchase and installation components are converted once before totals and CAPEX factor calculations. Original costs, price periods, source indices, sources and previous adjustments remain in the audit trail. Percentage factors and physical quantities are not inflated. Aggregation checks include the named index series, not just matching numbers/periods.

## Initial USD data

Pinned on 2 November 2026:

- BLS CPI-U US city average all items, **not seasonally adjusted**, 1982–84=100; series `CUUR0000SA0`.
- 1987 annual average **113.6**: https://www.bls.gov/cpi/tables/historical-cpi-u-201708.pdf (Table 24, PDF page 4).
- 2018 annual average **251.107**: https://www.bls.gov/regions/mid-atlantic/data/consumerpriceindexannualandsemiannual_table.htm .
- September 2026 **336.940**: https://www.bls.gov/news.release/archives/cpi_10142026.htm (Table 1; release 14 October 2026).

The default target is **2026-09**, a monthly observation, not a final 2026 annual average. Using the 1987 annual average for an “early 1987” source is an explicitly disclosed approximation. Consumer inflation is a **purchasing-power proxy**, not chemical equipment inflation, a vendor quote or a market-price forecast.

The Bank of England calculator describes UK pound purchasing power: https://www.bankofengland.co.uk/monetary-policy/inflation/inflation-calculator . It is not used for USD costs. GBP/other currencies require their own registered, sourced observations; no currency conversion is implicit.

## Automatic application and compatibility

The application enables the policy on calculation of new studies and existing coupled operating studies. Historical saved results are not rewritten on load. A user-triggered Python rerun recalculates from the saved source assumptions, preserving repeatability and avoiding cumulative inflation. Original assumptions retain their historical basis; translated operating assumptions and index observations are recorded in calculation evidence. Material prices, utility tariffs, salaries, fixed monetary allowances, explicit selling prices/deductions, commercial payments, avoided costs and closure allowance are rebased before OPEX/revenue/finance. Quantities, headcounts, ramp-up, tax rates, margins and discount rates are unchanged. Researched observations retain their original record and date in the audit.

Uncoupled legacy financial contracts retain historical behaviour until explicitly supplied a translation policy and aligned monetary inputs. Direct `calculate_total_cost()` calls stay historical unless `translation_policy` is supplied, preserving original-price calculations. New models can register additional named index series and dated observations without new translation functions. The catalogue is pinned data, not a live or licensed CEPCI feed. Native CAPEX/working-capital monetary overrides need an explicit price basis; no arbitrary override is relabelled as a current-year cost.

Use an explicit disabled policy (`{"enabled": false}`) to retain a historical study; the existing assumption-edit API accepts the `cost_translation` section. This policy is saved with the assessment. There is no runtime web/LLM call in translation.

## Verification

Automated tests cover independent native/proxy ratio calculations, 1987/2018 bases, future method names, target-year no-op, zero/invalid amounts, missing/ambiguous years, missing sources, missing consent, currency mismatch, installation, aggregation, CAPEX propagation, repeat escalation and operating quantities/percentages. A read-only M&E8 run in an isolated temporary store completed all stages on a 2026 financial basis; repeat runs and save/reload returned identical results. Original saved project untouched. Artifacts: ignored `outputs/cost-translation/`.

After individual adjustments, a common `PRICE_BASIS:<currency>:<period>` aggregation label allows different documented inflation series to contribute to the same dated-currency total. Its index value **1 is an internal numeraire, not a published CEPCI/CPI observation**. Each equipment estimate and translation audit retains its actual source/applied index and multiplier. Untranslated/differently dated or mixed-currency prices are not silently merged.

## Current-price UX

Assessment reads now use `backend/orchestration/current_prices.py` to recalculate a read-only current-price view through the canonical pipeline. Equipment, overview, capital, operating, revenue and financial pages consume the same results. HTML reports and JSON snapshots use that same view. Original saved plans, revisions and evidence are not rewritten. `GET /api/assessments/{id}?historical=true` remains available for the original snapshot. Explicit disabled translation policies are respected; missing engineering reports are disclosed. Recalculation uses a bounded eight-entry in-process cache keyed by the exact report, description and plan; no AI or external request is performed. Native calculation failures remain stage issues rather than fabricated current prices.
