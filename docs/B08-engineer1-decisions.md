# B08 · Engineer 1 decisions on monetary basis and timeline contracts

**Date:** 11 November 2026 · **Decided by:** Engineer 1 · **Responds to:** `docs/B08-monetary-timeline-contracts.md` on `engineer-2/development` (commit `9b91b69`)

These decisions approve the shared numerical rules Engineer 2 needs before integrating the B08 contracts into CAPEX, OPEX, Revenue, Finance and Monte Carlo. Each decision lists the rule, the reason, and the acceptance fixtures that must pass. Where a decision changes existing behaviour, the affected code is named. Nothing here changes production calculations until the integration work lands with its tests.

## Summary

| Area | Decision |
|---|---|
| A. Precision | Exact decimals end to end; no per-line rounding; round only for display and export, half-up, to the currency minor unit |
| B. Currency and escalation | Escalate in the native currency with a native-currency index, then convert with one dated FX snapshot |
| C. Capital scope | Three scopes; plant factors apply to purchased equipment only; scopes are never summed before factors |
| D. Missing and approval | Availability and approval are separate; missing never becomes zero; AI values are present but provisional |
| E. Quantity extension | Extend exactly once, in equipment costing; downstream receives extended totals only |
| F. Timeline | Project year 0 is the basis year; operating year 1 is project year C+1; phases in a fixed order |
| G. Commercial coverage | No silent contract extension; uncovered years are gaps until an approved renewal exists |
| H. Legacy | No backfill on reopen; saved snapshots stay byte-identical |

## A. Precision and rounding

**Decision**

1. Monetary arithmetic uses `Decimal` with a 40-digit context, matching OPEX, currency conversion and Finance.
2. Existing float values cross into the decimal contracts as `Decimal(str(value))`, the shortest round-trip representation. `Decimal.from_float` is not used, because it carries binary representation noise into the ledger.
3. Intermediate lines and subtotals are never rounded. Rounding happens only at display and export, to the currency's minor unit, with `ROUND_HALF_UP` (the mode `backend/ingestion/balance/display.py` already uses).
4. Displayed totals are rounded from the unrounded total. Reports state that displayed lines may not add up exactly to the displayed total.
5. The cashflow editor's default construction spend fractions (`backend/blocks/cashflow/schedule.py`, `[1 / max(1, build)] * ...`) are floats. Replace them with exact decimal fractions whose sum is exactly 1.

**Why:** rounding each line changes accumulated cash and NPV, and the error grows with the number of lines and years.

**Acceptance fixtures**

- Three lines of 0.005 USD: each displays as 0.01, the stored total is exactly 0.015, and the displayed total is 0.02.
- A float `0.1 + 0.2` crosses the boundary as `Decimal("0.30000000000000004")`, not as a 55-digit binary expansion.
- Three-year construction fractions sum to exactly `Decimal(1)`.
- NPV from unrounded lines equals an independent calculation to full precision; rounding only the final figure changes it by less than half a minor unit.

## B. Currency and escalation order

**Decision**

1. Escalate first, in the native currency, with an index for that currency (for example CEPCI for USD costs). Then convert with an FX rate.
2. Never convert first and then escalate with the target currency's index. Never escalate with an index of a different currency. `cost_translation.py` already refuses a mismatched index currency; keep that refusal.
3. Each study uses one FX snapshot with a stated date and source, recorded on every converted line (`translation_ref`). The default rate date is the study's price-basis date.
4. If no native index exists for the source year, the line stays unresolved. A general-inflation proxy is used only with the explicit policy consent the translation code already requires.
5. A period that doesn't identify one year (for example "2024 Q2" without a policy, or "2019–2021") stays unresolved rather than being mapped to a guessed year.

**Why:** escalation measures price change within one economy; FX measures the exchange between economies at one date. Mixing the order applies one country's inflation to another's prices.

**Acceptance fixtures**

- A 2015 GBP cost escalated to 2026 with a GBP index, then converted to USD at the snapshot rate, reproduces an independent calculation.
- The same cost with only a USD index available is rejected as unresolved.
- Two lines in different currencies and price years both end on the same comparison basis, each with its own `translation_ref`.
- A line whose period cannot be resolved to one year stays unresolved and is listed in the coverage report.

## C. Capital cost scope

**Decision**

1. Use three scopes:
   - `purchased_equipment`: equipment purchase price only.
   - `installed_equipment`: equipment plus installation, as defined by its source.
   - `unit_capital`: a source-defined complete package price (for example $/kW for an electrolyser), including whatever that source says it includes.
2. Lang and factorial plant factors apply **only to `purchased_equipment`**.
3. `installed_equipment` lines receive only the factors their source does not already include, typically indirects, contingency and owner's costs. Each source's inclusions are recorded in an inclusion matrix.
4. `unit_capital` lines receive no installation-type factors. They receive owner's costs and contingency only where their source excludes them.
5. Scopes are never added together before factors are applied. CAPEX reports a subtotal per scope and one bridge to total capital.

**Why:** applying purchase factors to installed or package prices counts installation twice, which the roadmap's G3 gate forbids.

**Acceptance fixtures**

- Purchased 100 + installed 300 + unit capital 1,000 with a Lang factor of 4.7 and a 10% contingency: the result equals 100 × 4.7 + 300 × (1 + indirects not in its source) + 1,000, plus contingency on the eligible bases only. Installation is counted exactly once.
- A line with no recorded scope is rejected rather than defaulting to `purchased_equipment`.

## D. Missing, zero and provisional values

**Decision**

