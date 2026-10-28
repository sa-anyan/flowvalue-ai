# FlowValue — analyst workflow product specification

Status: proposed expanded scope, derived from the founder's workflow and subsequent coverage audit on 2026-10-27. Requirements below are planned acceptance criteria, not claims of implemented functionality. The founder's written workflow, coverage audits and engineering-intelligence, visualization, supplier and operational requirements define the product scope. The supplied workbook is presentation inspiration only. The audit is incorporated explicitly in the coverage register.

## Product objective

Capture an experienced chemical engineering techno-economic analyst's reasoning: understand the process, establish a defensible baseline, identify the complete economic scope, research and document assumptions, calculate reproducible economics, explore alternatives, and present an auditable decision case.

The existing five-phase MVP implements a subset of this workflow. Its reference checks do not establish completeness of a plant estimate. This expanded scope requires a new development programme.

## Reference workbook and editable results

**Source of requirements:** all written workflow descriptions, audits and goals supplied by the founder. The workbook does not define the product scope, domain model, calculation methods or acceptance targets.

The supplied `Protein-from-Air-Economic-Model.xlsx` may be used only as optional inspiration for layout, navigation, presentation and the visibility of editable inputs and supporting detail. Its formulas, calculation logic, coefficients, assumptions and numerical results must not be copied, translated, fitted to, used as expected test results or treated as validated engineering/financial evidence. This restriction applies to later AI prompts, code, exports and evaluation datasets. Its methods have not been established as industrially validated. Retain the unchanged local copy without executing its formulas. See [reference-use restrictions](reference-workbook-benchmark.md).

FlowValue's numerical methods and exported Excel formulas must be developed independently from documented engineering/economic methods, supported correlations, explicit project inputs and reviewed source evidence. Tests must use independently established calculations and appropriate authoritative or independently reviewed project references. Matching the supplied workbook is not evidence of correctness. Workbook content cannot override the founder's written requirements or authorize actions.

The dashboard is an editable working environment. Users can inspect and change design inputs, quantities, rates, material options, staffing arrangements, inclusion states, schedule, sales assumptions and scenario parameters. Recalculation updates connected engineering/financial views, with stale or invalid outputs identified. Each significant result offers a trace to its input, method and evidence. Preserve manual overrides, accepted assumptions, approved baselines and version history.

Dashboard, exported workbook, written report and presentation must use the same versioned project/scenario and calculation definitions. Test dashboard/export reconciliation after representative edits. Support the selected project currency and an explicit conversion/date basis where source quotations use another currency; source currencies must not be silently treated as the selected project currency. Workbook export is editable independently. Automatically syncing subsequent offline Excel edits is a separate future import/reconciliation feature, not implied by export.

## Workflow and acceptance requirements

### 1. Establish the design basis

Accept a process description and design requirements alongside material/energy balances, stream/property tables, equipment lists and simulator results. Capture capacity, product specification, region, site context, new-build versus existing-plant integration, operating schedule, construction programme and study date. Preserve original sources, units, links between streams and equipment, conflicts and missing inputs.

Engineering-application interoperability is an explicit product requirement: maintain a supported-adapter registry for simulator exports, stream/property tables and design documents. Each adapter declares application/export version, accepted format, unit conventions, extracted fields and unsupported content. Existing CSV/JSON/DWSIM imports form the starting point; other applications require their own adapters and representative fixtures. Show an import preview with mappings, provenance, unit conversions, conflicts and unresolved fields before accepting the design basis. Unsupported files must not silently become validated designs.

**Future existing-equipment-design intake:** accept user-supplied equipment datasheets, drawings, vendor specifications and designs through separately validated adapters. Retain supplied dimensions/materials/ratings, distinguish supplied design from inferred sizing, and require review of extraction confidence and inconsistencies. A supplied design can become the baseline for downstream costing without redesigning it; modifications remain separate alternatives. This is a future extension, not delivered by importing stream tables.

The analyst creates a structured design-basis record before generating costs. A short adaptive questionnaire requests high-impact missing information. Unknown information remains explicit; inferred values are marked assumptions. Future equipment drawings/designs need their own validated extraction adapters.

