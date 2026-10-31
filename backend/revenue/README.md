# Revenue estimation engine

The working engine now supports six independent commercial categories, consolidated
annual revenues, separate avoided-cost OPEX reductions, the existing bounded LLM
orchestration and the local editable Revenue page. See [MECE architecture and
calculation rules](MECE_ARCHITECTURE.md) for the current integration, assumptions,
compatibility and limitations. Earlier product-sales implementation details follow.

## Source and methodology

Donald E. Garrett, *Chemical Engineering Economics* (1989), Chapter 5,
**Product Sales Value / Market Research**, printed pp.75–76 / PDF pp.87–88, in
the supplied `Chemical Engineering Economics for me.pdf`. Printed p.76 was
visually inspected. The filename, SHA-256, reference and page are recorded in
`indexes/garrett/model.py`. Chapter 5 also covers interest and preliminary project
evaluation; this implementation uses its sales section, not historical taxes.
No workbook formulas or spreadsheet assumptions were used.

Garrett provides a market-investigation workflow, **not universal selling prices,
premiums, discounts, sales fractions or market-growth factors**. Consequently no
such commercial numbers default automatically. The historical 10% share guidance
for an established market produces a review warning, never a hard share limit.
Only Garrett is currently registered; future methodologies remain independent.

## Structure

```text
revenue/
  models.py                 immutable streams, assumptions, products and schedules
  engine.py                 deterministic annual production/sales/net-price math
  registry.py               list_models/get_model/calculate_revenue
  advisor.py                structured proposals + optional OpenAI transport
  research.py               future market-research consent/evidence contract only
  snapshots.py              frozen projects, editable revisions and review actions
  persistence.py            matching input/result/proposal bundles, no overwrite
  connectors.py             canonical Measurement import and explicit OPEX/DCF handoffs
  indexes/garrett/model.py   source reference and contextual guidance
```

## From engineering input to sales

1. Pass parsed, sourced `Measurement` values through `stream_from_measurement`.
   The adapter requires provenance, preserves original value/unit/source, defaults
   the physical boundary to **unresolved**, and performs no parser or AI calls.
   Alternatively supply already normalized `Stream` records explicitly.
2. Optionally call `propose_products` to identify candidate main products and
   by-products against those existing stream IDs. It never changes project data.
3. Establish allocation, specification suitability, saleable fraction and annual
   commercial assumptions. `draft_product` retains unknowns and cannot approve
   saleability or invent flow/yield values.
4. Review the candidate and calculate with Python. Unknown physical information,
   unconfirmed product/customer suitability or missing active assumptions block
   the authoritative annual schedule.
5. Save the immutable inputs and matching calculations. Create edited scenarios
   without changing the baseline. Preview recalculation needs no LLM request.

An outlet is never automatically a sale. Unassigned outlets are flagged and not
included in revenue. Explicit product exclusions require a reason. All-excluded
products can deliberately yield zero; an absent product decision is unresolved.
Prospective customers are contextual leads, not contracts. No numeric probability
of winning a contract is generated or applied to expected revenue.

## Deterministic arithmetic and units

For every included product and explicit operating year:

```text
produced = normalized outlet flow per hour × operating hours
           × throughput fraction × allocated stream fraction
saleable = produced × saleable specification fraction
sold     = saleable × sales fraction
           OR an explicit sold quantity not exceeding saleable output
           OR min(saleable, addressable demand × selected market share)
unsold   = saleable − sold

net unit price = quoted unit price + premiums − revenue deductions
annual product revenue = sold × net unit price
annual revenue = sum(included product revenues)
```

Operating hours and throughput are shared per year across products. Hours already
represent the supplied annual operation: do not duplicate availability in hours
and throughput. The chosen flow basis, throughput ramp and quality fraction must
be justified. Allocations across products using the same stream cannot exceed
100%. Allocation does **not** design a separator or prove component recovery.
Inventory carryover, purchased resale and inter-product conversion are not assumed.
Unsold output reduces quantity sold; it is not deducted from revenue a second time.

The existing canonical converter normalizes hourly mass, volume or molar rates
into the selected price quantity unit per hour. Source and conversion references
are retained. Ambiguous tons/gallons need an explicit conversion context; unsupported
gas-reference changes or mass↔volume conversions require engineering information.
No density, molecular weight, moisture or purity conversion is invented. Original
values remain in the frozen inputs. Canonical conversion uses its existing floating
point implementation; revenue arithmetic uses Decimal at local precision 40.

Prices have an explicit unit such as `GBP/kg`; sold quantities use `kg/year`.
Currency and valuation-period conventions reuse the canonical OPEX `Basis`.
No FX, inflation, CEPCI price escalation or nominal/real convention is inferred.
Use one consistent valuation convention and explicit per-year prices. Years are
positive operating-year indices, not calendar dates; market base year uses that
same index. Market demand can be projected from explicit baseline demand and
annual growth, including negative growth above −100%. No growth default is used.
Known demand must not be less than planned sales without revising the market scope.

## Price and cost accounting

Use `net_fob` or `gross_quote` plus explicit commercial terms. `included_charges`
states what the quoted price already incorporates. `additional_charge_scopes`
identifies deductions expressly outside that price. A scope cannot be both.

Adjustments have a unique identity and economic scope, a premium/deduction
direction, an assumption and one accounting treatment:

- `revenue`: changes net unit selling price once.
- `included_in_quote`: records an existing adjustment without subtracting again.
- `opex`: returns a separate, **unapplied** selling expense without reducing revenue.

Supported adjustment arithmetic is an amount per sold unit or a fraction of the
original quoted price. Fractions do not silently compound on adjusted prices.
All percentages need explicit rationale/evidence or an acknowledged estimate;
there are no default commercial percentages. Negative net selling prices are
blocked for review as a potential disposal/purchasing cost, rather than silently
classifying a payment to a buyer as product sales. Annual fixed selling expenses
belong in OPEX rather than being divided by potentially zero sales here.

