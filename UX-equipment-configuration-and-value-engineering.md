# Equipment configuration and value-engineering UX

Saved: 30 October 2026
Status: proposed UX and acceptance requirements, not implemented functionality.

## Purpose

Let users inspect parsed equipment, change equipment-specific features, and compare equipment, installation and combined costs while preserving the original design baseline.

## Equipment page layout

Use one compact equipment register with an expandable configuration panel for each item. Each equipment item has its own editable feature controls, rather than a large separate table occupying the page for every unit.

Keep the interface clean, professional and easy to inspect. Controls adapt to the equipment type: a reactor, pump and heat exchanger should not expose the same configuration fields.

## Handling a parsed reactor

An item labelled “reactor” does not by itself establish the appropriate cost model. First display the available engineering evidence:

- Equipment tag and description.
- Volume and units.
- Operating pressure and design pressure, distinguished explicitly.
- Temperature.
- Material of construction.
- Agitation.
- Jacket.
- Source workbook, worksheet/cells or other parser evidence.

Missing features remain “Not specified”. Do not silently assume agitation, material, pressure rating or a costing configuration.

## Example reactor controls

| Feature | Control |
|---|---|
| Volume | Numeric input and unit |
| Design pressure | Numeric input and unit |
| Material | Supported material dropdown |
| Agitation | Yes / No / Not specified |
| Jacket | Yes / No / Not specified |
| Costing method | Applicable source and configuration |
| Installation factor | Source default with reference and applicability notes |

Expose only supported combinations as calculable. Explain missing evidence or unsupported choices rather than silently substituting another equipment curve. Preserve parsed values separately from user changes and show their provenance.

## Costing examples

- A jacketed, agitated mild-steel reactor at 300 psi can map to Garrett’s agitated-tank reactor curve G258-006, subject to the remaining source applicability conditions.
- The corresponding 50 psi agitated reactor curve is G258-007.
- A jacketed 304 stainless reactor without agitation belongs to the separate reactor curve G299-133.
- Do not infer a reactor subtype from a tag alone or automatically interpolate between pressure curves without an implemented, justified method.

## Interactive cost preview

Changing a supported feature produces a preview through the deterministic costing engine. Show:

- Equipment cost.
- Installation cost.
- Equipment plus installation cost.
- Difference from the saved baseline.
- Selected cost model, source, cost date/index and units.
- Provisional-data, extrapolation, missing-factor and unresolved-assumption notices.

Unknown installation cost remains unavailable, not zero. Avoid double counting installation already present in source prices. Unit prices need explicit quantities before they become total costs.

## Value-engineering comparison

Preserve the original configuration and approved baseline. Let the user compare alternatives and explicitly apply a selected alternative. Retain a record of the changes and the original source evidence.

A cheaper material, lower pressure rating or changed agitation arrangement is only an economic scenario until it is shown to meet the process and design requirements. A dropdown change does not establish corrosion resistance, food safety, mechanical suitability or equivalent process performance.

## Build status and next implementation work

Existing backend configuration IDs and separate equipment/installation/combined cost outputs provide a foundation. The adaptive equipment configuration UI and automatic evidence-based configuration matching are not yet built.

Next implementation work:

1. Build the expandable equipment register and equipment-specific controls.
2. Map engineering features to exact supported costing configurations, with explicit missing-information handling.
3. Connect preview changes to the canonical costing engine.
4. Preserve baseline-versus-alternative comparison and require an explicit Apply action.
5. Verify model selection, units, costs, source traceability and baseline restoration end to end.

## Pressure-method selector — backend implemented, UI pending

For supported equipment, add a pressure-costing dropdown with “Keep original pressure curve”, “Garrett pressure power relationship”, and “Garrett table with linear interpolation”. Agitated-tank options must visibly say “agitated-vessel proxy”; they are not a Garrett instruction specific to agitated tanks. Source/reference pressure, target design pressure, explicit gauge/absolute basis and an applicability note must be shown.

The backend now exposes `pressure_adjustment_options`, source references and a full factor-ratio breakdown. Show F(reference), F(target), their ratio, interpolation/extrapolation assumptions, unchanged installation-factor assumption, and equipment/installation/combined price differences. Default remains the original curve. No saved baseline is automatically changed. Unsupported/open-tank pressure scenarios are blocked.

See `backend/equipment_costing/indexes/garrett/PRESSURE_ADJUSTMENT.md` for the request contract and limitations. This is backend readiness for the proposed selector; the clean rebuild has no executable frontend page yet.