### 2. Establish baseline equipment and materials

Generate an equipment register with sizing basis, operating/design conditions, service requirements, proposed materials, engineering rationale, sources and review status. Food-contact, cleanliness, corrosion, pressure and temperature requirements are separate inputs, rather than properties inferred from a material name alone. Identify possible liners/cladding and distinct internal/external materials where supported by design information.

Material suitability research must consider process chemistry and concentration, operating excursions, corrosion/erosion, hygiene/cleanability, food-contact requirements where applicable, fabrication, availability and maintenance. Record each claim's source, applicability and uncertainty. Represent wetted/internal material, liner/cladding and structural/external material separately; a premium lining and ordinary outer shell require explicit compatibility and construction assumptions. Neither stainless steel nor a citation alone establishes sterility or suitability.

Equipment costing explicitly uses named correlations or quotations and dated escalation indices including CEPCI, with reference/target index, material and pressure factors, validity ranges and license/source basis. Location, currency and scope adjustments are separate factors with documented application order. Missing correlations, indices or suitability evidence must remain visible.

Enable collaborative design review on each material/equipment decision. Show the proposal, reasoning, evidence and unresolved assumptions; authorized reviewers can agree, challenge, comment and resolve questions. Record reviewer identity, date, decision and subsequent revisions. Challenges remain linked to the affected items and dependent estimates. Build a reviewable analytical record rather than assigning a material without justification.

Investigate each relevant equipment item individually, including pumps, valves, reactors and heat exchangers. Link process duty and service constraints to item-specific questions, material/sizing methods, supplier evidence and costing scope. Equipment without a supported sizing/cost method requires an identified quotation, assumption or missing-data state.

Baseline decisions must be captured before optional value engineering. Numerical sizing and cost calculations use validated code, identified correlation ranges and explicit quotation/index bases. Unsupported equipment stays unpriced or uses an identified assumption/quotation, never an invented validated correlation.

### 3. Build a scoped total-capital estimate

Use a work/cost breakdown covering process equipment, installation, piping, instrumentation, electrical, civil/structural works, buildings, utilities/offsites, site/land, engineering, construction management, permits, commissioning, contingency and owner costs. Include temporary facilities, construction labour and other location/project-specific categories when relevant. Explicitly investigate land, temporary staff accommodation, project offices, printers/office supplies and small construction/operating consumables when applicable. Record why a category is not applicable instead of treating absence as zero.

Make the **schedule → work packages → resource breakdown → material/equipment quantities → cost ledger** chain explicit. For each scheduled activity, identify labour roles/hours, construction equipment, subcontracted services, temporary facilities and material take-offs or disclosed allowances. Link quantities and costs back to activities and design sources; retain unallocated costs and missing take-offs as visible coverage gaps. Include temporary accommodation where the location, workforce and construction plan justify it. Do not fabricate item-level precision from a factor-based estimate.

Location-specific site development, transport/logistics, wage and productivity assumptions, permits/fees and new-build versus integrated-site infrastructure must have explicit ledger entries or documented exclusions. Distinguish construction/procurement resources from the operating workforce and preserve their timing.

Each cost item records description, quantity, unit, rate, currency/date, calculation method, source/evidence, inclusion status, uncertainty and scope boundary. Distinguish estimated, quoted, factored, measured and missing quantities. Show coverage and exclusions explicitly. Prevent double counting equipment installation against bare-module factors and separate contingency from probabilistic allowances.

At preliminary design, estimate civil works and bulk materials using disclosed allowances or factors. Detailed concrete, flanges, bolts and other quantities require layouts, P&IDs, piping specifications/isometrics, civil/structural designs and take-offs. A mass/energy balance alone cannot produce an exhaustive procurement BOM or construction-ready blueprint. Tag deliverables by the actual design information and estimate maturity; do not promise construction readiness from preliminary inputs.

### 4. Build an editable operating-cost ledger

Develop fixed and variable costs from process duties, consumables and operating assumptions. Cover feedstocks, utilities, labour by role/shift, supervision, maintenance, spares, cleaning, laboratory/quality, waste, insurance, site overhead and other justified categories.

