# OpenPyTEA index

Pinned original catalogue and adapted deterministic costing. See
[engineering note](ENGINEERING_NOTE.md), `sources.json`, `LICENSE_NOTICE.md`,
`catalogue_audit.json` and the [integration report](../../../../docs/handover/openpytea-catalogue-integration.md).

Use the canonical `backend.equipment_costing.registry` API. Imported IDs are
namespaced while preserving original keys. Six shared evaluators, no per-model
Python file, upstream financial runtime, automatic parallelisation or escalation.

403 models are available provisionally; 18 incomplete-scope/currency rows remain
visible but disabled. Missing bounds and composite coordinates remain explicit.

Example:

```python
from backend.equipment_costing.registry import estimate_cost
result = estimate_cost(
    "openpytea:belt_conveyor_seider_2013", 20, size_unit="in",
    second_size=100, second_size_unit="ft",
)
```

Both sizes are per unit, not inferred equipment counts. Source-native currency/year
are retained until the canonical cost translator is explicitly invoked.
