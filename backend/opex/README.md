# Offline OPEX estimation engine

Garrett Chapter 4 is the default and the only implemented methodology. This
package does not change the frontend, equipment costing, CAPEX, saved projects
or existing financial calculations. No provider calls, research, HTTP routes,
automatic classifications or live financial handoffs are enabled.

## Layout

```text
opex/
  models.py                  immutable assumptions, bases, results and snapshots
  registry.py                list_models/get_model/get_factor_ranges/calculate_opex
  engine.py                  validated deterministic annual calculations
  engineering.py             power expense, straight-line depreciation, interest
  connectors.py              inactive canonical CAPEX/financial adapters
  advisor.py                 future advisor/research protocols and draft validator
  indexes/
    garrett/model.py         source parameters, applicability and group checks
    legacy_reference.py     original workbook provenance and section mapping only
```

Future methodologies belong in their own `indexes/<method>/` package and register
their own categories/checks in `registry.py`. No factors from unselected methods
are merged. Placeholder models are not advertised as supported methods.

## Source review

Default parameters were checked against **printed page 52 / PDF page 64** of
Donald E. Garrett, *Chemical Engineering Economics* (1989), Table 4-4. Read the
conditions in Chapter 4 pp.44–63 alongside the parameters. The local source file,
hash, page and reference are recorded in the model. Only independently
implemented numerical parameters and concise applicability notes are stored;
the source PDF, scans and table layout are not distributed in the package.

- Labour factors use **operating labour only**, not all staffing or loaded wages.
- Capital factors use **fixed capital including offsite plus startup**, excluding
  working capital. This is not purchased equipment, bare module or total CAPEX.
- Sales factors use explicitly supplied annual revenue, not production capacity.
- Raw materials, utilities, operating labour and interest need itemized inputs.
- Local taxes and insurance are a combined allowance. To split them, replace the
  allowance with detailed `taxes_insurance:local_taxes` and
  `taxes_insurance:insurance` items. Income tax belongs in the financial model.
- Packaging and storage are similarly combined; prevent duplicate freight,
  handling or storage already charged in delivered feed prices or selling costs.
- Maintenance includes labour/materials/services; laboratory includes staff and
  supplies. Declare these scopes on separate staff or materials when applicable.
- Group totals/typical rates are **comparison checks**, never additional charges.

Source discrepancies remain explicit:

1. Table R&D maximum is 4% of sales; prose p.62 mentions 5%. Default is the table.
   A different fraction needs a documented user override.
2. Sales-row maxima sum to 36%, whereas the printed group maximum is 37%.
   Calculations sum the actual rows and retain the published comparison range.
3. Royalties prose p.57 gives narrower illustrative guidance than the table.
4. Table depreciation is a historical preliminary allowance, not a tax schedule.
   The separate straight-line helper uses caller-supplied depreciable assets
   (excluding land), salvage, lifetime and operating year, and stops at end of life.

The founder's `Task 2 Charlie Economics 2.xlsx`, `Opex` sheet, was inspected
read-only. Its hash, section cell addresses and methodological differences are
retained in `indexes/legacy_reference.py`. No workbook formulas or numeric
assumptions are imported. It is not a competing default model. No workbook or
textbook files were modified.

## Input contract and methods

Use `OpexInputs` containing immutable tuples of `Assumption`, `MoneyBase` and
`Exclusion`. Each line needs an ID, category, method, fixed/variable behaviour,
currency/price period, rationale, source, uncertainty description and cost scopes.
Split mixed fixed/variable costs into separate lines; no behaviour is guessed.

| Method | Inputs | Annual arithmetic |
| --- | --- | --- |
| `quantity_price` | annual quantity, unit price | quantity × rate |
| `headcount_salary` | FTE, annual salary/FTE | headcount × salary |
| `percentage` | fraction, named/category/item base | fraction × resolved base |
| `fixed_annual` | annual amount | explicit allowance |
| `engineering` | annual amount, calculation description and evidence | supplied documented engineering result |
| `market_price` | annual amount and supporting evidence | supplied annual quote/estimate |

`engineering_formula` is descriptive evidence only: arbitrary formula text is
never executed. The independent engineering helpers perform the supported power,
straight-line and interest arithmetic. Other engineering calculations must be
provided by a reviewed deterministic upstream calculation; they are not validated
merely by receiving a label or source string.