Allow inclusion/exclusion with recorded reasons and user-added cost items. Distinguish incremental cash expenditure from allocated existing staff/facility costs and other accounting treatments. Record headcount, shift coverage, salary burden and maintenance basis. Reconcile fixed/variable components with totals without duplicate utility/raw-material charges.

Investigate operating costs against the actual unit operations, operating mode, hygiene/cleaning requirements, maintenance strategy, wastes and staffing needs. Ask targeted questions for unknown shifts, staffing arrangements, outsourcing, existing assets and shared services. Record employee versus contractor, already employed versus incremental hire, employer/project payer, allocation fraction, benefits/burden, recurring versus one-off cost and cost owner. Salaried labour may be fixed; contract or throughput-dependent labour needs its own classification rationale.

Provide a checkbox for each cost item/category and an **Add item for AI investigation** text box. A user can request an extra cost, review the proposed description, quantity/rate, source, fixed/variable treatment and inclusion basis, then include it. Excluding an item keeps its value and rationale in the audit trail and updates coverage, totals and downstream metrics. Excluded, zero-cost, not applicable, unknown/missing information and unsupported/unquantifiable estimates are distinct states. Unsupported values must not be silently replaced with zero or disguised as researched estimates. Show the effect of incomplete coverage on the estimate scope; do not invent a numerical allowance without a labelled basis. Category totals must reconcile to enabled child items.

Explicitly classify and report **FCOP (fixed cost of production)** and **VCOP (variable cost of production)**, with units and throughput basis. Costs that combine fixed and variable portions must be split; allocation must not silently change cash expenditure.

AI proposals remain reviewable ledger entries; user requests create explicit cost items with units, sources and assumptions before changing calculations. No silent mutation of an approved baseline.

### 5. Research revenues and market scenarios

Record product grade, geography, sales basis, date, currency, quantity and delivered/ex-works basis. Distinguish retail/listing prices, quotations, historical observations and achievable bulk selling-price assumptions. Model sales volume separately from production, including ramp-up and unsold production assumptions. Support by-products and disposal costs where appropriate.

Supplier and buyer/market research are separate evidence streams: supplier quotations/listings support purchased inputs and equipment; achievable product sales prices require a matching grade, region, volume and commercial basis. Record quote validity, date, minimum quantity, transport/duties and currency where available. Contacting suppliers or sending inquiries requires explicit user authorization; public research alone does not imply a quotation or sale commitment.

Research returns attributable sources, observations, limitations and conflicting evidence. If reliable prices are unavailable, request a quotation/input or label the chosen assumption. Never manufacture citations, market charts or confidence scores.

#### Natural-language commercial opportunity exploration (founder example: selling waste)

A user may describe a commercial idea in ordinary language, for example: **“We currently earn revenue from food. Could we sell our waste as well?”** FlowValue must interpret the idea as a **proposed revenue scenario**, not merely answer in chat. Use the available project description, stream/material balances and waste specifications to identify candidate saleable streams; show unknown quantities, composition, quality or legal/commercial suitability as questions instead of inventing them. The existing food revenue remains intact, and the waste opportunity becomes a separately labelled, traceable proposed revenue item.

- **Price provided by the user:** If the user supplies a selling price (including a later follow-up), capture the price and its currency/unit/sales basis as a user assumption. Show waste as an additional revenue source with the supplied price and the supported or explicitly assumed saleable quantity. Recalculate a **preview scenario** using revenue = volume sold × selling price and consider relevant additional treatment, processing, storage, transport or avoided disposal costs where applicable. Do not silently turn the proposed opportunity into confirmed sales or overwrite the approved baseline.
- **No price provided:** Ask whether the user wants FlowValue to **research a potential selling price**. Only perform that research following the user's affirmative choice. Return possible price points or ranges with attributable references, observed date, location, material grade/quality, volume and delivery basis, plus limitations or conflicting evidence. If a credible comparable price cannot be found, say so and ask for a quote or manual assumption; never invent a market price.
- **Likelihood of securing a buyer/contract:** Alongside researched prices, evaluate potential buyers and the **probability of obtaining a contract** in light of actual supporting evidence (buyer requirements, demand, competing supply, waste specification, logistics, expressed interest and available deal outcomes). Show the evidence and uncertainty. Give a numeric probability **only if an explicit, defensible calibrated basis exists**; otherwise state that a numeric probability cannot be reliably estimated and present a qualified assessment, not a fabricated percentage. A market listing or identified buyer is not a signed contract.
- **Connected financial and visual response:** The proposed waste revenue appears in the revenue breakdown and relevant charts, with updated total revenue, cash flow, NPV, IRR and other affected metrics. Applicable process/stream visualisations reflect the proposed waste-sales path where process connectivity is supported; do not fabricate physical connections. Display **before/after** comparisons and distinguish user-entered, researched, estimated, unknown and confirmed inputs. The idea and its sources, assumptions, calculations and user decisions remain inspectable and versioned.

