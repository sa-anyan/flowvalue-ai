# Calculation basis: Phase 2 and Phase 3

These are transparent preliminary screening calculations. No mechanical design certification or estimate accuracy class is assigned by this engine. Monetary results are USD at the configured CEPCI basis. Temperature-dependent material strength, equipment specification and local installation costs need project-specific review.

## Correlation provenance

The purchased-cost polynomial is `Cp0 = 10^(K1 + K2 log10(S) + K3 log10(S)^2)`. The selected Turton et al. correlations and size bounds are cross-checked against [OpenPyTEA's published equipment database](https://github.com/pbtamarona/OpenPyTEA/blob/main/src/openpytea/data/cost_correlations.csv), whose entries identify Turton et al., *Analysis, Synthesis, and Design of Chemical Processes*, Table A.1. Bailie is a coauthor of the cited textbook; this is one module-cost method, not two independent estimates.

| Model | Size S | K1 | K2 | K3 | Allowed S |
| --- | --- | --- | --- | --- | --- |
| Fixed-tube shell-and-tube exchanger | area, m² | 4.3247 | -0.3030 | 0.1634 | 10–1,000 |
| Vertical vessel / reactor shell | volume, m³ | 3.4974 | 0.4485 | 0.1074 | 0.3–520 |
| Centrifugal pump | shaft power, kW | 3.3892 | 0.0536 | 0.1538 | 1–300 |
| Compressor | fluid power, kW | 2.2897 | 1.3604 | -0.1027 | 450–3,000 |

The module and material factors for exchangers, vessels and compressors follow Table 5 and the appendix of [Cloete et al., Journal of Cleaner Production 275 (2020), 123024](https://re.public.polimi.it/bitstream/11311/1152172/2/11311-1152172%20Giuffrida.pdf). The pump module factors and pressure polynomial are documented in [Lecompte et al., Energies 8 (2015), 2714–2741, Table 6](https://www.mdpi.com/1996-1073/8/4/2714). Numeric coefficients are explicit constants in `costing.py`, not downloaded at runtime.

## Sizing and factors

- Exchanger: `A = 1000 Q_kW / (U_W/m²/K × LMTD_K × F)`. The optional correction factor F defaults to 1. Duty is a positive magnitude. `lmtd()` accepts positive terminal differences and handles the equal-difference limit. Stream tables alone do not determine U or terminal temperatures.
- Vessel/reactor: cylindrical volume, `D = (4 V / (π H/D))^(1/3)`, `H = (H/D) D`. Shell thickness is `max(t_min, P_MPa D / (2 (S_MPa E - 0.6 P_MPa)) + CA)`. Defaults are S=94.4 MPa, weld efficiency E=0.9, CA=3.15 mm and minimum thickness=6.3 mm. This is a thin-wall screening expression, not a code design. Head volume and head thickness are excluded. Ratios t/D above 0.1 are rejected. Reactor costs use a vessel-shell proxy; no agitators, jackets, catalyst or internals are included.
- Pump: differential pressure `ΔP = ρ g H`, hydraulic power `Q_m³/s ΔP / 1000` kW and shaft power `hydraulic power / efficiency`. g=9.80665 m/s². The pressure factor uses the greater of declared design gauge pressure and derived differential pressure. Supply actual discharge/design pressure when suction pressure is above atmospheric. Driver, NPSH and pump curves are excluded.
- Compressor: single-stage ideal-gas isentropic head `k/(k-1) × (8314.462618/MW) × T × (ratio^((k-1)/k)-1)` J/kg. Fluid power is mass flow times head; shaft power divides by isentropic efficiency. The cost curve uses **fluid**, not shaft, power. Real-gas effects, staging, cooling and driver cost are excluded.

Carbon steel Fm=1. Stainless Fm defaults: exchanger 2.7, vessel 3.1, pump 2.3. The **pump stainless factor is an explicit planning assumption**, not a universal textbook constant; replace it with an approved project value. Compressor uses direct module factors 2.7 (CS) or 5.7 (SS), represented as B1=0, B2=2.7 and relative Fm=1 or 5.7/2.7.

Pressure factors are at least 1. Exchangers use 1 through 5 barg and `10^(-0.00164 - 0.00627 log10(P) + 0.0123 log10(P)^2)` above it, limited to 140 barg. Pumps use 1 through 10 barg and `10^(-0.3935 + 0.3957 log10(P) - 0.00226 log10(P)^2)` above it, limited to 100 barg. Beyond those limits an explicit factor override is required.

Vessel Fp is the Turton reference-thickness correction `max(1, ((P_barg+1) D / (2 (850 - 0.6 (P_barg+1))) + 0.00315) / 0.0063)`. This empirical pressure-factor equation retains its own reference steel basis; it is separate from the user-specified mechanical thickness calculation. Diameter range is 0.3–4 m, with pressure restricted to 0–300 barg. Vacuum is unsupported. Compressor Fp=1: pressure dependence enters fluid power; special casing requirements need an override.

Size/diameter extrapolation is rejected unless `allow_extrapolation=true`, in which case warnings remain in the BOM. Overrides are also flagged. No units are silently split into parallel trains.

## Cost meanings and scope

- `base_purchase_cost_usd`: Cp0 at the reference index, per unit.
- `indexed_base_purchase_cost_usd`: Cp0 × CEPCI_current / CEPCI_base.
- `purchased_equipment_cost_usd`: indexed Cp0 × Fm × Fp, per unit.
- `bare_module_cost_usd`: indexed Cp0 × (B1 + B2 Fm Fp), per unit. Material/pressure factors are not applied twice.
- BOM totals multiply each per-unit cost by its quantity. Sizing inputs are **per unit**.

Default CEPCI is **800 / 397 as requested**, a configurable planning basis, not a verified current index. There is no automatic index update or claim that 397 precisely matches every source's year convention. Bare module totals exclude offsites, contingency, land, working capital and owner costs. `/api/assessment` uses this sum as CAPEX per the requested model; use `/api/financial/dcf` for a separately developed total project CAPEX.

## Financial conventions

Inputs are annual USD OPEX, annual production capacity in a user-selected consistent product unit, USD per product unit, and decimal annual tax/discount rates. Production equals capacity times capacity factor. Annual OPEX is already at that utilization and is not scaled again.

Full CAPEX occurs in year zero. Annual revenue and OPEX are constant in real terms, with end-of-year operating cash flows. Depreciation is straight-line over the chosen depreciation life (default operating life), and stops at the end of that life. Un-depreciated book value remaining after the project horizon has no terminal recovery.

`Taxable income = Revenue - OPEX - Depreciation`; `Taxes = max(0, Taxable income) × tax rate`; `Net income = Taxable income - Taxes`; `FCF = Revenue - OPEX - Taxes`. There is no debt, construction schedule, working capital, loss carryforward, inflation, tax credit, salvage or decommissioning value. NPV includes year zero. IRR and DCFROR are identical here; rates can be negative. IRR uses a bracketed [SciPy Brent solver](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.brentq.html) in log(1+r) space. A project without positive returns has null IRR; rates numerically indistinguishable from -100% are also null with a warning.

Both paybacks linearly interpolate the recovery year and return null if recovery does not occur within the project life. LCOP is **pre-tax** discounted capital plus operating cost divided by discounted production; it is not the after-tax break-even selling price.

## Monte Carlo conventions

Default 1,000 runs, seed 42, independent [SciPy uniform](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.uniform.html) multipliers from 0.8 to 1.2 for annual feedstock and utility expense at fixed consumption. These expenses must be supplied as **components** of total variable OPEX. The remainder of variable OPEX is unchanged. Each scenario draws each multiplier once and holds it across operating years, preserving project-level price uncertainty rather than averaging it away across years. All tax/depreciation conventions match the deterministic engine.

P10/P50/P90 are ascending NPV percentiles (P10 is the lower outcome), not exceedance probabilities. Seed, sample count, bounds and probability of positive NPV are returned. Zero exposure produces a constant distribution and a warning. No correlations, price trends or distribution calibration are implied. API sample count is capped at 10,000.


## Export and dashboard conventions (Phases 4-5)

Exports are generated from validated assessment inputs, not uploaded financial results. The dashboard's CSV/JSON uploader only validates/inspects stream data; sizing inputs are explicit. Debounced assessment requests cancel superseded requests, and downloads are disabled until the current scenario has a matching successful result.

Excel contains only formulas in numeric cash-flow cells. Inputs and BOM correlation data feed cash flows and summary metrics. The schedule reserves years 0-100; years after plant life contribute zero, and IRR uses only the active horizon through a bounded OFFSET reference. A one-year project uses the equivalent closing cash flow / initial CAPEX - 1 expression to avoid spreadsheet solver edge cases. The PDF is a two-page snapshot with category-grouped equipment costs; the workbook retains full equipment detail. Monte Carlo histograms return bin boundaries and counts summing to the number of runs. Constant outcomes use a small expanded display range around the common NPV so large-valued constant scenarios remain representable.

Workbook verification includes native LibreOffice recalculation against the API and changes to operating life, discount rate, product price and feedstock OPEX. The workbook is flagged to recalculate on opening; openpyxl does not provide precomputed formula caches. Formula display in lightweight previews can differ from Excel/LibreOffice.

### Imported estimates and policy scenarios

DWSIM ingestion reads stored SI results only. Auto-mapped design pressure is an operating-pressure proxy with an explicit review warning, not a pressure-vessel design certification. Unsupported unit operations are excluded and disclosed as incomplete scope. Reactor costs cover the shell only. No simulator scripts execute.

External `quoted` equipment stores purchased and installed per-unit cost, source and reference CEPCI. Its indexed cost equals quoted cost × target/reference index × capital stress multiplier. Quantity multiplies total costs. Pressure/material assumptions are embedded in the external estimate; changing a material label does not change its price.

Production incentive cash flows are explicit user-confirmed assumptions. Credits apply only in the configured operating-year interval to eligible annual production. Cash-payment treatment adds a nontaxable scenario cash flow; tax-offset treatment reduces tax by min(generated credit, current tax), with no refund or carryforward. Credit expiry can produce nonconventional cash flows; unique IRR is then reported unavailable. LCOP excludes incentives. DCF and Monte Carlo use identical credit timing/treatment, and Excel contains active credit formulas. No 45V eligibility or legislative sunset is inferred from project classification.

## Planned R39 multi-revenue accounting

**Future requirement, not yet available in the existing single-product screening engine.** See [founder example](analyst-workflow-specification.md#natural-language-commercial-opportunity-exploration-founder-example-selling-waste) and [roadmap](product-build-roadmap.md#cross-phase-roadmap--conversational-commercial-opportunities-r39).

Proposed waste/by-product revenue is a separate annual line computed as **saleable volume actually sold × accepted selling price**, with declared product/stream, quantity, unit, currency, date, region, commercial basis and timing. Do not equate production with sales, extrapolate a missing stream yield, or double-count existing food revenue. Track attributable processing, handling, storage and transport expenses separately, and only a supported avoided disposal cost (never twice). Price, conversion or quantity gaps remain unresolved rather than being assigned fabricated numbers.

The same validated deterministic DCF calculates the preview's resulting taxes, cash flows, NPV, IRR and payback without mutating the approved baseline. Multi-product LCOP needs an explicitly defined allocation/product basis, not a hidden by-product credit. Revenue/Scenario/Main dashboard charts, process annotations where the source stream is real, Excel and reports must reconcile to the same scenario revision. Uncalibrated contract probabilities must neither be presented as numbers nor silently applied as probability-weighted revenue; any risk modelling requires an explicit basis and review.

## Modular costing layout — 29 October 2026

Source-specific base prices now belong to `app/engine/equipment_costing/`: the existing Turton reference formula is in `turton_et_al/`, and `garrett/` is an explicitly unimplemented boundary for future reviewed Garrett curves. The previous combined sizing/factors/BOM implementation is retained in `equipment_costing/legacy/screening.py`; `engine/costing.py` only re-exports its existing public interfaces. Existing API calculations and baseline conventions are unchanged.

Generic index-only translation is separate: `app/engine/price_escalation/escalator.py` takes a sourced `EquipmentPrice`, its original index and an explicit compatible target index. Missing original indices or differing index series/normalization bases are rejected. Currency and price scope are retained; there is no automatic FX, sizing or installation adjustment, live-index selection, or implicit assumption that a target value is today's price. The existing rights-aware index catalog moved to `price_escalation/catalog.py`, with `engine/indices.py` retained as an import facade. See `app/engine/equipment_costing/README.md` for interfaces and limitations.
