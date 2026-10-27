# Phase 4 — engineering integration and reference validation

## Supported scope

The API keeps its lightweight dependency set. A separate pinned Python 3.12 environment runs trusted BioSTEAM code locally. No cloud compute upgrade, uploaded code execution or AI calls are required. `make install-biosteam` creates `backend/.venv-biosteam`; `make validate-biosteam` runs a fixed pump → utility-heater water template and writes a portable snapshot plus a mass/energy check record. Numeric overrides can be supplied with `--inputs file.json`; unknown keys/code/import paths are rejected. The worker has a 300-second timeout. Initial scientific-library startup may be slow.

The resolved optional stack is in `backend/requirements-biosteam.txt`: BioSTEAM 2.54.0, Thermosteam 0.54.2, Numba 0.62.1, llvmlite 0.45.1 and CoolProp 6.6.0. Newer CoolProp builds crashed or stalled during this Mac's fluid initialization; 6.6.0 completed the actual run. These dependencies are deliberately separate from the cloud API. Re-test before changing pins.

`export_system` can connect an already simulated trusted single-product BioSTEAM System to FlowValue. It transfers per-operation purchased/installed costs, stream T/P/mass flow/endpoints, annual material/utility costs, production and product price. Operating hours are applied exactly once. Fixed OPEX is an explicit operator input. The older trusted TEA exporter remains available. Multiple boundary products, invalid annual hours, net utility credits, duplicate IDs and double-counted OPEX are rejected rather than silently approximated.

Snapshot v1 remains backward compatible. Additional optional metadata includes streams, project name/classification, kg product basis and assumptions. The import endpoint validates the resulting assessment; legacy snapshots without streams still return an assessment directly. Snapshots with streams include a `streams` field for the dashboard importer. Generic `/api/assessment` requests must exclude that extra stream field.

Imported installed equipment cost is **not** full BioSTEAM FCI/TDC. FlowValue recomputes finance using its disclosed screening conventions. Construction, working capital, coproduct sales and other TEA differences are not reconciled automatically. Built-in template prices, fixed OPEX, heat-utility prices and index 800 are illustrative assumptions, not current market data. The generated example always remains labelled a demo.

## Repeatable validation

`make validate-engineering` and authenticated `GET /api/engineering/validation` compare the engine against seven frozen reference cases in `backend/app/data/engineering_reference_cases.json`: exchanger duty/area/reference purchase cost, pump SI power, vessel geometry/thin-wall thickness, ideal-gas compressor power, quote escalation/quantity, two-year DCF/IRR/payback and zero-discount utilization/LCOP. The dashboard exposes case equations, expected/computed values, tolerances and a downloadable versioned record. Regression tests also prove the report fails if a financial result drifts.

The actual 10,000 kg/h BioSTEAM example produced zero mass imbalance and 2,301,349.66 kJ/h heater duty versus 2,299,000 kJ/h using Cp=4.18 kJ/kg/K: relative difference 0.1022%, within the declared 3% screening tolerance. Files are in `backend/examples/water-heating-biosteam*.json` and the dashboard's downloadable examples. A separate closed-form annuity test reconciles the imported capital, OPEX, NPV and LCOP. This validates transfer/accounting and supported arithmetic; it does not independently validate BioSTEAM's equipment cost correlations.

## Completing native equipment

Each imported operation now has a structured sizing/quote form. Missing sizing and design pressures stay blank; common mechanical/efficiency defaults are visible and editable. Applying requires a written design/quotation basis and explicit input/scope confirmation. Backend BOM validation must pass before the active BOM changes. New numeric edits reset confirmation. The unit's original missing inputs remain visible as historical import notes; active mapping status is shown separately. Review basis is stored in project engineering notes and carried into saved revisions and reports. Reactor models remain shell-only proxies.

## Limits and evidence

These are implementation and bounded-template reference checks, not independent validation of arbitrary commercial plants, supplier quotes, regional prices or code compliance. Additional customer benchmark projects and specialized correlations remain future validation work. Thermodynamics is performed by the installed library, never reimplemented or executed from uploaded scripts.

Primary references: [BioSTEAM getting started](https://biosteam.readthedocs.io/en/latest/tutorial/Getting_started.html), [System annualization/cost API](https://biosteam.readthedocs.io/en/latest/API/System.html), [TEA conventions](https://biosteam.readthedocs.io/en/latest/tutorial/Techno-economic_analysis.html). Other core equations and validity ranges are documented in [calculation basis](calculation_basis.md).