Exact/hierarchical duplicate charge scopes and already-included deductions are
rejected. Semantically identical expenses with different scope names still require
human reconciliation. The engine does not know which existing OPEX items contain
freight/packaging: explicit handoffs flag separate charges for reconciliation,
never automatically add them. Purchasing costs are not product sales.

## Assumptions, evidence and market context

Each numeric `Assumption` contains value (or unknown `None`), units, rationale,
source when available, uncertainty, ISO as-of date and evidence status:
`source_supported`, `user_assumption`, or `llm_estimate`. Source-supported values
require a reference, but a reference is not independent source validation.
Unknown values differ from zero. Every active numeric assumption is validated;
an unresolved result has issues and no authoritative annual totals. Partial product
rows are inspection evidence only.

Physical stream flow, allocation and quality fractions cannot be supplied as LLM
estimates. They require engineering evidence or explicit user assumptions; this
still does not constitute physical or specification validation.

Product context retains specifications/customer requirements, geography, historical
market notes, competing producers/capacity/location descriptions and prospective
customers. Missing market evidence is visible. Only actual demand/growth inputs
drive numerical market projections; notes do not become invented numbers.
Market share, quantities, prices, allocations and deductions remain editable.
Confirmed suitability and reviewed status are user decisions, not certification.

## Optional LLM connection

`OpenAIRevenueProvider` implements a bounded Responses API structured-output call.
Official contract checked during implementation:
[OpenAI structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs).
The implementation uses Python's standard library; no SDK/vendor code is copied.

Server-side configuration only:

```text
AI_ENABLED=true
OPENAI_API_KEY=<server secret>
OPENAI_MODEL=<explicit configured model supporting structured output>
```

No model is selected implicitly. `from_environment()` checks the enable flag;
`propose_products(project, provider, allow_model_call=True)` additionally requires
explicit authorization to send context. Credentials are never put in source,
project snapshots, prompts or browser-facing configuration. Redirects are blocked,
timeouts/output/context limits apply, provider errors are sanitized, response
refusals/incompletion/malformed data are rejected. No automatic paid retries.
`store=false`; no search/tool calls. This does not establish provider retention
policy, quota or model access.

The versioned prompt asks a chemical-engineering commercial analyst to identify
candidate uses and important unknowns, distinguish market assumptions from physical
facts, and propose justified commercial estimates only. It sends selected typed
project context, not original workbooks, authentication records or arbitrary project
objects. Still review proprietary content before explicitly sending it to a model.
Input descriptions are treated as untrusted data, not tool instructions.

Local validation rejects unknown fields, invented stream IDs, unknown classifications,
invalid numeric suggestions, duplicate assumptions and citations not present in
the provided context. The model may return null and questions when a price or
commercial basis is insufficient. Unsourced proposals remain unverified LLM
estimates; plausibility and truth cannot be established by schema validation.
No contract probability or financial arithmetic is accepted from the model.

`draft_product` maps price, sales-fraction and market suggestions to an incomplete
candidate, leaving allocation/quality/specification/terms unknown. Premium/discount
suggestions remain in the proposal until the user explicitly chooses adjustment
scope, basis and accounting. Proposals carry prompt/model/time/project-snapshot
metadata and cannot be applied to a changed project without renewed review.

Future market research has separate request/evidence contracts and a consent-state
gate (`research_readiness`). It does not perform research. Missing-price research
needs an explicit opt-in; refusal makes zero research calls. Approved consent only
prepares the future connector. This build did not execute paid generation, source
market facts or validate any real buyer/price.

## Editing, saving and future integration

```python
result = calculate_revenue(project)
preview = calculate_revenue(edited_project, preview=True)
snapshot_json = freeze_project(project)
restored = restore_project(snapshot_json)
save_assessment(project, result, path_to_new_json_file)
```

`revise_project` creates a new revision with actor/reason, parent hash and a matching
expected snapshot. Changed products, or all products affected by an operating
schedule change, require renewed review. `review_product` records an explicit
decision. Draft preview bypasses only acknowledgement, not physical/specification/
unit/commercial validation. These functions make no AI requests. Frozen input
objects preserve the original baseline.

`save_assessment` persists matching input, calculation and optional proposal JSON
to a new file, refusing overwrite and stale result/proposal combinations. Snapshots
are schema-versioned and reloadable. Files and actor labels are not authenticated
database history or signed approval. Retain baseline and revised files explicitly.

`annual_revenue_base(result, year)` returns the canonical `MoneyBase` used by
Garrett OPEX sales-based factors. It uses net product-sales revenue, not revenue
after separately classified OPEX. `financial_handoff` returns per-year sales and
separate unapplied selling charges. Both reject incomplete/draft results. These
are explicit adapters, not live connections; OPEX source code is unchanged.

No HTTP server, UI, DCF, new supplier-research service or production deployment was
added. Future Revenue-page wiring can restore a snapshot, edit assumptions and
invoke this engine; its existing page need not be rebuilt around an LLM call.

## Verification

```sh
python3 -m unittest backend.tests.test_revenue -v
python3 -m unittest discover -s backend/tests -v
```

Independent synthetic cases cover annual quantities/revenue, ramp-up, by-products,
unsold output, allocation limits, price units/conversion, premiums/deductions,
already-net prices, separate OPEX, demand/share/growth, missing data, edits, snapshot
restoration, persistence, canonical adapters, and mocked AI/schema/provider failures.
No supplied legacy-workbook formulas or expected results are used. These checks
establish software behaviour, not industrial or independent market validation.
