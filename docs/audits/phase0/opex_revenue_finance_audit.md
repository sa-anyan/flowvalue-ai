# OPEX, Revenue Box and financial audit

Baseline `74f364d`; no financial policy/equation edits. Functional evidence is in `baseline_test_report.md`; equation/source validation remains separately classified.

## OPEX

`backend/opex/indexes/garrett/model.py` defines historical Chapter4/Table4-4 parameters with a stored PDF hash/page reference. The original PDF pages were not rechecked during this audit: **SOURCE NOT VERIFIED**. `evidence/factor_registry.json` preserves the actual structured ranges, calculation bases and applicability notes; no new factors were invented.

Supported categories include raw materials, utilities, operating labour, interest, payroll overhead, supervision, laboratory, maintenance, operating supplies, royalties, packaging/storage, insurance/taxes, administration, distribution/selling and R&D, plus definitions recorded in the factor registry. The exact 19 IDs are: `raw_materials`, `utilities`, `operating_labor`, `interest`, `payroll_overhead`, `supervision`, `laboratory`, `maintenance`, `operating_supplies`, `environmental`, `depreciation`, `taxes_insurance`, `plant_overhead`, `royalties`, `packaging_storage`, `administration`, `distribution_sales`, `research_development`, `other_manufacturing`. Category applicability is process-specific; a named category does not establish that every project supplies a credible number. Financing and depreciation remain identifiable rather than cash operating costs.

| Method | Actual equation / basis | Required data | Numerical evidence and limitation |
|---|---|---|---|
| Quantity-price | Annual quantity × matching denominator unit price | Source consumption, hours/ramp, loss/purity/allocation, money basis | `test_opex.py` quantity/unit/boundary cases; delivered tariffs not independently checked |
| Labour | FTE × salary per FTE/year | Staffing, salary basis, loaded/unloaded scope | Loaded payroll/supervision overlaps checked; staffing is not deduced by arithmetic alone |
| Factor | Fraction × named CAPEX/labour/revenue/component base | Source range, selected fraction, exact base, override rationale | Recursive dependencies/cycles/overlaps checked; arithmetic test does not validate source transcription |
| Fixed annual | Explicit annual amount | Currency/year, recurring/capital/WC scope and justification | No implicit market evidence |
| Engineering/market | Precomputed supported engineering annual amount | Evidence and formula text, not executable arbitrary equations | LLM proposals cannot replace supported deterministic quantity math |
| Utility | kW × load × hours × throughput × tariff | Electrical/shaft/hydraulic/thermal basis, efficiency and service tariff | `energy_costs.py` keeps bases distinct; default variable energy behaviour remains an explicit modelling choice |

`energy_costs.py` implements measured electrical, explicit electrical assumption, shaft/thermal divided by efficiency, hydraulic QΔP/η, specific-energy and power-density paths. `consumption.py` and `engineering.py` build annual consumption/cost evidence. `annual_phasing.py` modifies fixed cash costs via an explicit mobilisation schedule; variable consumption is not ramped again there. It defaults fixed costs to full cost once operating unless a user-owned schedule says otherwise. 314 days is a planning assumption, not a universal maximum operating efficiency.

Core OPEX validates matching currency/period and annual units, named bases, reviewed categories/exclusions and cost-scope overlap. Prices and salary/time/site assumptions are not automatically current or validated. Exact quantity/price sources are per-project; this audit did not ingest private production projects.

## Existing Revenue Box — preserved

Six categories remain unchanged: `product_sales`, `processing_services`, `capacity_availability`, `infrastructure_usage`, `environmental_attributes`, `other_contractual_income`. Avoided cost belongs to OPEX savings, not an invented seventh sales category.

`revenue/commercial_intent.py` requires source quotations and intent IDs; a physical outlet is not proof of a sale. `revenue/authority.py` binds user approval to current assumptions/source streams/calendar. Draft LLM assumptions are conditional, not contracts. `rate_workspace.py` supports stream/rate-based product quantities, price assumptions, periods and editable methods; Python performs arithmetic. Price suggestions require opted-in research and remain sourced drafts, not guaranteed supplier/market prices.

Product physical quantity is rate × operating hours × throughput × allocation × saleability, limited by an explicit sold fraction/market assumption. Net prices avoid adding charges already included in FOB/net terms. Additional direct commercial lines use explicit annual `PaymentYear` quantities and billing terms. A general non-product path is:

`max(minimum_payment, fixed_payment + max(quantity, minimum_quantity) × rate × periods × availability) × (1 + escalation)^(year − 1)`.

