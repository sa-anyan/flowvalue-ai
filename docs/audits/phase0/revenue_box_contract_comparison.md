# Revenue Box contract compatibility review

Reconciliation addendum, 2026-11-10. Production schema unchanged. Source: official roadmap SHA256 `1a9e805750f738b140cdba0d2354eb059654f2328b8ce85aac2c8d037fe56cdb`, paragraph213. Paragraph250/G4 and the preceding Phase4 acceptance criteria also apply.

## Authoritative requirement and its limit

> Every revenue source must preserve your established 13-field structure, including the payment mechanism, workbook quantity source, billable units, payment conditions, operating years and missing inputs.

The document specifies a **count of13** and names six required concepts; it does **not enumerate13 field names, data types or versions**. No exact named13-field definition was identified in the inspected Revenue source/current roadmap. An exact13-to15 field equivalence cannot honestly be certified. This is **BLOCKED pending the founder/engineers' canonical named contract**. A difference in field count alone does not demonstrate lost data or an incorrect schema; the13 logical fields could span nested records. Do not delete two fields to force a count.

## All15 actual CommercialLine fields

Source `backend/revenue/models.py:232`; validation `backend/revenue/validation.py`; serialisation `backend/revenue/snapshots.py`. Field meanings below are observations, not proposed renames.

| Field | Actual contract | Purpose | Compatibility with specified concepts | Limitation |
|---|---|---|---|---|
|id|str, required|Internal line identity|Supports stable identity; not named individually in paragraph213|Does not by itself establish a unique economic payment|
|name|str, required|Human-readable income name|Presentation/interpretation support, not separately enumerated by roadmap|Name similarity cannot prove/dismiss duplicate payments|
|category|str, required|One of six MECE categories|Partial payment-mechanism mapping with rate_period/PaymentYear terms|Category alone does not encode the formula or all conditions|
|payment_id|str, required|Unique commercial payment identity|Supports Phase4 unique-payment acceptance criterion|Two different IDs can still represent overlapping economic consideration|
|quantity_unit|str, required|Billable quantity denomination|Direct mapping to billable units|Price denominator/currency belongs to PaymentYear.rate.unit, not this field alone|
|rate_period|str, required|per_unit / annual / monthly billing|Payment-mechanism and billable-time mapping|Monthly periods and actual contract calendar require separate checks|
|arrangement|str, required|user_confirmed / user_assumption / llm_proposed|Evidence/authority status; not full external user approval|Server revenue_authority approval fingerprint remains separate|
|rationale|str, required|Commercial explanation|Supports payment conditions and analyst reasoning|Free text cannot replace structured clauses or approved terms|
|source_references|tuple[str,...], required|Source evidence references|Part of workbook quantity source/provenance mapping|References are not guaranteed to be workbook cells; follow report IDs and stream/property bindings|
|years|tuple[PaymentYear,...], required|Year-indexed quantities/rates/minima/fixed/availability/escalation/periods|Direct operating-years and structured payment-condition mapping|Years are operating indices; calendar effective/expiry/renewal are not first-class CommercialLine date fields|
|stream_id|str, default empty|Physical source linkage where relevant|Part of workbook quantity source mapping|Blank can be legitimate for fixed/capacity income; contract quantities are not workbook facts|
|included|bool, default true|Income inclusion switch|Scope/review support beyond explicitly named roadmap examples|Inclusion does not independently grant Revenue Box authority|
|fixed_variable_distinct|bool, default false|Explicit fixed/variable payment scope separation|Supports payment conditions and double-counting review|Boolean assertion is not independent proof of two distinct contractual scopes|
|eligibility_basis|str, default empty|Environmental attribute eligibility/ownership assumption|Category-specific payment condition|Does not certify policy/legal eligibility|
|exclusion_reason|str, default empty|Reason for omission|Completeness and exception reporting|Excluded income is not zero-valued evidence of an actual contract|

## Required concept mapping

| Roadmap concept | Actual representation and evidence | Verdict |
|---|---|---|
| Payment mechanism | `category`, `rate_period`, `years`/PaymentYear terms; allowlisted category calculators | PARTIAL semantic coverage; named logical field contract not supplied |
| Workbook quantity source | `stream_id`, `source_references`; draft `stream_key`, property/component selection in `connectors/commercial.py`; report workbook/sheet/cell provenance | PARTIAL distributed mapping; distinction from explicit contractual/manual quantity must survive round trip |
| Billable units | `quantity_unit` plus `PaymentYear.quantity.unit` and `rate.unit`; billing period and periods | Implemented validation; not independent source sign-off |
| Payment conditions | PaymentYear fixed/minimum quantity/payment, availability/escalation/periods; fixed_variable_distinct and eligibility_basis | Implemented clauses, not unrestricted contract interpretation |
| Operating years | `years[].year` matched to common operating schedule; financial calendar outside this record | Implemented; R-01 demonstrates horizon mismatch correctly rejected |
| Missing inputs | Nullable `Assumption.value`; draft `pending_inputs`; returned issues and Revenue Box clarification/approval questions | Distributed representation; no standalone missing_inputs field on CommercialLine |
| Remaining seven of13 logical fields | Not enumerated by authoritative roadmap | BLOCKED; no inferred field names invented |

`PaymentYear` contains year, quantity, rate, fixed_payment, minimum_quantity, minimum_payment, availability, escalation and periods. Each numerical Assumption carries value, unit, rationale, source, uncertainty, status and as_of. These nested fields must not be confused with the15 top-level CommercialLine fields. The Product sales record and LLM draft are also distinct contracts, not aliases of CommercialLine.

Six categories are unchanged: product_sales, processing_services, capacity_availability, infrastructure_usage, environmental_attributes and other_contractual_income. Avoided costs remain separate OPEX savings. Source quotes/intent IDs and server-owned approval fingerprints live outside this dataclass; `arrangement=user_confirmed` or `included=true` must never be treated as a substitute for current user authority.

## Evidence and next controlled decision

The targeted `test_revenue_authority.py` suite was executed with fake inputs/provider boundaries and no paid/cloud access; aggregate counts are recorded in the reconciliation report. These tests do not prove full13-field compatibility, date-expiry handling or arbitrary historical migration. A calendar-year contract such as2027/renewal2028 cannot be certified from integer operating years without its project-calendar and explicit assumptions.

Engineer1 must define payment/billing/year/source/missing-value calculation semantics. Engineer2 must supply a versioned named contract mapping, serialisation/UI/API round-trip and old-version compatibility plan. Founder/engineers must identify the actual13 logical fields and agree additive/backward-compatible mapping before production schema work. No implementation or schema change is part of this assignment.
