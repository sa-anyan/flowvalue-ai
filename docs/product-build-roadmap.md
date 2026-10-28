# FlowValue product build and independent-review roadmap

Source of scope: the founder's written requirements and coverage audits. The supplied workbook is presentation inspiration only. Its formulas, assumptions, coefficients, calculation logic and results are prohibited as implementation or validation sources.

## Delivery phases

| Phase | Deliverable | Exit evidence |
|---|---|---|
| A — Study foundation | Design context, source/evidence register, editable CAPEX/OPEX ledger, coverage questions, inclusion/exclusion states, reviewed OPEX application and saved study versions; foundation for structured R39 natural-language revenue proposals | Blank versus zero preserved; unknown costs visible; no double counting of applied OPEX; context/evidence survives save/reload; dashboard/export reconciliation; proposed waste-sale idea remains reviewable without baseline mutation |
| B — Engineering analyst | Item-specific investigation, supported sizing/material research, internal/external materials, engineering hypotheses, collaborative challenges and connected 2D/3D inspection; R39 waste-stream identity, composition and flow linking | Service constraints and unsupported designs explicit; source-linked decisions; independent sizing cases; reviewed baseline; unsupported stream suitability or invented geometry is blocked |
| C — Project economics | Location/site capital scope, schedule/resources/quantities, workforce allocations, FCOP/VCOP, construction cash flow, sales ramp-up and independently derived workbook formulas; R39 multi-product/by-product sales, incremental costs and avoided disposal | Independent scheduled economics cases, scoped totals without installation double counting, editable export reconciliation; waste revenue and DCF/export reconcile independently of food baseline |
| D — Markets and alternatives | Comparable supplier/product evidence, price history when available, researched energy alternatives, dedicated value-engineering action and baseline-preserving comparisons; R39 optional opted-in comparable waste prices, buyers and contract evidence | Evidence fits grade/region/date/quantity; alternative meets stated constraints or flags gaps; no fabricated quotations; sourced observations; no fabricated quotes or calibrated probabilities |
| E — Risk and study delivery | Researched scenarios, supported distributions/dependencies, reproducible Monte Carlo, detailed study/report/presentation and next actions; R39 natural-language-to-scenario/chart/process-visual reconciliation | Seeded reproduction; independent cases; all deliverables use one approved project version; all metrics and saved graphs agree with the same validated scenario and unchanged baseline |
| F — Existing designs | Validated adapters for specified design/datasheet/drawing formats and reviewed take-offs | Supplied and inferred dimensions distinguished; traceable quantities; no unsupported construction-readiness claim |
| G — Suppliers and execution | Specification-based supplier discovery, RFQ/email/call drafts and authorized workflow execution | Per-action destination/payload authorization, recorded outcomes, returned quotations reconciled to ledger |
| H — Operational integration | Scoped company connectors, actual plant data and validated time-aware operational models | Asset/tag/unit/time mapping, quality/freshness handling and model-versus-actual evidence; scenario animation not labelled live twin |
| I — Independent assurance and recognition | External engineering evaluation, controlled review environment and versioned evidence dossier; seek an applicable IChemE recognition route | Route and criteria confirmed by IChemE; independent assessments and findings resolved; no recognition badge before explicit written permission |

Phase I evidence collection begins in A and continues through delivery. It is not necessary to complete every operational integration before asking which recognition route might apply. Review is scoped to a named product version, use case, methods and limitations; completion of software phases does not confer professional accreditation.

## Cross-phase roadmap — conversational commercial opportunities (R39)

