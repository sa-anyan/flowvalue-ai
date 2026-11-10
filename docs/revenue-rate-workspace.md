# Rate-based Revenue workspace

The primary `/revenue` page is a compact editable income worksheet. Add product
sales or per-unit processing fees. Select a parsed material stream, or select
**Other** and supply a rate with a time unit (for example 2 m³/h). There is no
standalone annual/batch quantity input for these lines.

Python converts compatible rate units, multiplies by the saved operating hours,
applies the saved annual production ramp once, applies saleable/allocation/sold
fractions for products, and calculates income using the recorded price basis.
The analysis-period total sums the canonical annual revenue ledger. Construction
years remain under the existing Cashflow schedule. The 314-day calendar is an
editable planning assumption, not a physical maximum plant availability.

The calculation follows OpenPyTEA 3.2.1's rate × price × operating-time convention,
independently implemented over FlowValue's existing canonical revenue/financial
models. It does not replace finance with a second OpenPyTEA engine. The optional
reference test compares equivalent calendars against the installed upstream
`Plant.calculate_revenue` implementation. No upstream revenue code is copied.

## Assistant and authority

The Revenue Box continues to authorize income sources. The assistant drafts
editable lines from that text and the actual stream register. It cannot authorize
selling every outlet. For an explicitly supplied custom rate, Python extracts the
literal number/unit and gives the assistant an enumerated reference to select.
It cannot fabricate a flow rate or overwrite a workbook stream. Custom rates
retain `user_assumption` provenance without invented worksheet/cell references.
The user confirms draft inputs by clicking Calculate; Python validates before
approval. Save does not trigger an LLM or calculation. Missing commercial details
remain visible in the worksheet. No external research is started automatically.

The assistant is one unified MECE review popup, not a repeated sequence of full
commercial forms. See [MECE review implementation](revenue-mece-review-design.md)
for category controls, co-products, source-backed price proposals and consent. Explicit in-progress worksheet edits are retained when AI
interpretation returns. All six MECE methods have method-specific editors in the review popup. Existing
complex year-specific contracts and detailed ledgers remain available at
`/revenue?advanced=1`; they are not coerced into product sales. Existing deductions and other unchanged
inputs are preserved by simple line edits; changing the units of a line with
per-unit deductions requires reviewing those deductions in Advanced contracts.

## Verification

`backend/tests/test_revenue_rates.py` covers time-rate units, custom product and
service income through the canonical engine, one application of ramp-up,
traceability, explicit draft approval, invalid quantities/units, preservation of
existing deductions, and the optional OpenPyTEA 3.2.1 numerical comparison.
`frontend/tests/revenue-rates.test.cjs` covers saved-line interpretation and
preservation of advanced contract types and individual price periods.

A mass rate is not silently treated as a volume rate; a compatible quantity basis
is required. Unknown prices and unsupported contract details are not invented.

Local verification on 10 November 2026: 77 focused backend tests and 4 frontend
tests passed, along with the production build. Browser verification used an
isolated synthetic assessment, not a user project. A live AI draft retained the
literal 2 m³/h and USD 5/m³ inputs and 2026 price period. With an additional
3 m³/h processing fee at USD 2/m³, 314 days × 24 hours and 20 full operating years,
the canonical ledger and page both showed USD 120,576/year and USD 2,411,520 total,
with no unresolved calculation issues. Desktop horizontal overflow and browser
console-error checks were clear. These are software integration checks, not
verification of market prices or the underlying real-world engineering study.