**Acceptance case:** Starting with food-only revenue and an identified waste stream, entering “Could we sell our waste?” creates a proposed revenue branch. With a supplied price, the proposed waste line and relevant visuals and economics update without changing the baseline. Without a price, the app asks permission to research; affirmative consent produces sourced price possibilities and a defensible contract-likelihood assessment (or an explicit “not estimable”), then allows the user to select or edit assumptions and see the corresponding updated scenario. A refusal does not trigger research. Unsupported quantity or buyer certainty remains visible rather than being silently filled in.

### 6. Model calendar and cash flow

Support multi-year construction spending, commissioning, production and sales ramp-up, operating costs by year, working capital, replacement expenditure, depreciation/tax assumptions, policy scenarios and terminal/decommissioning assumptions. Explicitly distinguish fixed operating costs that begin before full production from throughput-driven costs.

Calculate NPV, IRR/DCFROR, discounted and undiscounted payback and LCOP from the same scheduled cash-flow model. Document discounting/date convention, real versus nominal basis, treatment of inflation and definitions of LCOP. Return an explicit undefined/no-payback result when appropriate; do not manufacture a unique IRR for cash flows with multiple sign changes. Annual revenue equals sales volume times the applicable selling price, with inventory/unsold output treatment declared.

An acceptance case must reproduce three construction years with no sales followed by 20% production/sales in the first operating year, with a user-defined later ramp. Financial metrics and formula-driven exports must use the same approved annual schedule. Construction, operating-year and calendar-year dates must be reconciled with policy windows.

### 7. Compare alternatives and risks

Provide a dedicated **Optimise for value engineering** button after baseline approval, with progress/error states and a comparison view. Propose material/design alternatives with technical constraints, sources, cost implications, unresolved suitability checks and approval status. Compare scenarios side by side; retain the baseline unchanged.

The comparison view must show original and alternative materials/design assumptions, technical suitability gaps, CAPEX, FCOP/VCOP, revenues, NPV/IRR/payback/LCOP and evidence. Users can accept an alternative as a new version or reject it; running the action never overwrites the approved baseline.

Support deterministic sensitivities and researched scenario narratives before probabilistic simulation. Separate historical evidence from forward assumptions. Monte Carlo inputs must have specified distributions, bounds and justified dependencies/correlations; avoid independently perturbing every parameter or treating a stress range as a probability distribution. Report missing evidence and sampling assumptions. Provide a dedicated **Run Monte Carlo** action with parameter/distribution selection, bounded run count, seed, progress/errors, P10/P50/P90 results and reproducible settings. Calculate sensitivity and uncertainty on the expanded scheduled model, including non-cost drivers where justified. Research-driven scenario tests must connect each event/trend to a parameter, magnitude, horizon and source; speculative scenarios are labelled as such.

### 8. Process visualization and operational integration

Maintain a connected process graph linking streams, equipment, design requirements and economic ledger items. Provide interactive 2D/3D process views with selectable unit operations and associated sizing, materials, conditions and costs. Geometry/layout derived from a schematic must be distinguished from verified engineering/CAD geometry. Editing a supported input from a unit-operation view follows the same validation and recalculation workflow as dashboard edits.

