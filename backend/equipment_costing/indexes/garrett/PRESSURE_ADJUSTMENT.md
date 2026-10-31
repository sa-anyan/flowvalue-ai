# Selectable pressure adjustments

The canonical registry supports explicit pressure scenarios without changing the saved/native curve. No pressure adjustment is applied by default.

## Available choices for a future value-engineering dropdown

Use `list_pressure_methods(curve_id)` or a model's `pressure_adjustment_options`:

1. `native_curve`: keep original curve pressure. Map this selection to `pressure_adjustment=None`; it does not claim that the reference curve meets a newly entered design pressure.
2. `garrett_power`: Garrett's printed vertical-column pressure relationship, F(P)=(P/50 psi)^0.44.
3. `garrett_table_linear`: Garrett's vertical-column pressure table, with piecewise linear interpolation in psi. The table is source data; linear interpolation is an explicit implementation assumption.

For agitated tanks, labels include **agitated-vessel proxy**. Garrett does not instruct applying the column factor to these tanks. The user must select that approximation and record an applicability note. The pressure-vessel chart on printed p.298 explicitly refers to column pressure factors; the separate vertical-column method on p.268 uses its own source basis. No proxy is offered for an open tank or unrelated equipment.

The relative multiplier is **F(target) / F(reference)**, not F(target) alone. The graph cost already includes its reference pressure. Installation and module factors must not apply pressure again. Selecting a discrete pressure factor and a relative pressure scenario simultaneously is blocked.

## Example: 100 source-gallon autoclave at 105 bar gauge

```python
from backend.equipment_costing.registry import (
    estimate_cost, PressureAdjustment, list_pressure_methods,
)
from backend.equipment_costing.unit_conversion import Measurement

print(list_pressure_methods('G258-004'))

result = estimate_cost(
    'G258-004', 100, size_unit='gal', allow_unverified=True,
    pressure_adjustment=PressureAdjustment(
        method='garrett_power',
        target_design_pressure=Measurement(
            105, 'barg', {'source': 'user design-pressure scenario'},
        ),
        reference_pressure_basis='gauge',
        applicability_note=(
            'Screening scenario: apply vertical-vessel pressure-factor ratio '
            'to the same-volume agitated autoclave. Proxy requires review.'
        ),
    ),
)
print(result.equipment_cost)
print(result.installation_cost)
print(result.equipment_and_installation_cost)
print(result.evidence['pressure_adjustment'])
```

On the current provisional graph-price baseline, this explicit **gauge-pressure scenario** gives approximately USD 47,385 equipment, 28,431 installation and 75,816 combined, early 1987 / CE Index 320. The table-interpolation alternative gives approximately USD 47,509 / 28,506 / 76,015. These differences are methodological estimates, not validated supplier-price uncertainty bounds. Bare “105 bar” without an explicit pressure basis is blocked; these examples do not resolve that ambiguity for the user.

## Evidence and limitations

- Base configurations and reference pressures remain explicit: G258-004 1500 psi, G258-005 600 psi, G258-006 300 psi, G258-007 50 psi, G268-031 50 psi, G298-132 250 psi. The last uses interpolation to establish its reference factor when the table method is selected.
- The source is Garrett Appendix 1, printed p.268 / PDF p.18; its PDF identity is inherited in the costing result. The vessel cross-reference is printed p.298 / PDF p.48. The source psi label is not independently treated as gauge or absolute; `reference_pressure_basis` is a recorded caller interpretation.
- Target design pressure is a typed measurement with source provenance. Gauge/absolute conversion needs explicitly supplied atmospheric pressure. Operating pressure is never substituted for design pressure. If parsed design pressure is also supplied, it must agree with the scenario's target after conversion.
- The table covers 50–5000 psi. This envelope is also a screening guard for the power relationship, **not a source-validated applicability interval for that equation**. Table extrapolation is rejected. Power-law extension beyond the guard requires `allow_extrapolation=True` and `extrapolation_justification`; nearest-boundary factor, extrapolation and assumption are recorded.
- Applying this correction does not select construction, determine wall thickness, validate agitation seals or jacket ratings, establish mechanical feasibility, or certify vessel design.
- The installation factor remains the selected equipment-family factor, held constant as a screening assumption across the pressure scenario. It is not independently calibrated versus pressure. Pressure modification reaches equipment price first, then installation/module calculations and the unchanged index-ratio adjustment. All three totals and quantity extension reconcile.
- The value-engineering UI can show method, formula/table basis, native and target pressures, unit conversion, factors, ratio, source pages, proxy status, interpolation/extrapolation assumptions and native-versus-preview costs. Applying a preview must be explicit; the current function does not mutate baseline/source data.

## Verification and UI status

97 automated test methods pass, including 12 new pressure-method tests: independent power/table arithmetic, exact nodes and interpolation, native identity/restoration, explicit pressure bases, unsupported/open configurations, duplicate pressure corrections, extrapolation guards, parsed-pressure conflicts, all three totals and index/quantity reconciliation.

This clean rebuild contains only `frontend/AGENTS.md`, not an executable equipment or value-engineering page. Dropdown metadata and calculation evidence are implemented in Python; no live frontend page or cloud deployment was added or claimed.
