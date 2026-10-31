# Canonical OPEX cost register

An offline layer around the existing OPEX engine. No existing equations, factor
tables, CAPEX/equipment calculations, frontend or live integrations are changed.
There is no AI invocation, external research or new runtime dependency.

## Workflow

```text
Shared inputs + expense ownership + alternative methods + evidence
                              ↓
Select one method per expense → review method and coverage
                              ↓
Resolve references, validate evidence metadata, units and ownership
                              ↓
Canonical OpexInputs → existing deterministic OPEX engine
                              ↓
Annual totals + line calculations + input/source lineage
```

`Expense` is the canonical owner of a cost scope. `EstimateOption` groups one or
more existing-engine `Assumption` templates into an alternative estimate.
Only `active_option_id` contributes to totals. Multiple detailed lines may belong
to that one option; alternatives are never additional charges.

For example, one packaging/storage expense can own these required scopes:

- `packaging_storage:packaging`
- `packaging_storage:storage`

Its Garrett option covers `packaging_storage` as a whole. A detailed alternative
must cover both required scopes. A packaging quote alone cannot silently replace
the combined allowance. Declare the expected leaf scopes explicitly when detailed
replacement is intended; the register does not invent a complete scope inventory.
Two expense records cannot own overlapping scopes. Existing-engine checks also
reject overlapping selected lines and circular percentage dependencies.

## Shared facts and numerical bindings

`SharedInput` holds one quantity, price, salary, fraction, annual amount or capital
base with units and evidence. Method templates contain no copied numerical values:
`Binding("quantity", "annual_power")` and `Binding("rate", "electricity_tariff")`
resolve those values immediately before calling the existing engine. The same
input ID can be referenced by multiple estimates. Equal numbers are not assumed
to represent the same business fact; callers choose the correct shared identity.

For monetary inputs `basis` must match the register's currency/price period.
For nonmonetary inputs `basis=None`. Binding contracts:

| Shared kind | Unit | Target |
| --- | --- | --- |
| `annual_quantity` | e.g. `kg/year`, `kWh/year` | quantity × price quantity |
| `headcount` | `FTE` | staffing quantity |
| `unit_price` | e.g. `kg`, `kWh` as price denominator | quantity × price rate |
| `salary` | `FTE/year` as salary denominator | staffing rate |
| `fraction` | `fraction` | percentage rate |
| `annual_amount` | e.g. `GBP/year` | annual allowance or annual revenue |
| `capital_amount` | e.g. `GBP` | named capital base |

`BaseBinding` references a shared monetary input for an existing engine base such
as `fixed_capital` or `annual_revenue`. Base definitions remain those of the
existing OPEX engine; total CAPEX is not silently substituted for Garrett's plant
base. Existing canonical CAPEX adapter outputs can supply these shared values and
their evidence; this package does not rerun or automatically connect CAPEX.

`AnnualConsumption` optionally annualises shared demand and operating hours once.
Supported demand mappings: `kW` → `kWh/year`, `kg/h` → `kg/year`, `t/h` → `t/year`,
`m3/h` → `m3/year`, `L/h` → `L/year`, `MJ/h` → `MJ/year`, `GJ/h` → `GJ/year`.
Hours must be `h/year` and no more than 8784. The caller supplies electrical input
demand, not shaft duty, and accounts for load and efficiency. Other engineering
requirements, unit conversions and annual consumption must come from reviewed
upstream calculations. No expressions are evaluated, units inferred or equipment
sized. Recurring OPEX coverage cannot be replaced with CAPEX or working capital.

## Evidence and uncertainty

`Evidence` records a kind, source reference, ISO source/assumption date, rationale,
uncertainty description and applicability. Supported kinds are `garrett_allowance`,
`user_assumption`, `supplier_quotation`, `engineering_calculation` and
`researched_estimate`. These are provenance labels, not verification or accuracy
ratings. A quote's applicability must address scope/validity; the register does
not independently check suppliers, expiry, local law or price freshness.

Missing active input values, invalid metadata, inconsistent units/currency/period,
unreviewed selections or uncovered scopes block compilation/totals. An unresolved
inactive option is preserved and blocks only that option's comparison. Duplicate
shared IDs or ownership remain structural errors, even for inactive options.

Compiled OPEX inputs retain the consumed shared inputs, their provenance, derived
input dependencies and selected method IDs in engineering-context JSON. Results
remain `calculated_preliminary`, never engineering-verified. Existing engine
category-completeness and exclusion checks still apply. Review of each expense
does not automatically declare the whole category or plant complete.

## Review, comparison and versioning

Public functions are exported from `backend.opex.cost_register`:

```python
calculation = calculate_register(register)
previews = compare_methods(register, "packaging_storage")
snapshot = freeze_register(register)
restored = restore_register(snapshot)

draft = select_method(
    register,
    "packaging_storage",
    "detailed",
    actor="Project reviewer",
    reason="Compare itemized packaging and storage",
    expected_snapshot_id=register_snapshot_id(register),
)
reviewed = review_expense(
    draft,
    "packaging_storage",
    actor="Project reviewer",
    reason="Reviewed both packaging and storage scope",
    expected_snapshot_id=register_snapshot_id(draft),
)
```

`compare_methods` calculates isolated **draft previews** through the same engine,
including downstream cost dependencies. It returns expense costs, scenario cash
OPEX and the change from the active scenario when sufficient inputs exist.
These previews bypass review acknowledgements only, never arithmetic/evidence/
scope validation. They neither apply a method nor become an approved baseline.
Incomplete cases retain explicit issues and unavailable totals/deltas.

`select_method` produces a new unreviewed revision. `revise_input` takes an updated
`SharedInput` (including revised evidence); it flags affected active expenses for
review. Invalidation follows annualisation, capital/revenue bases and percentage
dependencies on OPEX items/categories. Unrelated reviews remain intact. Changing
the labour method also invalidates dependent labour-factor reviews.

All editing helpers require an actor, reason and expected snapshot ID; stale
revision edits are rejected. Frozen objects and JSON snapshots preserve the
original. New revisions contain a parent hash, revision number and change reason.
Schema version 1 snapshots can be stored/reloaded by a future persistence layer.
This is not a database, authentication system, signed audit trail or automatic
history archive: callers must retain snapshots. An actor label is not proof of
identity, and a hash is not a cryptographic approval signature. Direct Python
construction is intentionally available; future application permissions must
enforce review actions at its boundary.

## Limitations and tests

Ownership and coverage use explicit scope IDs. Semantic duplicates hidden behind
different labels, missing engineering scope, quote authenticity and unsupported
market assumptions require human review. This register does not discover expenses
or add a new price source. No live financial or frontend connections are enabled.

Run from repository root:

```sh
python3 -m unittest backend.tests.test_opex_cost_register -v
python3 -m unittest discover -s backend/tests -v
```

The test module includes a complete **synthetic** register, independent expected
cost/delta checks, complete/partial packaging replacements, shared power/hours/
tariff calculations, missing values, evidence/units, ownership, snapshots, stale
edits and dependency review invalidation. It is not industrial project validation.
