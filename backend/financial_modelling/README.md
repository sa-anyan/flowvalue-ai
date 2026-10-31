# Annual financial modelling engine

One deterministic engine (`calculate_financials`) produces one immutable annual
ledger. P&L, project/equity cash flows, financing, metrics and reporting data all
use that ledger. No upstream costing engine, parser, frontend, HTTP API or live
LLM integration is modified.

## Public workflow

```python
from backend.financial_modelling.connectors.calculator import prepare_financial_inputs
from backend.financial_modelling import calculate_financials, save_assessment

# All economic assumptions/policies/mappings are explicitly supplied by caller.
inputs = prepare_financial_inputs(
    project_id=project_id,
    assumptions=assumptions,
    capex_result=capex_result,
    opex_by_revenue_year=opex_results,
    revenue_result=revenue_result,
    year_map=revenue_to_financial_years,
    price_year=declared_price_year,
    capital_spend=construction_percentages,
    depreciation_policies=asset_policies,
    disposal_proceeds=declared_residual_values,
    startup_treatment=startup_treatment,
    working_capital_funding_year=wc_funding_year,
)
result = calculate_financials(inputs)
save_assessment(inputs, result, new_file_path)
```

`FinancialInputs` can also be supplied directly for independently specified cases.
The composite adapter consumes existing results and does not rerun upstream engines.
It records full CAPEX/OPEX/Revenue snapshots in the saved inputs. Missing active
inputs or reconciliation failures return `needs_review`, no ledger or metrics.
A valid model returns `calculated_preliminary`, never industrially validated.
Undefined individual metrics retain their own status, basis and unavailable value.

## Components

| Package | Implemented responsibility |
| --- | --- |
| `assumptions` | Canonical sourced scalar contracts, money, explicit FX and escalation |
| `financial_schedules` | Single annual timeline, construction/commissioning/first-production validation and date-based active fractions |
| `production_sales` | Reuse Revenue's flow/quality/sales calculations with explicit hours, availability and utilisation |
| `capital_investment` | Editable CAPEX distributions, startup, replacement, sustaining and expansion expenditure |
| `operating_costs` | Actual annual cash costs or explicitly driver-scaled variable costs; fixed/variable and COGS/SG&A distinctions |
| `depreciation` | Asset-specific straight line, declining balance with optional straight-line switch, supplied MACRS rate tables and nondepreciable capital |
| `taxation` | Explicit annual rates, optional expiring losses, offset limits, interest/closure/disposal treatment and supplied nonrefundable current-year credits |
| `profit_loss` | Gross profit when classifications permit, EBITDA, EBIT, interest, pre-tax and net income |
| `working_capital` | Explicit required balances, incremental investments and terminal recovery |
| `financing` | Term debt, draws, grace period, equal principal/annuity, cash interest, optional shutdown balloon, equity funding and DSCR |
| `cash_flow` | Operating/investing/financing statements, FCFF/FCFE, cumulative cash and timing-aware discounting |
| `investment_metrics` | NPV, project/equity IRR and MIRR, ROI, payback, profitability index, accounting break-even and DSCR |
| `unit_economics` | LCOP, cash/full production costs and contribution margin on declared product bases |
| `reconciliation` | P&L/cash, debt, working-capital, timing and project/equity bridges |
| `connectors` | Explicit upstream imports and baseline-preserving scenario recalculation |

The root `models.py` is the only annual-ledger definition. Component `models.py`
files re-export relevant canonical schemas; component interfaces expose independent
calculators. There are no separate financial ledgers or source-specific engines.
Additional domain validators can be separated further as policies expand; current
checks run in calculators and the root cross-component validator.

## Timeline and timing conventions

- Year zero is an instantaneous project-start cash point. It is not an operating
  year and cannot take annual depreciation.
- Years 1 onward are anniversary-based annual periods. Cash investment can be
  explicitly assigned to year zero or later year-end points. Construction shares
  must be nonnegative, unique by year and sum exactly to 100%.
- Initial direct/indirect/offsite capital stays within the declared construction
  window. Replacement/sustaining/expansion capital has its own explicit schedule.
- Commissioning cannot precede construction completion; production cannot precede
  commissioning. Operating lifetime is measured from first production.
- Midyear start/shutdown dates produce actual-day fractions for physical operation.
  These **do not turn the model into monthly modelling or XNPV**: annual cash
  positions and full-year asset schedules remain declared conventions. Terminal
  cash occurs at the last annual model point, not an automatically exact shutdown day.
- Annual periods are limited to 150, construction to 30 years and operation to 100.

Three explicit discount conventions are available: `discrete_end`,
`continuous_end`, and `garrett_uniform`. The last discounts recurring operating
cash continuously across each annual interval while capital/WC/terminal components
remain point cash. Every NPV/IRR/payback/LCOP uses the selected convention; rates
must be consistently effective annual or continuous as appropriate.

## Production, sales and variable OPEX

An upstream `RevenueResult` already contains produced, saleable and sold quantities
and net revenue. The finance adapter does **not** apply availability, utilisation
or sales ramp a second time. Every active financial period requires an explicit
operation row, even if its actual production is zero.

