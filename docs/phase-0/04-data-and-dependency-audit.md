# Phase 0 · Data and dependency audit

~~~mermaid
flowchart LR
  IN["Workbook bytes, description, Revenue Box"] --> ENG["Engineering report and review"]
  ENG --> EQ["Unique equipment, sizes, cost lines"]
  EQ --> CAP["CAPEX and capital basis"]
  ENG --> OP["OPEX independent inputs"]
  ENG --> REV["Revenue plus approved commercial terms"]
  REV --> OP
  CAP --> OP
  CAP --> FIN["Annual finance ledger and metrics"]
  OP --> FIN
  REV --> FIN
  FIN --> VIEW["Cashflow, TEA summary and exports"]
  REV -. "fallback revenue when ledger absent" .-> VIEW
~~~

The conceptual engineering-to-economics sequence does not imply CAPEX or OPEX is always required to run Revenue. The coordinated order is equipment → CAPEX → Revenue → OPEX → Finance. OPEX consumes capital and sales/savings as optional bases and can run partially. [Registry](../../backend/blocks/registry.py) · [Group workflow](../../backend/blocks/stage_workflow.py#L32).

| Concept | Current authority and representation | Boundary finding |
|---|---|---|
| Project | Assessment ID, revision, workbook BLOB/hex, JSON state, source SHA, descriptions, plan and stage envelopes. [Local Store](../../backend/orchestration/store.py#L16), [cloud schema](../../backend/cloud/schema.sql). | Optimistic revision guards writes. Domain schema is embedded in JSON. Row ownership and revision are storage keys. |
| Measurements and streams | [BalanceReport, Entity, Evidence, Connection](../../backend/ingestion/balance/models.py#L14) and [build_register](../../backend/ingestion/engineering_register.py#L96). Report keeps original units, normalized observations, identifiers, property, component context and references. | IDs identify extracted entities or observations in a scoped report. Duplicate printed names, repeated blocks and different source types need mapping rules. Stream link presence does not prove flow balance or topology completeness. |
| Equipment | Extracted report entity plus equipment plan, alias/duplicate reviews, editable physical assets, sizing and pricing results. [Resolution](../../backend/equipment_resolution) and [equipment runner](../../backend/blocks/equipment/runner.py#L78). | Preserve distinction between report key, normalized equipment tag, physical asset ID, duplicate alias, component and quantity. Tag-keyed scenario outputs can collide if distinct assets retain a tag. [Scenario extraction](../../backend/scenarios_and_uncertainty/monte_carlo/engine.py#L60). |
| Schedule | Financial operating years/ramp in operating economics plus explicit analysis schedule/cashflow schedule, first-operation timing and year-indexed mappings. [Schedule editor](../../backend/blocks/cashflow/schedule.py), [Cashflow view](../../backend/blocks/cashflow/view.py#L40). | Project year, construction year and operating year are different coordinates. Saved configurations have legacy fallbacks. A single authoritative timeline contract is missing. |
| Assumptions, evidence and approvals | Workbook `Evidence`, plan and assumption register, locks, reviewed proposals and stage-specific approval fingerprints. [Service edit](../../backend/orchestration/service.py#L475), [engineering approval](../../backend/blocks/stage_workflow.py#L18), [Revenue authority](../../backend/revenue/authority.py#L28). | Approval target differs by stage. Draft/reviewed/source/user/synthetic statuses must remain explicit. Completeness of numerical coverage is separate. |
| Costs | `EquipmentCostTotal`, `CapexResult`, year-indexed `OpexResult` with typed basis and decimal serialization. [Equipment totals](../../backend/equipment_costing/total_cost/calculator.py), [CAPEX models](../../backend/capex/models.py#L139), [OPEX models](../../backend/opex/models.py#L183). | Scope and index basis affect additivity. Frontend JSON dictionaries can display a payload lacking cost scope unless the view checks it. |
| Commercial contracts and savings | [Revenue models](../../backend/revenue/models.py#L202) for typed annual terms, `CommercialLine`, `AvoidedCost` and `RevenueResult`. Rate study UI maps into shared plan. | Per-line currency/date and category-specific evidence must survive conversion. Product, contract and savings identities use different semantics. |
| Results and history | [Execution views](../../backend/blocks/execution.py#L168) and [finance engine](../../backend/financial_modelling/engine.py#L24). Named snapshots and reopen-as-derived assessment [Store.load](../../backend/orchestration/store.py#L93). | Several JSON projections coexist. Historical result, edit baseline, UI snapshot, canonical payload and scenario are not interchangeable. Current checkout has no demonstrated schema-migration matrix across older saved versions. |

The onboarding diagnostic described a strict report mismatch for extracted_on. At this HEAD, [BalanceReport](../../backend/ingestion/balance/models.py#L84) declares that field, and direct model introspection confirmed its presence. That historical schema finding is not carried forward as a current defect. Provenance and mixed-basis reconciliation still need coverage.

### Propagation and contracts

[Execution._inputs](../../backend/blocks/execution.py#L55) selects the inputs per stage. [input_fingerprint and fresh](../../backend/blocks/execution.py#L125) combine the slice with upstream output hashes. Edits refresh statuses. When a CAPEX or Revenue output changes, OPEX also considers its optional basis hashes. Financial results require fresh CAPEX, OPEX and Revenue. Store writes are revision checked. Engineering and Revenue approvals are content fingerprints. Recalculate via an explicit run or coordinated group. Partial/stale UI and persisted prior receipts need to remain distinguishable.

Potential identity inconsistency is structural, rather than evidence of duplication in a real assessment. Do not infer conversion from similar unit labels. Flow, count, standard gas volume, mass basis, cost scope and price periods need typed context and evidence. Cost comparisons and exports must carry the same source revision.

| Shared P2 contract | Required semantics and initial proof |
|---|---|
| Source observation and entity reference | Stable source hash, parser version, sheet/cell/coordinates, observed value and units, canonical units, observation and entity IDs, quality/conflict status. Retain raw values and lineage through serialization. |
| Equipment identity and sizing request | Physical asset ID plus report key and normalized display tag. Explicit alias/spare/train relationships and approved quantity. Method, typed parameters and evidence IDs. Round-trip same-tag distinct assets and aliases. |
| Monetary amount and scope | Decimal amount or explicit missing status, currency, date, index and value, source/target basis, scope and priced coverage. Refuse aggregation across unmatched bases and preserve allowed translation evidence. |
| Timeline and revenue approval | Project and operating year mapping, ramp and hours owners, stable line identity, authority and approved price basis. Deterministically invalidate only affected approvals and stages. |
| Revision and runner receipt | Source/plan/schema/method versions, input/output fingerprints, approval ID and status/completeness. Report and snapshot consume the same receipt. Golden parity between stage and scenario for the same input. |

[Ownership](07-two-engineer-development-plan.md) · [Requirements R09–R12](08-requirements-register.md)
