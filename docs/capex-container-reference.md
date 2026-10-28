# CAPEX container reference and implementation boundary

The founder identified `Task 2 Charlie Economics 2.xlsx` as the legacy reference for this CAPEX iteration. It was inspected read-only. The earlier Protein-from-Air workbook remains historical presentation inspiration, with its existing calculation-use restrictions.

Reference structure inspected:

- `Task 2 equipments!A2:E38`: tagged equipment, descriptions, original-currency purchase costs, converted costs and installed costs.
- `Equipments!A2:J17`: equipment families, quantities, costing references, installation and escalation.
- `Linked Sheet!D1:K10`: direct, indirect and other indirect scope. Legacy percentages are not adopted as validated factors.
- `Capex!A2:I27`: category roll-up, fixed capital, working capital and total investment, with scenario variants.

The software retains all seven CAPEX children and existing equipment, engineering, index, source and validation sections. The new worklist uses active project inputs, distinct scope states, explicit quantities/rates, allocations and linked evidence. Named scope rows can be created without amounts. Those placeholders are missing inputs, never zero-cost estimates.

The legacy register includes paired/combined equipment tags and standalone specialised equipment. A tag is not proof of equipment count, capacity, design rating or a suitable vessel-shell cost proxy. No mass/energy balance or complete design specification was supplied in this request. Actual equipment sizing must continue to use supported project design inputs or explicit quotations. The UI does not invent streams, ratings, correlations or supplier prices from the workbook.

Current arithmetic remains independently implemented quantity × USD rate × allocation. Foreign-currency references prompt conversion review; no exchange rate or inflation factor is imported from the legacy file. Bare-module cost and purchased cost remain non-additive. Planning allowances are not automatically added to DCF CAPEX or presented as a reconciled total investment. Working-capital scope is distinct from depreciable equipment.

No legacy figures, formulas, workbook binary or private source path are published with the frontend. No paid AI research is used for these deterministic worklist checks. The inspected file's hash is recorded locally for source-preservation verification.
