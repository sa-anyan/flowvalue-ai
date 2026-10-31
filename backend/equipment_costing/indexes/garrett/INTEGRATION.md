# Garrett workbook integration

This adds a shared Python registry without replacing the existing per-equipment modules. The workbook snapshot contains **51 groups, 154 separately named curves, 498 numeric point candidates**, and missing-point placeholders. All raw readings remain unverified. The supplied workbook is unchanged.

## Usage

```python
from backend.equipment_costing.registry import (
    estimate_cost,
    list_equipment_models,
    list_factors,
)

models = list_equipment_models()
curve = next(c for c in models if c["id"] == "G265-023")
result = estimate_cost(
    curve["id"],
    20,
    size_unit=curve["size_unit"],  # exact source units; never guess conversions
    allow_unverified=True,
)
print(result.status, result.amount, result.issues)
print(result.fit_diagnostics)
```

Without the provisional-data option, graph-derived prices return `needs_review` and no amount. Direct PDF equations work without that option. `formula_estimate` means a supported historical formula calculation, not an industrially validated estimate. Each response retains workbook filename/SHA256, worksheet row/cells, configuration, PDF filename/SHA256 and pages, raw point units/values, fitted reference and diagnostics. Source-coordinate units and returned direct-equation units can differ through explicitly implemented conversions (e.g. thousands of pounds to pounds for adsorbers); both remain in evidence.

Select corrections through `list_factors(curve_id)`. The **172 scalar factor records** cover material, module, installation, design and selected pressure cases. Applying them requires `allow_unverified=True` and a nonempty `factor_basis_confirmation` describing why the original baseline and requested configuration match. This records a caller assertion; it does not automatically verify engineering applicability. Unsupported, ambiguous, formula-based or compound correction factors are retained in page review evidence rather than silently guessed. Missing factors are rejected. Not all PDF factors have executable implementations.

```python
result = estimate_cost(
    "G287-092",
    200,
    size_unit="heat-transfer area, ft²",
    allow_unverified=True,
    factors=("287.material.316_stainless",),
    factor_basis_confirmation="304 stainless baseline changed to 316; service unchanged",
    target_index=640,  # synthetic demonstration; NOT a current published index
    target_period="synthetic scenario",
    target_index_source="user scenario assumption",
)
assert result.historical_amount is not None
```

Module and installation factors are alternative cost scopes and cannot be stacked. Unit-price and already installed scopes cannot receive a total-equipment module/installation factor. Alternative factors in the same category cannot be stacked. Exact curve selection and caller baseline confirmation avoid silently mixing pressure, material, support, driver or agitation variants. Compound recipes requiring several same-category factors are deliberately unsupported.

## Numerical method and limits

- Existing PDF direct equations take precedence, even when graph readings disagree. Duct prices are per foot; conflicting workbook graph prices are not fitted to those equations.
- For graph models, fit `log(C) = a + n log(S)` to non-holdout readings. Where a numerical printed exponent is mapped to that exact configuration, hold n fixed and fit only the reference-price intercept. Otherwise fit both parameters. Repeated identical sizes do not receive extra regression weight; conflicting duplicate prices are rejected. With printed n, one non-holdout reference point can suffice; estimating n requires two distinct sizes.
- Preserve Fit/Holdout labels. Holdout points do not affect coefficients. Diagnostics include observed and predicted prices and `(predicted / observed - 1) * 100` residuals. These are model discrepancies, not confidence intervals. A discrepancy above 20% adds a review flag; this threshold is a diagnostic flag, not a pass criterion or uncertainty bound.
- Agitator bands are fitted separately. Source-limited boiler and column reference ranges are respected. Observed point ranges are not claimed as validated equipment validity ranges.
- Outside the usable interval, calculate the nearest boundary cost and apply `Ctarget = Canchor * (Starget / Sanchor)**n`. A fitted exponent alone does not justify extrapolation. Use a mapped printed n, or explicitly supply an exponent and its justification. All extrapolations remain flagged as unvalidated. Spray/quencher affine equations require a caller-justified exponent outside the sample interval. Existing adsorber boundary assumptions remain unchanged; exact 10,000 lb remains blocked.
- No material conversion, price basis conversion, SI conversion, supplier price, current index or uncertainty distribution is invented. Linear-axis/curved graphs (e.g. centrifuges) can be poorly approximated by power laws and are explicitly provisional.

## Coverage gate

Representative in-range audit: **7 direct-equation configurations; 140 provisional graph configurations; 7 blocked configurations**. Every one of the 51 groups has at least one calculable configuration. This is not support for every possible equipment configuration.

Blocked workbook curves:

| Curve ID | Configuration | Required resolution |
|---|---|---|
| G273-049 | Roll conveyor | No numerical readings; a reference price or points are needed |
| G277-060 | Fluid-bed dryer | Resolve plotted versus actual volume scaling |
| G277-062 | Spray dryer | Resolve volume scaling and missing numerical readings |
| G297-125 | Chemical injection | Workbook flow-times-pressure conflicts with separate source flow annotation |
| G297-126 | Other pumps | Separate diaphragm/rotary/gear/sump readings and units |
| G306-153 | Steam-jet ejector | Workbook multiplies flow by vacuum; source divides by absolute mmHg |
| G306-154 | Vacuum pump | Same capacity-factor unit conflict |