For `quantity_price`, `quantity_unit` is e.g. `kg/year` and `rate_unit` is `kg`
(denominator of currency/kg). Supported unit tokens are `kg`, `t` (metric tonnes),
`g`, `lb`, `m3`, `L`, `kWh`, `MWh`, `MJ`, `GJ`, `MMBtu`, `unit`, `h`.
Ambiguous thermal/reference-volume definitions must be resolved upstream.
FTE quantities use `FTE` and annual salary denominator `FTE/year`. Annual
consumption already includes operating hours, availability and losses as applicable;
the engine does not silently annualize or apply ramp-up again. Normalize differing
units using the existing canonical conversion layer before passing quantities.
Different quantity/price units are rejected, not guessed or relabelled.

Fractions are decimal fractions (e.g. `.05`, not `5`). No factor is automatically
selected. A table-backed percentage uses the published base and inclusive bounds.
Departures require `override=True` and `override_reason`; results warn that the
assumption differs from Garrett. A percentage without a published Garrett factor
also needs an explicit override. Detailed price, staffing and fixed allowances
can replace factor estimates without pretending they are source factors.

Named money bases: `purchased_equipment`, `installed_equipment`, `bare_module`,
`fixed_capital`, `plant_including_startup_excluding_working_capital`,
`annual_revenue`. These are not interchangeable. Dependencies on resolved annual
costs use `category:<category_id>` or `item:<assumption_id>`. Self references and
cycles are blocked; there is no guessed algebraic circular-cost solution.

Every price/base must share the exact currency and price period. No FX or price
escalation is inferred. **CEPCI must not be applied to salaries, utility tariffs
or commodity prices as though it were a general inflation index.**

## Completeness, overlap and accounting

All 18 Table 4-4 categories require an assumption or an explicit, reasoned
exclusion, including no-borrowing decisions. `other_manufacturing` accepts
additional project-specific expenses without an invented default factor.
`reviewed_categories` explicitly attests itemization/applicability review;
absence of this review blocks totals. A line does not prove that every plant
expense has been discovered.

Scopes are hierarchical: `utilities` covers all utilities;
`utilities:electricity` and `utilities:steam` can coexist; a full utilities
allowance and a separate electricity charge cannot. Bundled salaries can declare
`payroll_overhead` as an included scope; adding another payroll allowance is then
blocked, and that bundled salary is not a clean operating-labour factor base.
Users must label inclusions consistently. Semantic duplicates disguised with
different scope names cannot be discovered by deterministic bookkeeping alone.

`scope='capex'` and `scope='working_capital'` amounts are reported separately,
not included in recurring annual OPEX. Initial catalyst and inventories are
examples; ongoing makeup and disposal can be recurring costs. Reserve accounts
are not automatically recurring expenses. Financing (interest) and noncash
depreciation are excluded from `annual_cash_opex` and shown separately.

Missing/invalid inputs produce `needs_review`, explicit issues and no final totals.
`resolved_cash_subtotal` is only a partial inspection aid. A complete calculation
is `calculated_preliminary`, **never engineering-verified or accredited**.
Historical factors do not establish present-day site-specific cost accuracy.

## Snapshots and inactive connectors

`freeze_assumptions(inputs)` → portable JSON; `restore_assumptions(json)` restores
the immutable inputs. `scenario(inputs, assumptions=...)` returns a new scenario
without changing the baseline. Results include an input SHA-256 and methodology
source. Decimal arithmetic uses a local precision of 40, independent of the
caller's global context. Freeze one operating-year case per scenario; this is
not a loan amortization, tax depreciation or multiyear production model.

`prepare_opex_inputs(canonical_capex_result, ...)` prepares explicit bases only,
never calls either engine. It rejects unresolved CAPEX and preserves supplied
engineering context as JSON. `financial_handoff(result)` rejects incomplete OPEX
and returns cash, depreciation and financing separately, ready for a future
reviewed integration. Nothing is connected to live calculations.

`advisor.py` defines draft assumptions, missing categories, clarification questions,
process/equipment/balance/CAPEX context, evidence metadata and opt-in research
requests. No LLM SDK, model, network call, external research or provider
implementation is present. A future reviewed proposal still passes the same
deterministic checks; proposal validation never applies or saves it. Future
research requires a permission reference, dated evidence, units, location and
uncertainty. A public listing or an LLM opinion is not verified plant data.

## Checks

From repository root:

```sh
python3 -m unittest backend.tests.test_opex -v
python3 -m unittest discover -s backend/tests -v
```

Tests cover source factors/bases, all boundaries, independent min/max totals,
selected rates, itemization, detailed replacements, overlap, cycles, missing
inputs, currency/period/units, nonrecurring exclusions, scenario restoration,
canonical adapters and inactive advisor draft validation. These are software and
source-transcription checks, not industrial validation of a particular plant.