Provide time-aware process visualization for construction stages, commissioning, ramp-up and operating scenarios. Label simulated scenario playback separately from measured operational history. A proposed 4D digital twin requires explicit asset/tag mappings, timestamps, data quality, engineering units, lineage, update cadence and comparison of model predictions against actual measurements.

Future company-system connectors should support declared capabilities for engineering document systems, ERP/procurement, CMMS/maintenance and historian/operational data where authorized. Begin with bounded imports and read-only integrations; document ownership, retention, freshness, missing/invalid telemetry and access scopes. Operational state must not silently rewrite the approved design/economic baseline. A live-data or digital-twin claim requires a connected, validated data source and defined model behavior, not just an animated 3D graph.

### 9. Supplier intelligence and authorized execution

Identify relevant equipment/material suppliers against item specifications, region, supply capability and available evidence. Keep supplier discovery separate from verified supplier qualification, current stock, quotation or contractual commitment. Compare specification fit, quotation scope/date/currency, delivery, transport, maintenance and gaps when information exists.

Prepare reviewable RFQs, supplier-enquiry emails, call briefs and follow-up tasks from the approved specifications and scope. An execution proposal identifies recipient/destination, payload, attachments, purpose, costs if any and requested action. Sending emails, placing calls or writing to external company systems requires explicit user authorization for that action and destination. Preparing drafts does not authorize transmission. Record authorization, execution outcome and any returned quotation against the relevant cost item. No external communications are authorized merely by this requirements document.

### 10. Deliver an auditable study

Export design basis, equipment register, scoped capital estimate, operating ledger, market assumptions, construction/operating cash flow, alternatives, risk results, references, exclusions and review decisions. Preserve active workbook formulas and a reproducible study version.

The deliverable is a versioned **project study and execution-basis dossier**: design assumptions, work/resource breakdown, available quantities, staffing plan, cost scope and schedule, dependencies, unresolved design deliverables, financial workbook and written report and presentation deck with recommended next actions, owners and outstanding inputs. A construction-ready blueprint is a future, conditional deliverable requiring the relevant detailed engineering and qualified review. Show which procurement/construction decisions the present study can and cannot support.

Every material reported number must trace to an input, calculation, quotation or clearly labelled allowance. Changing an assumption invalidates dependent approvals/results. Reports state estimate maturity and required additional engineering deliverables.

## Consistent AI execution

Engineering judgment must be represented as a reviewable investigative process: develop hypotheses from design context, identify overlooked requirements, prioritize consequential unknowns, select the next useful research/question, compare alternatives and explain which evidence supports or challenges a conclusion. Capture project-specific reasoning beyond mandatory checklist coverage. Where evidence is insufficient, ask a targeted question or propose a labelled assumption rather than fabricate certainty. Evaluation should test the quality of the investigation and technical/economic implications as well as checklist completion.

A rigid role prompt is one component. Use a versioned workflow, structured schemas, domain checklists, deterministic numerical engines, evidence records, tool permissions and approval states. Store model/prompt versions, retrieval timestamps, calculations and user decisions. Cache research by subject, region and date to reduce cost. Reuse accepted evidence and call paid research only for gaps or requested refreshes.

The analyst behaviour contract must specify role, stage inputs/outputs, required questions, mandatory coverage checks, source-quality rules, uncertainty labels, numerical-tool usage, stop/escalation conditions and prohibited unsupported claims. Use explicit structured outputs and an assumption register rather than relying on a free-form answer. Repeated runs on fixed fixtures must pass acceptance checks for coverage, unit consistency, source attribution and calculation reconciliation; wording may vary. Add representative founder examples as evaluation cases when supplied. Do not promise identical research results as sources/models change.

Suggested states: draft → missing-information review → proposed baseline → reviewed baseline → alternatives → issued study. Approval means a recorded user review, not independent engineering certification.

## Proposed build sequence

A. **Design basis and shared cost ledger**: context ingestion, adaptive questions, source/assumption records, editable scoped CAPEX/OPEX items and coverage reporting. This is the foundation for the rest.

B. **Equipment analyst and sourced baseline**: service-aware material/sizing proposals, equipment completeness, traceable cost methods and analyst review.