This **planned** founder example (“We earn revenue from food; could we sell our waste?”) is specified in the [canonical workflow](analyst-workflow-specification.md#natural-language-commercial-opportunity-exploration-founder-example-selling-waste). It is not an already implemented chatbot feature or a replacement for existing A–I scope.

| Phase | Work to build | Evidence required before completion |
|---|---|---|
| A | Natural-language idea/price → versioned structured draft, missing-information questions and review status | Both supplied-price and missing-price paths preserve the baseline; unknown quantity is never manufactured |
| B | Link draft to supported waste stream, quantity and quality; annotate schematic only when the stream exists | Missing/invalid stream and any proposed sale route are clearly distinguished from real process geometry |
| C | Multi-product revenue schedule (sold volume × chosen price) and attributable transport/treatment costs or avoided waste expense, without double-counting | Food-only versus proposed waste-sale DCF, NPV/IRR/payback, OPEX/revenue and spreadsheet formulas reconcile using independent reference calculations |
| D | Ask consent before researched prices; compare cited market observations and buyer requirements; assess contract likelihood | Decline triggers no web/paid request; price sources carry date/grade/location/volume/units; unsupported numeric contract probability is withheld |
| E | Link approved scenario preview to Revenue, Scenario and Main dashboard metrics/charts, supported process view, exports and decisions | Price/cost/volume edits update matching visuals and exports; stale/invalid data flagged; original baseline remains untouched |

**R39 regression/acceptance fixtures:** User supplies waste price; user gives none and consents to sourced research; user declines research (zero external calls); missing stream quantity or invalid units; potential buyer without evidence to estimate contract probability; revised assumptions with correct cash-flow/graphs/exports and save/reject/reload. Mock research and independently test deterministic numerical accounting. User-approved scenario application and external enquiries require their respective permissions. Browser acceptance and source review are required before “implemented” is recorded.

See [AI research contract](phase-3-ai.md#planned-r39-ai-opportunity-research), [calculation conventions](calculation_basis.md#planned-r39-multi-revenue-accounting), [engineering view](phase-4-engineering.md#planned-r39-process-view-connection) and [release gate](phase-5-release.md#future-r39-release-gate).

## Phase A implementation boundary

Build the design/evidence/ledger foundation first, with deterministic input review and no paid research calls. OPEX quantities and rates use annual USD values at selected utilization. An explicit, named-reviewer action replaces the model's manual fixed/variable OPEX totals with the reviewed ledger snapshot, rather than adding duplicate expenses. Subsequent edits mark the application stale until reviewed and applied again. Existing financial sensitivity controls remain available on the applied snapshot.

The CAPEX register is planning-only in A. BOM equipment CAPEX still drives the financial engine; location/construction/resource totals and scheduled spending are implemented in C. No non-USD conversion, autonomous engineering analysis, accreditation assessment, collaboration permissions or external communications are implied by the foundation UI.

## Phase B implementation boundary

The [Phase B implementation record](phase-b-engineering-analyst.md) describes delivered unit investigations, separate wetted/shell/lining materials, supported sizing, explicit evidence and baseline gates, bounded optional research and exact-revision peer review. These are preliminary user-reviewed designs, not mechanical/material certification. 3D remains schematic; browsers without WebGL retain 2D and unit-review controls. No paid research request was required for development validation.

## Recognition ambition and current evidence

Goal: develop a chemical engineering economic analyst that qualified professionals and professional institutions can meaningfully evaluate.

Checked official IChemE pages on 2026-10-27:

- https://www.icheme.org/training-events/training/icheme-approved-training/ — publishes independent training/course approval and use of approval graphics for approved courses.
- https://www.icheme.org/employers-educators/ — describes degree and graduate training scheme services.
- https://www.icheme.org/employers-educators/services-for-employers/accreditation-graduate-training-schemes/how-to-achieve-accreditation/ — describes assessment of graduate training schemes and associated recognition.

These are evidence of specific programme/training routes, not evidence that IChemE accredits AI analysts or that FlowValue qualifies. A software/AI-specific route was not established in this review. Obtain written guidance directly from IChemE before choosing an application category or making accreditation/endorsement claims. An award, course approval, partnership, human professional registration and software validation are distinct outcomes. “First AI to earn a badge” is an aspiration, not a verified priority or marketing claim. No institutional logos or badges are to be added without authorization. No outreach is authorized by this document.

## Independent-review evidence to accumulate

- Controlled scope, supported equipment/processes, known limitations and intended users.
- Versioned methods, units, correlation provenance/ranges and licensed-data rights.
- Independently established numerical cases; inspiration workbook excluded.
- Evidence provenance and explicit assumptions, unknowns and unsupported estimates.
- Recorded review decisions, challenges, changes and accountable engineering oversight.
- AI/model/prompt/tool versions and evaluation of unsupported claims and source attribution.
- Repeatability, uncertainty assumptions, sensitivity results and correct unavailable outcomes.
- Access control, privacy, permission boundaries, operational failure handling and change management.
- External validation reports, discrepancies, corrective actions and re-evaluation after material changes.

Accreditation criteria and decision authority remain external. FlowValue must not self-award a recognition badge or describe internal arithmetic tests as institutional approval.
