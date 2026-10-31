# Offline CAPEX estimation engine

This package implements separate, deterministic capital-estimation methodologies. **Garrett is the default.** The engine is callable for local studies/tests but has no routes, scheduler, frontend binding, automatic project writes or live CAPEX connection. The existing equipment-costing engine is not modified.

## Models and common API

```python
from backend.capex import (
    CapexInputs,
    EquipmentCost,
    WorkingCapital,
    list_models,
    get_model,
    get_factor_ranges,
    calculate_capex,
)

print(list_models())
print(get_model())  # Garrett metadata
print(get_factor_ranges("garrett", "solids"))

# Synthetic equipment cost, not a textbook equipment quotation.
inputs = CapexInputs(
    equipment=(
        EquipmentCost(
            tag="E-101",
            purchased_cost="1000000",
            quantity=1,
            currency="USD",
            period="early 1987",
            index_series="CEPCI",
            index_value=320,
            delivery_basis="delivered",
            provenance={"source": "synthetic demonstration"},
        ),
    ),
    process_type="solids",
    factor_selection="minimum",  # explicit scenario choice, not a recommended design
)
result = calculate_capex(inputs=inputs)  # default model_id='garrett'
print(result.fixed_capital, result.working_capital, result.total_capex)
```

Registered IDs:

- `garrett`: independent detailed factorial model, classifications `solids`, `mixed`, `fluids`.
- `nottingham`: detailed factorial profiles for `solids`, `mixed`, `fluids`.
- `nottingham_lang`: alternative overall method, also supporting `bioprocessing` and `water_treatment`.

The existing Turton package remains an empty placeholder and is not advertised as available. Model selection only changes `model_id`; all implementations accept the same `CapexInputs` contract. Metadata/ranges include source reference, file identity/hash, source page, calculation base, formula and applicability. Nottingham profile values are fixed published percentages, so their numerical minimum and maximum are equal; the three categories are not treated as a min/max range.

## Garrett source and installation treatment

Source: Donald E. Garrett, *Chemical Engineering Economics*, Chapter 3, principally **Table 3-4 printed p.29 / PDF p.41**, with contextual text in printed pp.26–41. Factors were checked against the rendered original table. Working-capital and startup guidance was checked on printed p.41 / PDF p.53. The source identity is retained in each factor definition.

Direct allowances use purchased equipment as their base. Construction/engineering, contractor fee and contingency can instead use the source's optional **direct-cost subtotal** percentages by selecting `indirect_basis='direct_costs'`. These are alternative bases, not extra charges. All three use the same chosen subtotal before indirect costs; they do not compound sequentially or reference the final plant total.

Garrett states that whole-plant installation is included through piping, electrical, foundations and other direct categories (pp.29–30). `equipment_installation` is therefore an explicitly **non-additive embedded line**, with no invented min/max. The approximate 63% average mentioned on p.30 is recorded as contextual metadata, not applied again. Equipment-specific installation and module totals are never used as the factorial starting base.

The table's land range includes zero; the prose's 3–10% allowance when new land is bought is retained as an alternative condition. Existing land/facilities need explicit exclusions or selected factors rather than inference from natural-language descriptions. A model does not automatically classify process descriptions.

Garrett does not provide a complete separate numerical direct-factor profile for each of solids/mixed/fluids. All share the published ranges, while their process characteristics inform user judgement. The source's usual overall multipliers and Lang references are stored as comparison metadata in the Garrett module, not additional charges or mandatory clamps. Missing classification/factor selections return review issues. `midpoint` is an explicitly selected arithmetic scenario, not a source-authored typical value.

## Nottingham source and calculation choices

Source: **CEEDG501 Cost Estimation Rev 3**, p.5. The revision history identifies Rev 3 (7 November 2017), while the body footer still says Revision 2 / September 2017; both facts are recorded. Its page-5 table is an embedded image and was visually verified rather than relying on extracted text.

`factor_basis_mode='published_table'` is the default. It applies the printed rounded percentages of **delivered purchased equipment** and exactly reproduces the source's reported profile totals.

`factor_basis_mode='relationships'` instead uses the table's approximate relationships: contractor fee at 5% and contingency at 10% of **direct plus engineering/construction cost before those two charges**. Working capital defaults to the stated 15% of total capital investment, solved as `fixed_capital * f / (1-f)`. These exact relationships differ slightly from the printed rounded percentages. Both bases/formulas are retained in factor metadata; the implementation does not pretend their results are identical.

Independent source checks with a synthetic delivered-equipment total of 1,000,000 reproduce total investment of 4,550,000 (solids), 4,870,000 (mixed) and 5,690,000 (fluids) in published-table mode. These are arithmetic checks, not current plant quotations.

The Nottingham table does not individually publish every Garrett category. Unlisted insulation, foundations, environmental, painting/safety, offsite and startup entries remain metadata with unavailable coefficients and `not_separately_published` line status. They are not assigned Garrett factors, automatically assumed included, or declared to have zero actual cost. The reported startup amount of zero means **no separate startup charge was added in reproducing that profile**, not proof of zero startup requirements. Review scope before relying on the aggregate as a complete project estimate.

Lang factors are a separate overall installed-cost method. No detailed factorial charges are added on top. Lang working capital requires explicit assumptions; it is not silently imported from the detailed table. The document's separate section 5 (p.12) supports 3–6 months of operating costs.

## Working capital and output conventions

`WorkingCapital` supports:

