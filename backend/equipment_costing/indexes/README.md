# Equipment costing methodologies

Source-specific equipment models belong here:

```text
indexes/
  garrett/        equipment modules, source parameters and supporting calculations
  turton_et_al/   reserved equipment modules
```

Future methodologies should have their own package. Source names do not imply a
method is implemented; Turton's current files remain placeholders.

The canonical public interface remains `backend.equipment_costing.registry`.
Shared models, unit conversion, cost-index escalation and equipment totals remain
at the equipment-costing package level. The move changes imports and paths only;
it introduces no new costing equations or financial assumptions.

Revenue, CAPEX and OPEX use the same `indexes/<methodology>/` convention.