C. **Project economics**: total capital scope, workforce/operating models, construction cash flow, ramp-up and formula-driven schedule exports.

D. **Market research and alternatives**: supported price evidence, sales assumptions, baseline-preserving value engineering and comparison views.

E. **Scenario research, uncertainty and study delivery**: evidence-based stress scenarios, supported distributions/dependencies, regression examples and expanded reporting.

F. **Existing designs and detailed take-offs (future extension)**: application-specific datasheet/drawing/design adapters, reviewed extraction and linking supplied equipment designs and engineering take-offs into the existing study. Start with explicitly supported document types; construction-level outputs depend on actual design maturity.

G. **Supplier intelligence and reviewed execution**: specification-matched supplier discovery, sourcing comparison, RFQ/email/call drafts, explicit authorization controls and quotation-to-ledger reconciliation.

H. **Company integration and operational digital twin (future extension)**: authorized system connectors, actual plant data, asset/tag mappings, data-quality handling and time-aware model-versus-actual analysis. Earlier phases provide the process graph, interactive 2D/3D views and clearly labelled schedule/scenario playback; operational 4D capabilities require measured data and model validation.

These are proposed phases, not completed phases or a time estimate. The founder's written examples guide workflow acceptance; independently established calculations and reviewed engineering evidence guide numerical validation. The supplied inspiration workbook is excluded from calculation-reference cases and decision-rule extraction. Detailed engineering/procurement automation is a separately bounded expansion requiring the relevant design deliverables.


## Coverage register from the founder's audit

Every row is explicit planned scope. “Acceptance” describes how to demonstrate it, not current delivery status.

| ID | Requirement | Phase | Acceptance evidence |
|---|---|---|---|
| R01 | Understand description, balances and design requirements | A | Reviewable design basis links requirements to source streams/equipment; missing/conflicting inputs shown. |
| R02 | Accept data from different engineering applications | A, then F | Adapter registry and import preview; unit/mapping fixtures for each supported application/export version. |
| R03 | Eventually accept existing equipment designs | F | Reviewed design/datasheet fixture retains supplied dimensions/materials and continues to costing without silent redesign. |
| R04 | Detailed, consistent AI analyst behaviour | A–E | Versioned behaviour contract, structured outputs and repeated fixture-based coverage/calculation evaluations. |
| R05 | Baseline equipment sizing and material selection | B | Reviewed equipment register with sizing basis, service requirements, method and unresolved scope. |
| R06 | Research suitability and internal/external materials | B | Sourced, service-specific reasoning; distinct wetted/liner/shell selections and compatibility gaps. |
| R07 | Dedicated value-engineering button and comparisons | D | Button creates an alternative; comparison shows technical/economic changes and preserves baseline. |
| R08 | CEPCI, indices and correlation-based equipment costs | B | Reproduce a calculation with dated index ratio, correlation, factors, range checks and source/license basis. |
| R09 | Location-specific CAPEX, installation, permits and construction | C | Scoped ledger has location/site basis and included/excluded amounts; no duplicated bare-module installation. |
| R10 | Schedule → resources → detailed BOM | C; detailed take-offs F | Trace an activity through resources/available quantities to costs; show allowances and missing engineering inputs. |
| R11 | Research-backed estimates, sources and justifications | A–E | Each material input traces to evidence, calculation or explicit assumption; unsupported claims fail review. |
| R12 | Uncovered costs and limitations | A, C, E | Coverage register distinguishes unknown, excluded and not-applicable items; report reproduces gaps. |
| R13 | Design-specific operating-cost investigation | C | Unit-operation/operating-mode checklist generates justified operating items and targeted questions. |
| R14 | Staffing, employment and contractor allocation | C | Role/shift/payroll/contract fixture reconciles incremental and allocated costs with payer and timing. |
| R15 | Tick/untick and custom AI-researched cost items | A foundation, C research | Exclusion updates totals without deleting evidence; custom proposal requires review before inclusion. |
| R16 | Separate fixed and variable operating costs | A classification, C model | FCOP/VCOP subtotals reconcile; throughput changes scale variable components with documented bases. |
| R17 | Supplier research, market prices and revenues | D | Comparable price/quote evidence includes grade/region/date/volume; sales assumptions drive revenue. |
| R18 | Multi-year construction, ramp-up and sales | C | Three construction years with zero sales, then 20% production and explicit sales; schedule reconciles. |
| R19 | NPV, IRR, payback and cash flows | C | Scheduled reference case reconciles financial metrics and workbook formulas, including undefined outcomes. |
| R20 | Research-driven scenarios and sensitivities | D, E | Scenario links evidence/event to parameter swing and horizon; changes reconcile to recomputed metrics. |
| R21 | Monte Carlo uncertainty testing | E | Seeded run reproduces results with documented distributions/dependencies and bounded runtime. |
| R22 | Project blueprint, workbook and report | E study; F conditional detail | Versioned dossier, active formulas, references and coverage; construction readiness requires actual detailed designs/review. |