The direct-equation adsorber boundary at 10,000 lb is additionally blocked for that exact input, not for the whole curve. Other invalid units, missing reference data, unknown factors and unsupported extrapolation produce explicit review results with no fabricated amount.

## Files, index adjustment and verification

- `data/review_curves.json`: original values, blanks, formula text/cached values, labels and cell provenance, from all workbook tables used by the engine. Excel formulas are never executed. Auxiliary review notes are evidence, not executable instructions.
- `data/interpretations.json`: scoped printed exponents, source intervals, corrections and unresolved-unit flags.
- `data/factors.json`: scoped numerical scalar factors; transcriptions/applicability remain provisional.
- `data/pdf_review_notes.json`: per-page extracted source text for factor/condition review. OCR text is never executed as a formula. It does not certify that every displayed factor is unambiguously transcribed.
- `tools/import_garrett_review.py`: offline reproducible workbook importer. Runtime uses Python standard library JSON; openpyxl is not a runtime dependency.
- Existing `cost_to_future/escalator.py` was an empty rebuild scaffold. It now applies the explicit same-series ratio, with target period and source required. Historical corrected and final indexed amounts are separate; original uncorrected amount/scope remain in evidence. No live/licensed CEPCI feed is added.
- `reviews/integrated_coverage.json` and `reviews/garrett_integration_report.txt`: per-curve audit and limitations.

Run `python3 -m unittest discover -s backend/tests -v`. All 48 test methods pass, including previous per-equipment tests. New checks cover every group, direct-equation precedence, fitting/holdouts, configurations, units/scopes, blocked cases, boundary anchors, factor applicability, index reconciliation and mutation isolation. Workbook reimport was byte-identical to the saved snapshot. These are implementation/source-data checks, not industrial calibration.

The older `catalogue.json`/`COVERAGE.md` record the earlier formula-only build and remain historical inventories. The new registry and this integration report supersede the statement that graph-only groups have no calculator: those groups now have explicitly provisional graph fits where data permits. No frontend or cloud deployment is included.

## Automatic installation breakdown

Every registered curve now has an `installation_policy`, including explicit missing-source, already-installed and ambiguous-configuration states. The source-factor catalogue now contains 190 scoped records after replacing overly general installation entries with configuration-specific entries.

Canonical `CostingResult` exposes `equipment_cost`, `installation_cost`, and `equipment_and_installation_cost`; these are also in its nested, serializable `installation` record. Installation is `equipment * (F_install - 1)`, not `equipment * F_install`. The combined amount is their sum. The previous `amount` remains the selected purchase/installed/module output for compatibility. No new price basis is silently substituted.

Default factors are the PDF average or printed scalar for the selected configuration. Material/design/pressure corrections affect equipment price first. Module costs remain separate from the three installation components; module factors are not relabelled installation. Applying an explicit source installation factor does not cause a second multiplication when deriving the breakdown.

Autoclaves use 1.60 (source range 1.50–1.70); low-pressure tanks 1.44; open tanks 1.58. Turbine agitators use 1.32 and propellers 1.22. Plate/frame stainless uses 1.53; a matching mild-steel material correction uses 1.70. The spiral exchanger does not inherit the plate/frame factor. For merged mixed/axial pump curve G296-124, set `installation_variant='mixed_flow'` or `'axial_flow'`; the different factors are 1.32 and 1.58. No subtype is guessed from a combined label.

Coverage over 154 curves: 115 have default source-factor policies, 27 have no factor on the relevant page, nine already include installation without a component split, two have unresolved source price scope, and one needs pump subtype selection. Missing factors do not mean zero installation. Air-conditioning and refrigeration tables use the combined source label “Installation, Module factor”; its 1.46 value is used once and that source wording is retained in policy evidence. All policies remain preliminary applicability estimates, not site quotations.

`installation_policies.json` stores factor, source range where given, printed/PDF pages and applicability. `reviews/installation_coverage_report.txt` lists each curve and exclusions. All 67 test methods pass, including independent autoclave arithmetic, installation/material selection, no double counting, physical quantities, mixed index dates, missing factors and totals reconciliation.

## Shared unit conversion and input contracts

The registry now exposes `input_requirements` alongside each of the 154 models. These are declared in `garrett/input_requirements.py`; common unit aliases and conversion constants remain in the sibling `unit_conversion` package. Non-native size units convert before costing, and `estimate_from_parsed_inputs()` accepts typed measurements with source evidence. No pressure-based configuration selection or equipment sizing is inferred. Exact native source-coordinate calls remain compatible. See `unit_conversion/README.md` for usage and unresolved source-basis rules.

## Explicit pressure scenarios

The registry now exposes selectable pressure-factor methods and traceable relative adjustments for supported column/vessel configurations, plus separately labelled agitated-vessel proxies. They are off by default and require typed design pressure, explicit reference pressure basis, provisional-data approval and an applicability note. See [PRESSURE_ADJUSTMENT.md](PRESSURE_ADJUSTMENT.md). The converter still does not select a curve by itself. Pressure-adjusted equipment/installation/combined costs flow through the canonical totals.
