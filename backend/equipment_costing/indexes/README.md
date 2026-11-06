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

## OpenPyTEA and additional published models

`openpytea/` contains the pinned MIT-licensed source catalogue and six shared
formula evaluators. Use `source="openpytea"` or a namespaced model ID through the
canonical registry. All 421 pinned rows are inspectable; 403 are provisionally
available and 18 have explicit scope/currency blockers. The full audit, pin and
licence are in that package. Imported mathematical availability is not a claim
of automatic engineering sizing or industrial validation. There is no implicit
parallelisation, installation uplift or upstream escalation.

`additional_models/` retains the separate EPA pH, Turton fermenter and WaterTAP
clarifier configurations. Its existing model IDs remain unchanged. The imported
Turton fermenter row is separately namespaced and retains its upstream provenance.

The matching specialist searches all executable libraries without automatically
preferring a library or a price year; deterministic direct API default remains
Garrett for backwards compatibility. See
[OpenPyTEA integration report](../../../docs/handover/openpytea-catalogue-integration.md).