For an upstream physical plan, `revenue_with_operating_plan` calls the existing
Revenue engine with effective hours = annual hours × availability × active-date
fraction, and throughput = explicitly supplied utilisation. All active periods,
including partial terminal periods, must be covered. Revenue's quality, allocation
and sales assumptions stay separate and source-linked. No flow, market price,
product yield or production assumption is invented.

Cash OPEX accepts `actual` amounts, which are never scaled again, or `driver`
amounts computed from base cost × actual/reference physical activity. Driver ID,
matching units, a positive reference quantity and source are mandatory. No generic
"multiply all variable costs by utilisation" rule is introduced.

Upstream depreciation and interest are excluded from cash OPEX and recalculated
under the financial asset/financing policies. Gross profit is unavailable when
COGS/SG&A classification is incomplete; explicit depreciation-to-COGS allocation
is required. Category and item cost breakdowns are retained for dashboard grouping.

The adapters reject stale OPEX sales factors that do not match the selected Revenue
year. The composite adapter also rejects stale/incompatible OPEX capital-factor
bases against canonical CAPEX. Align their currencies and valuation bases upstream.
A financial sensitivity does not implicitly rerun engineering or OPEX correlations:
refresh the upstream dependent snapshots when changing their bases, or explicitly
supply and document independent annual overrides. Actual costs remain actual.

## Capital, depreciation and tax

The CAPEX import uses direct + indirect + offsite + startup and keeps working
capital separate. Purchased equipment, installed/module costs and allowances are
not added again. Working capital is imported once at an explicit funding year;
a divergent manual balance requires a rationale. Recurring annual changes and
partial terminal recovery are supported; unrecovered capital is visible.

Startup is either capitalized or expensed. Expensed startup is not also invested,
depreciated or written off as an asset at shutdown. Depreciable fractions,
service/disposal years, asset life, book residual and terminal proceeds are explicit.
Straight line flushes numerical rounding residue in its final year. Declining
balance can switch to straight line. Nondepreciable assets retain book basis.
Disposal gains/losses use proceeds minus remaining book value.