The direct contract schedule is already annual: no hidden second ramp. Monthly capacity reservations require explicit billing-period convention. Minimum payment is a floor, not extra revenue. Environmental attributes require a documented eligibility/ownership basis, not automatic regulatory verification.

Duplicate `payment_id` checks and distinct fixed/variable scope controls exist in `validation.py`. They cannot prove two differently named arrangements do not charge for the same payment. Physical stream sharing is legitimate for separate treatment fees and water sales when explicitly approved.

### Record contract discrepancy — R-04

The task specifies an established **13-field** record. Actual `CommercialLine` in `backend/revenue/models.py` has **15 fields** (listed in `evidence/inventory_counts.json`); `Product`, `PaymentYear`, LLM schemas and UI rate drafts are additional contracts. No exact versioned 13-field specification was found. This is a mapping/compatibility evidence gap, not a reason to delete fields or rewrite the Revenue Box. Engineer2 and Engineer1 must agree the contract before Phase2 changes.

## Financial model

One typed engine builds one annual ledger; metrics consume that ledger. `backend/financial_modelling/` has separate calculation, model, validation and connector modules. `engine.py` uses Decimal precision40 for core calculations and preserves issues/status.

| Component | Implemented behaviour | Assumptions / limits |
|---|---|---|
| Timeline/production | Anniversary-based construction and operating periods, day-based active fractions, explicit ramp | Calendar conventions and operating-vs-project-year mapping must match all upstream schedules |
| Capital | Explicit dated asset spend, startup, disposal, replacement and depreciation basis | Approved spend profile is user planning policy, not a universal textbook curve |
| OPEX/revenue | Annual recurring fixed/variable/sales/payment records, driver-aware phasing | Known amounts remain visible; full finance can wait for unresolved totals |
| Depreciation | None, straight-line, declining balance and supplied MACRS rates | No automatic jurisdiction eligibility; book/tax basis shared preliminary policy |
| Tax | Annual rate, carried loss lots/expiry/offset and nonrefundable credits | No implicit tax refunds; no deferred-tax accounting or automatic tax-law certification |
| Working capital | Required balance changes and terminal fraction recovery | WC remains separate from recurring expense |
| Financing | Draws, equal principal/annuity, grace/balloon and equity funding | One nonrevolving facility; interest expensed, residual-equity mode is not a funding commitment |
| Cash flow | Operating=NI+depreciation−gain−ΔWC; investing=−CAPEX+proceeds; equity adds draw−principal | FCFF/project and FCFE/equity distinguish financing |
| NPV | Discounted recurring and point series using one selected timing convention | Discrete end, continuous end and Garrett uniform conventions differ; cannot compare without matching basis |
| IRR/MIRR | Explicit undefined/multiple-root status, MIRR finance/reinvestment rates | Float/log polynomial root isolation vs Decimal ledger; nonconventional continuous search explicitly bounded |
| Payback | First cumulative recovery with annual linear interpolation; discounted variant | Within-year timing approximation; not recovered ≠ zero years |
| ROI/PI | Lifetime accounting ROI; discounted benefit/cost ratio | ROI is explicitly not annualised |
| Unit economics | Levelised cost, production cost, contribution margin, break-even | Product allocation explicit; no arbitrary multi-product allocation |
| Uncertainty | Seeded Monte Carlo, bounded marginals/correlations, shared recalc | Distribution choice/equipment completeness still need engineering approval |

Independent synthetic finance arithmetic exists in `test_financial_modelling.py:226` (explicit FCFF/NPV/IRR/payback). Source-table expected NPV constants exist at `:575`; original table/page and transcription not independently checked here. These are meaningful tests, but do not certify the entire financial engine. OpenPyTEA parity tests compare software, not industrial outcomes. Individual verification coverage is not numerically established merely by static test links.

## Observed integration defect and reporting limits

The original full baseline has one failed Monte Carlo integration test: `test_manual_price_monte_carlo_reconciles_same_canonical_run` expects complete and receives partial. A read-only synthetic reproduction shows commercial annual schedules not matching the requested operating years, missing annual-revenue OPEX bases, then pending finance. Equipment itself is priced in that fixture. This is a schedule/contract handoff failure, not evidence of a wrong equipment formula. It is R-01 and was not repaired during Phase0.

Frontend tests/build passed. Complete saved-scenario agreement across browser, API, exports and all financial charts remains **UNVERIFIED**; no browser-based production assessment was modified to manufacture that evidence.
