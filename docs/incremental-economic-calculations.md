# Incremental economic calculations

Local implementation: 2026-11-03.

The existing coupled canonical engine remains responsible for complete operating studies, including cost-plus/revenue-percentage coupling and financial reconciliation. When that calculation has unresolved inputs, `backend/orchestration/incremental_economics.py` evaluates independent revenue lines and operating expense cells with the same canonical equations.

## Dependency behaviour

- Explicit-price revenue needs the commercial method, source quantity, operating schedule, sale fractions and net price. It does not require equipment pricing, CAPEX, utility duty or labour budgets.
- Cost-plus prices remain pending when complete operating costs are unavailable. They are never reported using a placeholder zero price.
- Individual invalid material, utility, labour, allowance and factor inputs produce pending records. Other valid inputs still calculate. Failed items are rolled back so they do not retain a duplicate-charge ownership claim or leave a half-applied expense.
- Capital-dependent factors wait for their cost bases; revenue-dependent factors use resolved annual revenue only. A partial income subtotal is not passed off as complete revenue for dependent cost factors.
- Missing operating hours block throughput/energy-dependent cells, while fixed annual labour and other valid annual expenses remain available.
- Every result distinguishes complete totals from known subtotals. Pending costs are excluded from known subtotals, not set to zero. Investment metrics and complete free cash flow remain null/pending when required inputs are unresolved.
- Fixing an input and rerunning Python recomputes affected revenue, expense factors and finance without another AI request. Complete studies continue through the existing canonical financial handoff.

## Presentation and delivery

Revenue, OPEX and TEA overview show independent available results. Partial OPEX uses “Known cash OPEX subtotal”, with pending inputs accessible in the explorer. The financial page can show known operating-year inputs without fabricating NPV, IRR or free cash flow. These rows are operating-year observations, not a complete construction/financial calendar.

Partial reports no longer require a complete DCF. Currency conversion converts known monetary cells and preserves unknown values/metrics. Unresolved comparison-only currency metadata with no nonzero monetary amount cannot block the main study; nonzero unknown-currency money remains an explicit error.

## Charlie local acceptance

Independent scenario: `9789e3c8b4f24f449afbb00c9639d5d0`, derived from the preserved 19-priced Charlie scenario. No AI or outside research calls were made.

- Equipment: unchanged 19/32 priced.
- Revenue: calculated independently from saved user/AI commercial assumptions.
- OPEX: valid lines and known annual subtotals available; unresolved steam duties remain pending.
- Finance: available operating-year revenue/known-cost inputs visible; complete metrics pending.
- Browser verified Revenue, OPEX pending-input inspection, financial partial state and overview known subtotal. GBP view and partial report both return HTTP 200; no page-width overflow at desktop verification size.
- Full backend test result and private snapshots/screenshots are in `outputs/incremental-economics/`. Tests cover missing utility duty, invalid second sale, missing CAPEX, cost-plus dependencies, duplicate expenses, missing hours, partial FX/reporting and price-driven recalculation. Frontend TypeScript and production build passed.

This delivers partial calculation availability, not a claim of complete plant scope or industrial validation. Existing baselines and source assumptions are preserved.
