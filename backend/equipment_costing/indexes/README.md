# Equipment costing methodologies

Source-specific equipment models belong here:

```text
indexes/
  garrett/        equipment modules, source parameters and supporting calculations
  nottingham/     CEEDG501 equipment equations + explicitly unverified chart points
  turton_et_al/   reserved equipment modules
```

Future methodologies should have their own package. Source names do not imply a
method is implemented; Turton's current files remain placeholders.

The canonical public interface remains `backend.equipment_costing.registry`.
Shared models, unit conversion, cost-index escalation and equipment totals remain
at the equipment-costing package level. The move changes imports and paths only;
it introduces no new costing equations or financial assumptions.

Revenue, CAPEX and OPEX use the same `indexes/<methodology>/` convention.

## Available executable cost sources

The canonical registry now supports `source="garrett"`, `source="nottingham"`, and `list_equipment_models(source="all")`. The `/api/catalogue` endpoint exposes both. Select a model by exact `curve_id` and native `size_unit`; `N501-` identifiers route to the Nottingham index in the orchestration pipeline. Do not confuse Nottingham **equipment** costing here with its separate CAPEX Lang/factorial methodology in `backend/capex/indexes/nottingham`.

Nottingham uses historical GBP price bases and pinned ONS CPI proxy plus the existing pinned FX snapshot for common USD totals; see `nottingham/README.md` for formula details and scope caveats. Not all items have supported models and not all historical prices include installation.
