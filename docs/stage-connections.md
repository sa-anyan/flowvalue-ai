# Deterministic stage connections

The founder's Flowvalue workflow describes editable equipment decisions followed by connected economics. These repairs retain the existing Python engines and assumption contracts; they do not generate engineering inputs or change costing equations.

The tested route is workbook decoding → canonical stream/equipment register → source-backed sizing → shared unit conversion → per-unit equipment costing and quantities → Garrett CAPEX → coupled consumption/OPEX/revenue → annual financial ledger.

Repairs:

- `BalanceReport` accepts the extraction date emitted by the ingestion boundary.
- Source-derived interpretation IDs and their notes are stable across sorted JSON save/reload. The interpretation version changes so old cached reviews are not mixed with the new identity algorithm. Saved assessments are not migrated or overwritten.
- Sizing accepts both scalar named-unit parameters and typed parameter records already supported by the engineering calculator.
- Operating-study factors pass explicit `override` and `override_reason` through to the canonical OPEX assumption. Existing range validation still applies; an undocumented override is not accepted.

`backend/tests/test_stage_connections.py` generates an original synthetic workbook and exercises the real parser, Garrett tank costing, CAPEX, OPEX, revenue, financial engine, saved edits and baseline replay. It checks two-unit quantities, source preservation, 20 operating years, year-by-year reconciliation, and propagation of changed hold-up and utilisation. Network and AI proposal calls are forbidden in the test.

The Charlie diagnostic additionally exercised its 32 parsed equipment records in three deterministic scenarios using an isolated dummy model registry and complete synthetic inputs. This demonstrates connectivity, not engineering accuracy, appropriate equipment selection, market prices or model completeness. No test values are installed as production defaults. Explicit VCOP/FCOP outputs remain separate unfinished functionality, outside these connection repairs.
