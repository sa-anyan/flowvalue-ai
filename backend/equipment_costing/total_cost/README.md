# Equipment cost totals

`calculator.py` routes mapped parser records through the existing canonical registry, preserves each calculation and parser source, extends prices by quantity, and produces reconciled equipment-cost subtotals.

```python
from backend.equipment_costing.total_cost import calculate_total_cost

result = calculate_total_cost(
    [
        {
            "equipment_tag": "HX-101",
            "curve_id": "G287-092",  # explicit reviewed configuration mapping
            "size": 200,
            "size_unit": "heat-transfer area, ft²",
            "quantity": 2,
            "quantity_unit": "item",
            "parsed_source": {"worksheet": "Equipment", "cells": "A5:D5"},
        },
    ]
)
print(result.total, result.status)
```

The parser/engineer must supply the exact model configuration, size and units. Equipment tags alone do not determine equipment type, material, pressure or size; there is no automatic fuzzy mapping or invented sizing. Registry correction-factor, provisional-data and index options go in each item's `costing_options` mapping. Existing per-equipment formulas and graph fits remain in their original modules.

Whole-equipment prices default to one item. Per-foot, per-area, per-volume, per-height and per-tray prices require an explicit physical quantity and matching unit. Units are not converted implicitly. Unsupported scopes and invalid quantities remain review items.

Duplicate equipment tags are rejected to prevent double counting. Missing models, invalid inputs and blocked calculations remain visible in `result.equipment`. Partial subtotals are retained, but `result.total` is unavailable until every supplied item is resolved and all currencies, index/date bases and resulting cost scopes match. Purchased, installed, module and building scopes remain separate. Provisional calculations make the resulting total provisional.

This is a Python batch-costing layer. It does not create a frontend page, restore the old parser/application, automatically classify equipment, or calculate whole-plant CAPEX. Future parser/frontend adapters can call this function using the documented input contract. All original calculation evidence remains in each line's `calculation`; parser evidence is retained as `parsed_source`.

## Canonical equipment / installation breakdown

The result now exposes these explicit totals, with matching fields per item:

```python
print(result.equipment_cost_total)
print(result.installation_cost_total)
print(result.equipment_and_installation_cost_total)
print(result.cost_breakdown_status)
print(result.installation_issues)
```

`component_subtotals` groups all three values by currency and index/date basis. Any component that cannot be fully determined remains `None`, with the missing equipment tags retained. An equipment-only total can remain available when installation is unknown. Already-installed source prices can contribute a combined amount but do not invent separate equipment/installation amounts. Physical quantities multiply all components consistently. All three components receive the same index escalation.

The previous `total`, `subtotals` and line `amount` retain their original source-scope meaning for compatibility; **use the three explicit fields above for the equipment/installation report**. They do not add a module factor to installation a second time. `cost_breakdown_status` is provisional whenever source-factor estimates are used, even if the original equipment-only calculation uses a direct formula. No frontend is present in this clean rebuild; these are serialized Python result fields ready for a future page.

## Shared unit conversion

Non-native size units pass through the canonical registry's shared converter. Use `costing_options['unit_context']` for explicit source gallon/ton or pressure/gas conventions. Physical quantities such as duct length also convert through the same engine; `quantity_conversion` retains their original units and source. There is no repeated conversion arithmetic in this aggregator.
