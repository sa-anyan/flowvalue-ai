# Source-specific equipment costing

Each source owns its original/reference-basis pricing method. No module silently selects a different author or escalates a base price to today's price.

- `garrett/`: 51 separately named Python modules, one per source catalog/chart group, with uppercase headings, catalog IDs and both source references. Explicit unimplemented boundaries for Garrett's equipment charts. The names/source references and 320 historical basis remain in the equipment catalog. No curves have been invented or digitized.
- `turton_et_al/`: separate `heat_exchangers.py`, `vessels.py`, `pumps.py` and `compressors.py` modules own the existing FlowValue Turton coefficient table and reference-purchase-price calculation, extracted without changing the coefficients. `estimate_base_price(equipment_id, kind, size)` returns a traceable `EquipmentPrice`; size units/ranges are declared in `CORRELATIONS`. It does not size equipment or add installation, material or pressure factors. The reactor-shell proxy is not automatically selected for new generic inputs.
- `models.py`: shared price envelope: amount, currency, equipment ID, scope, source/method, original index and notes. An explicit zero is distinct from an unknown amount.
- `legacy/screening.py`: prior combined sizing/material/pressure/BOM engine retained for existing routes and saved projects. It still calls the same Turton reference formula. Its existing defaults and assumptions are unchanged.

`app/engine/costing.py` is now only a compatibility import facade. Existing API routes remain on the legacy engine until a separately reviewed method-selection migration. The old functionality has been moved aside, not deleted or globally disabled.

Add future independently reviewed methods as separate modules here, with source identity, valid units/ranges, exclusions and tests. Garrett methods must not fall back to Turton. A missing method raises an explicit unsupported result.

## Separate price escalation

`../price_escalation/escalator.py` accepts any `EquipmentPrice` with an explicit original index basis and a compatible target `CostIndex`. It never derives an index from an amount or year, converts currency, resizes equipment or silently adds installation.

```python
from app.engine.equipment_costing.models import EquipmentPrice
from app.engine.price_escalation.models import CostIndex
from app.engine.price_escalation.escalator import escalate_price

original = EquipmentPrice(
    equipment_id="V-101",
    amount="100000",
    currency="USD",
    scope="purchased",
    method="user_supplied_price",
    source_reference="Example source: Prices!B2",
    reference_index=CostIndex(
        series="CEPCI",
        basis="1957-1959=100",
        value=320,
        period="1987",
        source="Illustrative original index assumption",
        status="assumption",
    ),
)
target = CostIndex(
    series="CEPCI",
    basis="1957-1959=100",
    value=800,
    period="2026",
    source="Illustrative target assumption, NOT a verified current index",
    status="assumption",
)
result = escalate_price(original, target)
# result.adjusted_amount == Decimal("250000")
```

The caller supplies the target period and index; there is no implicit 800 or live feed. Both series and normalization basis must agree. Decimal arithmetic preserves the ratio without silently rounding to cents. Original inputs and source references are preserved. A supplied `verified` status is a metadata assertion, not independent verification by this function. Results remain index-adjusted estimates, not vendor quotations. Parsing a price without its original index leaves escalation blocked.

## Index catalog

`../price_escalation/catalog.py` contains the existing rights-aware index catalog validation; `app/engine/indices.py` is a compatibility facade. Stored records stay in `app/data/cepci.json`. Existing catalog rights restrictions remain in effect. The arithmetic function itself neither obtains redistribution rights nor selects/publishes restricted records; callers must enforce rights before exposure.

No original workbook formulas, new dependencies, third-party source code, model calls or licensed curve data were added for this refactor.

## Canonical author packages

Author names are Python packages, not monolithic files. Each package's `__init__.py` is the canonical explicit method registry/dispatcher and preserves the previous import interface. Garrett's `METHOD_MODULES` maps all 51 catalog IDs to separate modules. A source chart can cover several subtypes; splitting those into additional calculation methods requires independent scope/range evidence. No extra Turton equipment methods are implied beyond the existing four.

Each equipment file has a prominent module heading and implementation status. Shared Turton arithmetic/result construction lives in `_common.py`; equipment-specific constants live only in the corresponding equipment module. The previous single-file sources are retained as non-executable `.txt` records under `legacy/` for review. Legacy screening continues importing the Turton package through its unchanged public interface. Price escalation remains a separate package.