1. Keep availability (`status`: present, missing, unresolved, excluded, not_applicable) separate from approval (`authority`: provisional, approved, unknown), as Engineer 2 proposed.
2. Missing and unresolved values never become zero. A total over incomplete lines is reported as partial, with the missing record keys listed; the complete total stays null, as the current equipment totals already do.
3. An explicit zero is a present value with a rationale (for example a closure cost of 0 because the site is leased). Excluded working capital is reported as excluded with its reason, not as zero.
4. AI-proposed values are `present` with `provisional` authority. They price the item and may appear in previews and scenarios, labelled provisional. They cannot enter an approved baseline total until a user approves them. This implements the founder rule "nothing unpriced" alongside roadmap milestone M3.7 (assumption-based pricing tier).
5. `approved` authority applies only to present, excluded or not_applicable values. An approved missing value is rejected.

**Acceptance fixtures**

- Explicit zero closure cost: total is complete, line shows 0 with rationale.
- Positive closure cost: included once in the final period.
- Missing closure cost: total is partial and names the missing line.
- Excluded working capital: reported as excluded, not 0, and financial metrics are labelled accordingly.
- Provisional AI line: priced in the preview, absent from the approved baseline total, and listed as awaiting approval.

## E. Quantity extension

**Decision**

1. Quantity is applied exactly once, in equipment costing (`calculate_total_cost`), where AB pairs are already counted as two units.
2. Every consumer downstream (CAPEX, OPEX, Finance, scenarios, exports) receives `extended_total` lines only. A `unit_price` line reaching CAPEX is an error.
3. A unit price's denominator must match its quantity unit exactly, or be converted through the registered unit converter with its conversion recorded. No implicit mappings.
4. A user-entered quantity of 0 means the item is excluded, with a reason. It does not create a silent zero-cost line.

**Acceptance fixtures**

- An AB pair at 1,000 per unit gives 2,000 once; CAPEX receives 2,000, not 4,000.
- A $/ft unit price with a quantity in metres converts through the unit converter and records the conversion.
- A $/ft unit price with a quantity in m² is rejected.
- Quantity 0 produces an excluded line with its reason.

## F. Timeline

**Decision**

1. Project year 0 is the basis (decision) year. Construction occupies project years 1 to C.
2. Operating year 1 is project year C+1, matching the current cashflow view.
3. Calendar year = basis calendar year + project year.
4. Startup falls in operating year 1 by default, with the production ramp handling reduced output. A separate non-operating startup period exists only if the user specifies one.
5. Working capital is recovered at the end of the final operating year. A closure period after operation exists only when closure costs or salvage values are specified.
6. Phases must appear in this order: pre_operation, construction, startup, operation, closure. **The current `Timeline` model accepts operation before construction and closure before operation; add an order check.**

**Acceptance fixtures**

- C = 0: operating year 1 is project year 1.
- C = 1: operating year 1 is project year 2.
- C = 2: operating year 1 is project year 3, and construction spend falls in project years 1–2.
- A specified separate startup period shifts operating year 1 by one and keeps indices contiguous.
- A timeline with operation before construction, or closure before operation, is rejected.

## G. Stage and scenario commercial coverage

**Decision**

1. Contracts are never extended silently. Operating years outside a line's approved coverage are reported as gaps and excluded from approved totals, in both the stage ledger and Monte Carlo.
2. Extending a contract requires an explicit renewal or replacement assumption for that line, with an approval reference.
3. **Change the cashflow editor.** On a horizon change it currently repeats the last saved commercial terms into new years, labelled provisional (`backend/blocks/cashflow/schedule.py`, "last saved annual terms repeated"). That contradicts roadmap P4 ("contracts do not extend beyond their supported dates without an explicit assumption") and the R-01 rule now on main for Monte Carlo. It should propose the extension as pending, not apply it.
4. The production ramp applies only to volume-based lines (product sales, per-unit processing fees). It never applies to fixed fees such as capacity reservations.
5. The ramp is applied once, in the production schedule. Finance and scenarios consume ramped quantities and never ramp again.

**Acceptance fixtures**

- A 2027-only agreement in a project operating in 2027 and 2028 produces 2027 revenue only, with 2028 flagged as uncovered (roadmap ticket FV-ECON-004).
- An approved 2028 renewal creates the 2028 schedule.
- A fixed capacity fee is unchanged by the ramp; variable sales follow it.
- Stage, scenario and export agree on a fixed fee, variable sales and a ramp, for both an aligned and a short contract horizon.

## H. Legacy saved assessments

**Decision**

1. Reopening a saved assessment never backfills inferred fields.
2. Only facts explicitly stored in the snapshot (for example a currency or price-year field) may be projected into the new contracts.
3. Ambiguous legacy values, such as a free-text period, keep their original text and are marked `legacy_unverified`.
4. Reopening leaves the stored snapshot byte-identical. Recalculating under the new contracts happens only when a user reruns the study, which saves a new version.

**Acceptance fixtures**

- Reopen a saved assessment: snapshot bytes, quantities and the four economics totals (CAPEX, OPEX, Revenue, NPV) are unchanged.
- A legacy line with period "2019–2021" reopens with that text and `legacy_unverified`, not with a guessed year.

## Requested changes to the current B08 code

1. `Timeline`: enforce the phase order in decision F.
2. `MonetaryLine`: reject `approved` authority on missing or unresolved values (decision D.5).
3. `ExactDecimal`: add a magnitude bound. The model currently accepts `1E+400`; a sanity limit catches unit and scale mistakes.

NaN, infinity, binary floats and text such as "1,000" are already rejected correctly.

## Next steps

- Engineer 2 rebases `engineer-2/development` onto `main`, applies the three code changes above, and implements the approved handoffs with these fixtures.
- Engineer 1 reviews the integration pull request and the numerical parity results.
- Decision G's cashflow change and decision A's spend-fraction change modify current behaviour; they land with their fixtures in that pull request.