## Additional coverage from the written goals

| ID | Requirement | Phase | Acceptance evidence |
|---|---|---|---|
| R23 | Investigative engineering judgment | A–E | Representative case detects consequential design-specific gaps, asks useful questions and records alternative hypotheses/evidence. |
| R24 | Collaborative agreement/challenge on design reasoning | B | Authorized reviewers can challenge an item, resolve it and inspect the retained decision/version trail. |
| R25 | Equipment-specific investigation, including valves | B | Each supported equipment type has item-level service requirements and evidence; unsupported methods remain flagged. |
| R26 | Small consumables, offices and temporary accommodation | C | Coverage review records applicable costs or justified exclusions separately from unknown/unquantifiable amounts. |
| R27 | Multiple inputs including natural language and open-source adapters | A, B, F | Natural-language input produces reviewable structured context; supported simulator/data adapters preserve provenance and declared capabilities. |
| R28 | Interactive connected 2D/3D process representation | A graph foundation, B interactive view | Selecting a unit exposes linked conditions, sizing, materials and cost; supported edits update the model without breaking stream links. |
| R29 | Time-aware visualization / proposed 4D twin | C/E playback, H operational | Time selection changes stage/scenario results; operational mode labels measured versus simulated data and exposes timestamps/quality. |
| R30 | Real company workflow/system integration | H | Scoped connector fixture maps authorized records with units, ownership, freshness and error handling; writes require authorization. |
| R31 | Supplier identification and sourcing | D evidence foundation, G discovery | Supplier shortlist matches equipment/material specifications and region, with evidence and qualification gaps. |
| R32 | Agentic enquiries, emails and calls | G | Drafts show recipient/content/attachments; execution is blocked without explicit authorization and records the outcome. |
| R33 | Modifiable engineering/financial/scenario dashboards | A–E | Quantity/rate/schedule/material/inclusion edits update affected results; invalid/stale state is clear and baseline is preserved. |
| R34 | Detailed editable economic workbook driven by the written requirements | A–E | Independently developed cost/revenue schedules, DCF, sensitivities and controls reconcile with the dashboard and independent reference calculations. No formulas, logic or expected results originate from the inspiration workbook. |
| R35 | Written report, presentation, documentation and next steps | E | Outputs use the same project version and show findings, evidence, exclusions, decisions and actionable next steps. |
| R36 | Actual plant data and operational intelligence | H | Timestamped actual inputs reconcile to model units/assets; model-versus-actual analysis does not silently overwrite design assumptions. |
| R37 | External-event discovery and alternative energy research | D, E | A case traces a sourced event such as a pandemic-related power-price shock to a justified scenario; a wind-power alternative records region, availability, technical constraints and price basis. |
| R38 | Project currency and comparable commercial bases | A ledger, C/D economics | Mixed-currency project inputs and quotations use declared conversion/date assumptions; dashboard and exports reconcile in the selected currency. |
| R39 | Conversational waste/by-product sales opportunities and live economic visualisation | D market evidence, C revenue model, E scenario/visual comparison | Food-revenue baseline plus a new waste-sale idea: supplied price creates a separate proposed revenue line and recomputed graphs; absent price prompts before sourced research; buyer/contract likelihood is evidence-grounded or marked not estimable; baseline and source trail remain intact. |