- `model_default`: Garrett plant-cost fraction using an explicitly selected range value; Nottingham detailed published-table or relational convention according to selected mode; Lang needs monthly operating-cost assumptions.
- `plant_fraction`: a selected fraction of core plant cost.
- `annual_opex_fraction`: Garrett's alternative manufacturing/annual operating-cost basis; annual OPEX must be supplied.
- `installed_equipment_fraction`: Garrett’s rough p.41 alternative, using 50% of an explicitly supplied `installed_equipment_cost`; this is a working-capital basis only, never a replacement for the purchased-equipment CAPEX base.
- `total_investment_fraction`: `fixed_capital * f / (1-f)`; the Nottingham detailed nominal fraction is documented, other-model use requires an explicit rationale.
- `months_opex`: `annual_opex * months / 12`; Nottingham p.12 supports 3–6 months; other/out-of-source choices require a user rationale.
- `absolute`: itemized/user amount with rationale.
- `excluded=True`: explicit exclusion with rationale.

Custom working-capital bases/amounts use `WorkingCapital`, not an incompatible published-table selector. Do not provide conflicting working-capital overrides through several paths. OPEX and absolute monetary assumptions must already use the common currency/date basis of the equipment; this package does not automatically adjust or convert them.

Stage definitions are explicit:

- `purchased_equipment`: quantity-extended canonical purchased cost.
- `direct_costs`: purchased equipment plus selected direct allowances (or the Lang overall installed-cost output).
- `indirect_costs`: engineering/construction and the applicable fee/contingency charges.
- `plant_cost`: direct plus indirect, before additional offsite/startup/working capital.
- `fixed_capital`: plant cost plus additional offsite facilities.
- `startup_expenses`: separate capitalized startup allowance.
- `total_capex`: fixed capital + startup + working capital.

For Garrett, offsite and startup fractions use **core plant cost**, keeping the “additional” factors outside their denominator. This interpretation avoids self-referential capital bases and is disclosed in result evidence. Nonzero offsite allowances require a statement confirming that facilities are not already covered in utilities/buildings/environmental or other scope. Excluded categories remain visible with their reason. Missing bases/factors leave amounts unavailable and suppress total CAPEX; they are never silently changed to zero.

Inputs may supply `selected_factors`, explicit `Override(fraction=... or amount=..., rationale=..., source=...)`, and `exclusions`. A normal selection must fit the published range. An evidenced user override can depart from it, retaining the published range and user rationale. Unknown, conflicting, cross-model and embedded-category charges are rejected. Zero overrides are preserved.

All monetary arithmetic uses Decimal. Result dataclasses can be serialized with `dataclasses.asdict`; use an explicit Decimal-to-string policy when producing JSON rather than silently rounding early.

## Canonical connector — prepared, not activated

```python
from backend.capex.connectors import prepare_capex_inputs

prepared = prepare_capex_inputs(
    existing_equipment_total,
    process_type="solids",
    delivery_basis="delivered",
    factor_selection="minimum",
)
# This only prepares inputs. A future explicitly selected workflow may call:
# result = calculate_capex(model_id='garrett', inputs=prepared)
```

The connector reads each canonical line's `equipment_cost` component, which is already quantity-extended. It does not use legacy `.total`, installation, module or combined cost, and does not multiply quantity again. It retains parser/calculation provenance. An installed-only source without a purchase split is blocked. Mixed currencies, periods or index bases must be reconciled upstream. Additional included scope can be declared with `included_categories`, and overlapping CAPEX factors then require exclusions.

No existing equipment function is called by input preparation, no baseline is modified, and no engine is attached to the live application. Delivered-equipment confirmation is explicitly required for Nottingham. A caller assertion of delivery basis remains an assumption, not independent evidence of freight scope.

## Future advisor — interface only

`advisor.py` defines a future provider protocol, draft factor proposals and a deterministic validator for classification, published ranges, bases, rationale and source references. There is no LLM implementation, network call or provider dependency. A proposal is not automatically applied or used to change an approved baseline. The draft validator currently checks primary published-table bases; alternative-basis proposal workflows must explicitly select/extend their policy before activation.

## Verification and source handling

Run `python3 -m unittest discover -s backend/tests -v`.

There are 25 new CAPEX test methods: min/max/selected factors, all detailed categories and Lang sectors, optional subtotal bases, rounded-versus-relational Nottingham calculations, working capital, missing inputs, zero/absolute overrides, exclusions, duplicate/overlapping costs, delivered/currency/index scope, model switching, inactive connectors and advisor drafts. The full backend suite passes at 122 test methods. These checks verify source transcription and arithmetic, not industrial project accuracy.

Review renders and test logs are local under ignored `outputs/capex-source-review/`. Only independently structured numerical parameters needed by the implementation and references are stored in source. No scanned textbook table/graph, source PDF, copied table layout or substantial textbook prose is committed or distributed. Original source-document rights are unchanged. No new dependencies, frontend, dashboard, equipment-costing changes or live integrations are introduced.

## Package layout

```text
backend/capex/
    indexes/
        garrett/model.py
        nottingham/model.py
        turton_et_al/          # placeholder; not registered as available
    models.py
    engine.py
    registry.py
    connectors.py
    advisor.py
```

`indexes` groups source-specific CAPEX methodologies. It does not contain CEPCI or other time-escalation series; those remain in the separate equipment-costing index-adjustment layer. The shared API and model IDs remain unchanged.