`macrs` is a **supplied rate-table calculation**, not an automatic US tax election.
Supply the full table, source and class/convention/eligibility statement; `life`
then denotes the number of schedule entries, not automatically the named property
class. The table may incorporate a first-year convention. No eligibility, bonus
depreciation or recapture rule is inferred. IRS source used to verify this boundary:
[Publication 946](https://www.irs.gov/publications/p946).

Tax requires an explicit jurisdiction/policy source and a rate for every model
year, including zero. Losses can carry forward with a supplied expiry and offset
limit; no tax refund/carryback or terminal monetization is assumed. Separately
supplied current-year credits are nonrefundable, capped at tax liability, have no
carryforward and require a policy/eligibility source. They are not automatic 45V
or other subsidy qualification. Project taxes exclude debt interest; equity taxes
use the explicit interest deductibility policy. Their loss balances stay separate.

**Preliminary convention:** selected depreciation is shared for book and tax.
Separate book/tax depreciation, deferred taxes, progressive/bracketed taxes, VAT,
asset-specific gains/recapture rates and legal filing compliance are not implemented.
Time-zero expenses use a separate model loss bucket carried to later model years;
this is not a jurisdictional calendar-tax filing calculation.

## Financing and accounting identities

One non-revolving project-currency term facility is supported. Draws occur before
amortization; repayment can start after a grace period. Draw timing determines
first-year interest. Construction interest is cash-paid/expensed, **not capitalized
or rolled into principal**. Principal never reduces taxable profit. Debt beyond
shutdown requires an explicit balloon. Multiple facilities, refinancing, floating
rates and foreign-debt remeasurement are future extensions.

Residual equity mode explicitly funds annual deficits and distributes surpluses;
it is an unlimited-funding scenario assumption, not a lender/investor commitment.
Specified equity mode rejects funding shortfalls. Both report contributions,
distributions and financing cash separately. In this distribution model closing
cash is zero, rather than silently accumulating an unspecified treasury balance.

```text
operating cash = net income + depreciation − disposal gain − WC cash change
investing cash = − capital investment + asset proceeds
FCFE = operating cash + investing cash + debt draw − principal
FCFF = unlevered operating cash + project investing/WC/terminal cash
FCFE = FCFF + project tax − equity tax − interest + debt draw − principal
```

DSCR uses cash available before debt interest/principal and excludes new borrowing,
asset sale proceeds and terminal WC recovery. Its denominator is cash interest plus
principal; no service means undefined. Reported minimum includes any construction
period with debt service (therefore a zero construction DSCR is possible).

## Units, FX and valuation

Use explicit `Money(amount, currency, price_year, source)` and sourced `Assumption`
values with units, date, rationale and uncertainty. Unknown `None` differs from zero.
Finite amounts, quantity ordering, units, duplicates, period alignment, dates and
scope are validated. Real input prices must already use the declared financial
base year. Actual nominal amounts must carry their annual calendar price year.
A `base` price can be explicitly forecast with escalation; an `actual` annual price
cannot be escalated again. Terminal proceeds/closure have explicit price treatment.

FX is a supplied project-currency-per-input-unit rate with a calendar year. Missing
or duplicate required FX blocks calculation; no live lookup occurs. Foreign-debt
principal must be converted/restructured into a project-currency facility explicitly.
A known zero needs no fabricated FX. Generic financial inflation is not a substitute
for CEPCI or a chemical/utility market price index. Corporate historical equipment
prices must be aligned upstream before current-cost financial integration.

## Metrics and edge cases

- IRR never selects an arbitrary root when multiple rates exist. Discrete/point
  continuous IRR uses numerical positive-polynomial root isolation, including
  tangent roots. Extremely ill-conditioned values can be unavailable.
- Uniform-flow conventional IRR uses a bracketed continuous solution. Nonconventional
  uniform-flow cases return bounded-search candidates and no asserted unique IRR.
- MIRR uses explicit financing/reinvestment rates and the same timing convention.
- Payback is first cumulative recovery with disclosed linear within-year
  interpolation. No recovery/zero-output denominators remain unavailable.
- ROI is lifetime accounting net income / gross capital, expensed startup and
  positive WC investments, **not** an annualized return or equity ROI.
- Profitability index is PV positive net annual cash / absolute PV negative net
  annual cash. Its definition is preserved for subsequent capital spending.
- Break-even metrics are annual accounting zero-PBT quantity/price under constant
  unit contribution, excluding startup/disposal/closure. They are **not NPV-zero
  optimization**; no independent scenario solver is introduced.
- LCOP is pre-tax, unlevered discounted cash cost/capital/startup/closure/WC net of
  proceeds divided by discounted **saleable output**. Taxes, debt and credits are
  excluded. Cash/full production cost and contribution use their labelled bases.
- Multiple products need explicit cost allocation for product-level LCOP/unit/break-even
  metrics. No arbitrary summing of incompatible units or by-product credit is used;
  financial NPV and cash flow remain valid at project level.

## Persistence, scenarios, AI and reporting

`freeze_inputs` / `restore_inputs` use allowlisted typed, schema-versioned JSON.
Results contain currency, valuation mode/base year, discount convention, ledger,
metric statuses, warnings, source references and the input snapshot/hash.
`save_assessment` refuses stale results and file overwrite. Snapshots are not
signed approvals or an authenticated database history; retain revisions explicitly.

`connectors/playground.recalculate_scenario` creates a new immutable revision and
runs the same engine. Prices, quantities, expenses, capital, dates, rates, tax and
financing can be supplied as revised inputs. It does not contact an LLM, rewrite
the baseline, create a separate scenario engine or guess missing upstream data.

`interfaces.py` defines future structured financial assumption proposals only.
There is no model provider, paid API call, financial arithmetic by an LLM or live
research. The old frontend remains untouched; these are structured backend results
ready for a future authorized API/dashboard/report integration, not a live dashboard.

## Reference checks and implemented status

- Garrett Chapters 5–6; printed p.91/PDF103 Table 6-3 visually checked. With matching
  continuous uniform operating cash and point terminal WC, exact NPV is approximately
  2.523460 MM at 10% and −0.980839 MM at 12%, consistent with rounded table values
  2.5228 and −0.9808 MM. Exact continuous IRR is approximately **11.39645%**; the
  printed approximate 11.54% is retained as a discrepancy, not forced as test truth.
- Original Charlie workbook `NPV Calculation`, `ROI`, `Revenue`, `Final Summary`
  layouts inspected read-only. **No workbook formula, coefficient or expected
  numerical result was used**, consistent with founder source rules.
- Installed OpenPyTEA **3.2.1**, MIT licence inspected. Optional development-only
  harness `tools/compare_openpytea.py` checks its NPV metric after explicit timing
  alignment: first array entry is year one there; time-zero investment is added
  separately. A simple case differs by about 6.8e−15 currency units. No upstream
  source copied, code vendored or runtime dependency added. This is not full-model
  OpenPyTEA parity or adoption of its financial defaults.

The core annual end-to-end engine is implemented and tested. It remains preliminary,
with the policy/financing/allocation/timing limitations above. Independent engineering,
accounting and jurisdiction-specific validation remain outstanding. Only Garrett is
registered; Excel-reference/OpenPyTEA-inspired policy profiles are not advertised
as separately implemented models. They can later map policies into the same engine.

Run from repository root:

```sh
python3 -m unittest backend.tests.test_financial_modelling -v
python3 -m unittest discover -s backend/tests -v
```

The independent test suite covers construction, delayed/midyear production,
20% startup ramp, actual/driver OPEX, working capital, depreciation, taxes/losses/
credits, P&L/cash identities, unlevered/levered returns, IRR edge cases, unit costs,
stale upstream factor bases, original-baseline preservation, snapshots and full
CAPEX/OPEX/Revenue integration. Saved local evidence is under
`outputs/financial-modelling-review/` and is not a production dataset.
