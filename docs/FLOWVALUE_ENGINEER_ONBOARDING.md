# FlowValue AI — Engineering Onboarding, Architecture Memory & Collaboration Brief

**Last compiled:** 4 November 2026  
**Audience:** incoming chemical engineer, their Codex agent, founder and other collaborators  
**Repository:** https://github.com/sa-anyan/flowvalue-ai  
**Trello work board:** https://trello.com/b/muwloo6g/flowvalue-ai-end-to-end-development  
**Status:** living orientation document; do not interpret this file as certification of engineering accuracy or deployed functionality.

> **Codex, read this entire file before proposing or changing code.** Then read `AGENTS.md`, `docs/analyst-workflow-specification.md`, `docs/product-build-roadmap.md` and the README/schema/source modules for the task at hand. This document preserves founder decisions, engineering purpose, architecture relationships and recent test findings. Actual code and source records are the source of truth for implementation details. If implementation differs from this summary, report the discrepancy instead of silently changing the product scope.

## 1. What we are building

FlowValue AI is an **end-to-end, AI-assisted chemical/process engineering and techno-economic analysis (TEA) platform**, not merely a costing spreadsheet, financial calculator, LLM wrapper or an equipment cost index.

The user can begin with process-simulation outputs, a mass-and-energy (M&E) balance, process design information and/or a natural-language process description. FlowValue is intended to understand the process, identify streams and physical equipment, produce connected 2D/3D process representations, derive/inspect equipment sizing, estimate equipment costs, build a complete scoped CAPEX/OPEX/revenue/financial study, test alternatives and uncertainties, document sources and assumptions, and eventually perform authorised engineering/supplier workflows. Longer-term vision includes a time-aware/4D operational digital twin linked to real plant data.

**Core principle:** deterministic Python handles calculations, validation, economics and reconciliations. AI/LLMs may interpret unstructured engineering/commercial information, propose structured assumptions, select from *real implemented methods* and explain decisions. AI must not invent executable code, correlations, supplier quotes, physical connections, validated design conditions or financial arithmetic. User overrides and auditable evidence remain first-class data.

**Product differentiator the founder is pursuing:** capture and repeat the *reasoning workflow of a competent chemical engineering TEA analyst* — from interpreting unfamiliar project information through equipment design, costing, operating economics, financial decisions and eventually execution — with source-linked, editable and reproducible results. Do not narrow this to an MVP unless the founder requests a specific scope change.

**Scope hierarchy:** The canonical product specification at `docs/analyst-workflow-specification.md` and A–I roadmap at `docs/product-build-roadmap.md` are authoritative for the full product vision; they deliberately include capabilities not yet implemented. This onboarding file communicates context, not a new product specification.

## 2. The intended end-to-end workflow and data dependencies

```text
User process description + M&E/simulator data + explicit project context
                                |
                                v
              Source-specific import / canonical parser
               - streams, compositions, properties, units
               - source workbook/sheet/cell lineage
               - ambiguities, missing values, conflicts
                                |
                                v
                  Canonical process and equipment register
               - unique equipment tags and alias decisions
               - process duties and process connections
               - user-supplied designs vs inferred designs
                                |
                                v
                  Engineering equipment sizing/design
               - deterministic specialised Python methods
               - reviewed method choices and assumptions
               - physical conditions, materials and duty
                                |
                                v
                   Source-aware equipment costing
               - Garrett, Nottingham, future verified indexes
               - explicit sizing domain and costing scope
               - vendor comparable / approved manual overrides
               - year, index, currency, pressure/material factors
                                |
                                v
                         CAPITAL EXPENDITURE
               - equipment purchase & scoped installation
               - civil, piping, utilities, indirects, contingencies
               - construction, site, working capital, timing
                                |
          +---------------------+-------------------------+
          |                     |                         |
          v                     v                         v
    PROCESS INPUTS        OPERATING EXPENDITURE      REVENUE
    quantities & duties   - raw materials            - 6 MECE income categories
    product/operating     - utilities/consumables    - production/sales schedule
    schedules             - labour, maintenance      - commercial assumptions
                          - capital-linked costs     - avoided cost distinct
                          - fixed & variable         - saleable vs produced
          |                     ^                         |
          +---------------------+-------------------------+
                                |
                                v
              Canonical production / economic assumptions
                - same years, hours, ramp, throughput
                - applicable fixed/variable allocations
                - FCOP, VCOP and per-unit calculations
                                |
                                v
                     20-year financial model
                - annual P&L, project/equity cashflows
                - construction, debt, depreciation, tax
                - working capital, NPV, IRR, payback
                                |
                                v
              Editable dashboard, scenarios, reports/exports
                - one versioned study and coherent source basis
```

**Important calculation order:** The real orchestration in `backend/orchestration/pipeline.py` includes `equipment`, `capex`, `revenue`, `opex`, `financial`; **Revenue precedes final OPEX** for sales-dependent OPEX rates and avoided-cost interactions. A simplified conceptual diagram must not accidentally reverse this implemented dependency. Both Revenue and OPEX must share one production/operation schedule. Financial modelling must not independently ramp revenue a second time or double-charge depreciation/financing.

**Scope and canonicality:** purchased-equipment cost, installed-equipment cost, bare module, full CAPEX and whole-plant capital are different quantities; never add overlapping scope. An alias of the same physical equipment must not be costed again. Unpriced is not zero. User-provided engineering information, inferred engineering assumptions, market quotations and synthetic test prices must remain distinguishable. The original uploaded workbook should never be modified by normal parsing.

## 3. Current repository layout and important entry points

The following paths were checked or confirmed against the repository on 4 November 2026; always inspect the current code before making changes.

| Area | Path(s) | Responsibility |
|---|---|---|
| Development rules | `AGENTS.md` | Repository-specific Codex instructions, licensing and canonical-source order |
| Full product requirements | `docs/analyst-workflow-specification.md` | Founder scope and detailed acceptance requirements |
| A–I roadmap | `docs/product-build-roadmap.md` | Phases, dependencies and release gates |
| Backend API | `backend/api/app.py` | FastAPI routes, assessment and model catalogue API |
| Core orchestration | `backend/orchestration/pipeline.py` | End-to-end stages, canonical handoffs and staged failure handling |
| Orchestration contracts | `backend/orchestration/README.md`, `backend/orchestration/codec.py` | Input/output contracts and adapters |
| Ingestion | `backend/ingestion/` and existing parser packages | Source-specific parsing and canonical extraction |
| Source-stream mapping | `backend/orchestration/pipeline.py:source_streams` | Parsed, source-linked material rates |
| Engineering sizing | `backend/engineering_sizing/registry.py` | Allowlisted deterministic sizing methods |
| Sizing adapter | `backend/orchestration/sizing.py` | Selected sizing inputs to engine methods |
| Equipment costing API | `backend/equipment_costing/registry.py` | Cost source and exact model selection |
| Garrett index | `backend/equipment_costing/indexes/garrett/` | Historical equipment correlations, source metadata, factors |
| Nottingham index | `backend/equipment_costing/indexes/nottingham/` | CEEDG501 equipment equations and explicitly provisional chart models |
| Future cost indexes | `backend/equipment_costing/indexes/turton_et_al/` | Placeholder; directory existence does **not** mean implementation |
| Cost totals | `backend/equipment_costing/total_cost/calculator.py` | Equipment count, quantity, distinct cost scopes and subtotals |
| Cost escalation | `backend/equipment_costing/cost_to_future/` | Dated native/proxy indices, provenance, escalation |
| Currency | `backend/currency_conversion/` | Pinned, explicitly sourced FX conversion |
| CAPEX | `backend/capex/`, `backend/capex/README.md` | Factorial and alternative capital-estimation methods |
| OPEX | `backend/opex/`, `backend/opex/README.md` | Fixed/variable annual cost assumptions, categories, deterministic ledger |
| Revenue | `backend/revenue/`, `backend/revenue/MECE_ARCHITECTURE.md` | Sales, additional income categories, avoided costs and common schedules |
| AI commercial analyst | `backend/revenue/llm/COMMERCIAL_STRATEGY_ANALYST.md` | Optional reviewable commercial interpretation/research |
| Financial modelling | `backend/financial_modelling/`, `backend/financial_modelling/README.md` | Annual ledger, project/equity cashflows and investment metrics |
| Frontend | `frontend/src/`, `frontend/AGENTS.md` | Next.js views, editing, study navigation |
| Cloud | `backend/cloud/`, `backend/Dockerfile` | Supabase scoped assessments/RLS and Render deployment |
| User-facing catalogue | `GET /api/catalogue` | Advertises implemented sizing and equipment-costing models |
| Index reference documentation | `backend/equipment_costing/indexes/README.md` | Source-selectable index contract and limits |

**Run locally:** use Python 3.12, Node 24 where possible. From the repository root install `backend/requirements-orchestration.txt` and run `python -m uvicorn backend.api.app:app --host 127.0.0.1 --port 8000`. In `frontend/`, run `npm ci`, then `npm run dev`; navigate to `http://localhost:3000/entry`. See the root README and relevant package README for current environment setup. Keep secrets in local/server environment, not in Git.

## 4. Engineering model and method design philosophy

### 4.1 M&E and parser

- Start with the **actual** workbook's flows, units, headers and source-cell references, not inferred process values.
- Parser should accommodate diverse industry-style M&E exports over time, through explicit adapters; do not claim universal compatibility merely because an Excel test parses.
- Preserve original values and units plus normalised values and conversion evidence. Flag missing molecular weight, density, phase, heat duty, pressure basis, temperature basis or component mismatch where applicable.
- Equipment identification must distinguish a unique physical asset from alternative names, A/B spare units, aggregation and tag errors.
- Equipment-design calculation uses documented stream/equipment inputs and an engineering method; cost correlations consume the design output, not arbitrary tag names.

### 4.2 Deterministic sizing

Implemented method registry includes, among others: ion-exchange capacity and EBCT, vaporiser/exchanger area, gas compression/volume, phase-change duty, evaporated water, vessel hold-up, pump duty, filter area and dryer chamber sizing. See `backend/engineering_sizing/registry.py` for actual names, required parameters and allowable units. Missing parameters should be supplied through explicit user inputs/reviewable assumptions or an isolated test fixture; never imply the M&E supplied dimensions it did not.

### 4.3 Equipment costing indexes

Goal: **add source-specific calculation indexes so the workflow can select a compatible implemented method** by equipment service/type, sizing variable, unit, material, pressure, cost scope and validity domain. Selection may later be AI-assisted, but Python performs the arithmetic and validation.

- Garrett: historical book `Chemical Engineering Economics`, Appendix 1 and supporting tables; base-year/index distinctions must be explicit. Some plotted curves are approximations and remain flagged unverified.
- Nottingham: `CEEDG501 Cost Estimation – Capital Plant`. Separate equipment costing in `backend/equipment_costing/indexes/nottingham` from plant-level Nottingham CAPEX factorial/Lang models in `backend/capex/indexes/nottingham`. Index contains 2015 GBP pump motor-power equation, 2016 GBP fabricated-steel cost by mass, 2017 GBP pipe supply rate by diameter and two **unverified** 2012 GBP water-treatment package graph models. See source and limitations in the index README.
- Turton/etc: named placeholders are not implemented merely because files exist. Only advertise models executable through the shared registry.
- Supplier quotations and explicitly approved manual prices are legitimate, separately typed sources. A general inflation proxy is not a supplier quote or an independent cost model.
- Cost estimate provenance should include model ID, input values/units, equipment configuration, physical validity domain, price year/currency, escalation index, installation scope, factors, source reference, uncertainty and overrides.
- The **Charlie economics workbook's equipment prices must not be silently copied** as automatic fallback/index input; using or escalating an answer key is not independent costing. It may be reviewed as an external human-analyst comparison after independent calculation, but must not drive the estimate without explicit approval.
- An estimated equipment cost is not evidence that the engineering design or model choice is appropriate. Suspicious low model outputs also require scrutiny.

### 4.4 CAPEX

Equipment design → priced equipment subset → correct purchased/installed distinction → factorial/scoped plant investment → construction schedules and financial handoff. Existing registered CAPEX methods include Garrett, Nottingham detailed and Nottingham Lang variants (see `backend/capex/README.md`). Never stack Lang and detailed factorial calculations or count installation twice. A provisional subtotal built from priced equipment is not automatically complete whole-plant CAPEX.

### 4.5 OPEX

OPEX is **not simply a percentage of CAPEX**. The intended ledger combines:
- raw material flow × operating time × raw material prices;
- utilities/electricity/thermal duties × actual energy rates;
- staffing, shifts, maintenance, laboratory, consumables, chemicals, waste, insurance and other required costs;
- project-type and CAPEX-linked allowances where appropriate;
- fixed versus variable and production-attributable versus other operating costs;
- user/researched assumptions with source/date/currency and review evidence.

Current OPEX engine is deterministic with Garrett Chapter 4 as the documented implemented index. Founder task: research additional independent OPEX algorithms/indexes, keyed to project type, for eventual AI method selection. Ensure an actual input adapter forwards recognised percentage overrides into the engine.

**VCOP and FCOP:** the intended output explicitly includes variable/fixed cost of production and unit-cost views based on a declared relevant production denominator. The recent synthetic architecture diagnostic reported annual fixed and variable OPEX but **no separate VCOP/FCOP per-output metrics**. Do not report those as already delivered.

### 4.6 Revenue and OPEX interaction

The six current mutually exclusive, collectively exhaustive (MECE) revenue categories, from `backend/revenue/validation.py`, are:
1. `product_sales`
2. `processing_services`
3. `capacity_availability`
4. `infrastructure_usage`
5. `environmental_attributes`
6. `other_contractual_income`

The calculation boundary is `backend/revenue/engine.py:calculate_revenue`. Physical product sales are distinct from contract-based/commercial payments and from **avoided costs** (which lower an identified OPEX item rather than being added as sales). The system needs to identify appropriate categories from process/commercial descriptions and calculate them deterministically, preserving saleable/sold quantity, production hours, ramp, contracts/prices and user authority.

Revenue is calculated before final OPEX in the existing orchestration because royalty/sales percentages and avoided costs can depend on revenue/commercial conditions. Shared operational variables such as production hours and output quantity can feed both revenue and variable OPEX. **Revenue cash value should not automatically become a production expense.** Founder/co-engineer task: review all six methods and implement appropriate demo algorithms and category selection. The recent full synthetic test exercised `product_sales` only.

### 4.7 Financial modelling

The existing deterministic annual financial engine has one canonical ledger, not separate competing finance calculations. It supports construction/disbursement, depreciation, financing/debt, cashflows, working capital, NPV, IRR, payback and associated investment/unit economics. Reference `backend/financial_modelling/README.md` for implemented policies. Do not claim defined IRR when the cash-flow series contains no appropriate sign change; status can be undefined. Keep financial year, currency, price basis, start of production, construction and operating hours consistent across modules.

### 4.8 AI boundary and test modes

The full vision explicitly includes AI engineering judgement, context interpretation, method selection, sourced assumptions, commercial research, scenarios and agentic execution. However **the initial Python architecture acceptance test intentionally disabled all AI**:

- No OpenAI/API, LLM inference or online research.
- One deterministic test factor `TEST_FACTOR = 1.0` where a numeric factor needs a placeholder; dimensioned parameters require fixed valid, typed fixture values, not arbitrary multiplied physical quantities.
- Stub out the absence of an equipment correlation with deterministic test models while preserving actual Python module handoffs.
- Do not conflate a successful synthetic integration test with a validated price or chemistry.
- Test fixtures must remain isolated from production assessments, accepted baselines and live source files.

## 5. Human reference case: Charlie's M&E and economics

**Why this case:** a real human-prepared engineering design/economic exercise, useful as a moderately complex integration and engineering-judgement benchmark; neither workbook is guaranteed correct.

- Recent test reported **63 material streams and 32 unique equipment records** from Charlie's M&E workbook.
- One source file has been referred to as `M&E Balance V2 Team Charlie.xlsx` and a separate human economic reference as `Task 2 Charlie Economics 2(3).xlsx` (filename variants exist in notes). These private/workspace files may not exist in a new clone. **Do not assume they are present or commit personal datasets.** Ask the founder for an authorised share/fixture if unavailable.
- The economics workbook serves as **comparison and interpretation evidence**, not a pricing oracle. Do not automatically use its numerical purchase-cost entries to “resolve” equipment.
- Keep actual equipment identifiers, source references, aliases and independent costing provenance intact; do not manufacture duplicate assets.

### Seven specific unresolved purchased-equipment cases from the recent independent-pricing review

| Tag | Service / engineering question | Potential route / limitation |
|---|---|---|
| `C-201` | Spray dryer: quantify evaporative load, drying duty, chamber dimensions | Suitable spray-dryer price or comparable; do not substitute generic unrelated dryer without review |
| `PD-201AB` | Positive-displacement slurry pump; not a press/dryer | Need duty, model suitability; Nottingham generic power equation is not proven PD pump-specific |
| `R-101` | Electrolyser / hydrogen production system | Technology-specific $/kW/equipment scope or genuine comparable/vendor quote; historic workbook number is not an estimate |
| `R-201` | Possible independent reactor versus duplicate/tag inconsistency with `R-102` | Establish physical equipment and design duty before separate charge |
| `S-201` | Centrifuge at small capacity outside the relevant Garrett graph region | Small-scale centrifuge benchmark or supported sizing/cost model |
| `T-104` | Chemical storage (HCl/NaOH tag conflict; `T-103` may be separate HCl tank) | Confirm service, chemical/material and inventory basis |
| `T-105` | Pressure-rated liquid CO2 storage | Inventory, pressure, density and vessel design; fabricated mass cost alone is not full pressure vessel package |

**Alias-only records:** `T-101` → `T-101AB`, `FT-201` → `FT-201AB`, and `PD-201` → `PD-201AB` are proposed aliases and must not generate independent purchase charges. Verify actual equipment identity before treating proposals as final.

The earlier independent model review listed 22 priced, seven unpriced and three alias entries. Those are **review results, not verified engineering-valid prices**. In particular, extremely low small-equipment outputs require input/range/units/material checks.

## 6. Most recent Python architecture diagnostic (reported by Codex; not independently rerun in this document)

**Test purpose:** determine whether the Python chain can run from a real M&E workbook through financial results **if equipment indexes and all missing assumptions are artificially supplied**.

**Reported outcome:** the core pipeline completed all three scenarios, including **20 operating years, one construction year and a year-zero row**; 102 focused execution/reconciliation checks passed. No AI/network, production code edits or assessment modifications occurred during that diagnostic.

| Module | Reported assessment |
|---|---|
| `ingest.parse` | Data produced, but strict `BalanceReport` validation rejects additional `extracted_on` field |
| Equipment register | 32 unique records; connected |
| `sizing.derive_size` | Passed with typed synthetic sizing assumptions |
| Equipment costing → `calculate_total_cost` | Passed with synthetic costing model/installation factors |
| `calculate_capex` | Passed and fed downstream |
| `calculate_operating_study` → `calculate_opex` | Conditional pass; operating-study adapter needs to forward existing percentage override fields |
| `calculate_revenue` | Passed synthetic product-sales case only; five other MECE categories untested in this diagnostic |
| VCOP/FCOP | Annual fixed/variable OPEX present; separate per-unit VCOP/FCOP outputs absent |
| `calculate_financials` | Passed; annual financial ledger and NPV reconciliation |

**Test-only synthetic outcomes (USD):** baseline purchased equipment ~$9,859; CAPEX ~$443,655; fixed OPEX ~$2,218,272/year; variable OPEX ~$2,199/year; revenue ~$366/year; NPV approximately −$1.332m. Doubling one equipment price changed CAPEX and fixed OPEX/NPV; doubling operating hours changed source-based variable OPEX and revenue, without changing fixed OPEX or CAPEX. This is **not** an economic valuation of Charlie's real project. Synthetic factor overrides of 1.0, including percentage rates, are deliberately unrealistic.

**Four reported repair items:**
1. **P0 canonical schema mismatch**: `ingest.parse` emits `extracted_on`, strict `BalanceReport` rejects extra field. Align parser envelope and schema.
2. **P1 OPEX override handoff**: operating-study adapter drops percentage override fields. Pass the existing declared contract through normally.
3. **P1 separate VCOP and FCOP**: calculate explicit fixed/variable production cost metrics with a production denominator and consistent scope; annual fixed/variable totals already exist.
4. **P2 assumption provenance mismatch**: synthetic execution still labels some metadata as “AI study assumption” or “314 days” although the fixture used AI-free one-hour inputs. Derive evidence from saved actual inputs.

**What the diagnostic did NOT prove:** real equipment design adequacy; independent costing accuracy; five untested revenue categories; proper frontend reruns, edits and export; production cloud behaviour; supplier validity; project commercial feasibility. The result supports “calculation backbone connects under complete synthetic assumptions”, not “finished engineering product”.

## 7. Current six-task division of work (agreed 4 November 2026)

The new chemical engineer is a collaborator, not a replacement for the founder's decision authority. The actual Trello board is the operational task tracker and should be checked for updates.

| # | Task | Owner | Intended deliverable |
|---|---|---|---|
| 1 | Review economics book; populate Python engine with **dummy equipment costing indexes** | **Chemical engineer (colleague)** | Verify parsing and equipment calculations can execute with a complete synthetic costing catalogue |
| 2 | Research and improve OPEX algorithms; write independent OPEX indexes that AI can eventually select by project type | **Founder** | OPEX method/index research, documented deterministic calculation approaches |
| 3 | Research six MECE revenue methods, dummy algorithms and AI selection | **Founder + chemical engineer** | Complete candidate method definitions and testable category routing |
| 4 | Revisit M&E parsing and amend workbook/parser as needed | **Founder + chemical engineer** | Improved canonical parsing/stream-evidence quality |
| 5 | Redesign relevant FlowValue pages | **Founder + chemical engineer** | Connected UI design and editing workflow |
| 6 | End-to-end integration and acceptance test | **Founder + chemical engineer** | Upload → parse → identify → size → cost → CAPEX → OPEX → revenue → 20-year financials → dashboard/export, with verified recalculation and no unhandled failures |

**Task 6 acceptance defects:** track strict parser schema, OPEX overrides, VCOP/FCOP per-unit outputs and assumptions provenance. Do not assume the synthetic diagnostic automatically closed Task 6.

**Task ownership is descriptive**, not yet necessarily Trello member assignment or permission. Avoid editing somebody else's scope without coordination.

## 8. Engineering collaboration contract

When new engineer/Codex receives a specific ticket:

1. **Read this document, `AGENTS.md`, the canonical specification/roadmap and relevant module README/source.** State which parts are implemented and which remain proposed.
2. **Write a short task-specific engineering note** before changing methods: equipment category/service, governing equation, required properties, units, assumptions, applicability range, material/pressure conditions, literature page/reference, scope and independent check.
3. **Use source-driven deterministic Python** in the existing registry/index path rather than introducing a parallel engine, duplicate ledger, independent frontend calculator or ad hoc hardcoded Charlie costs.
4. **Preserve existing canonical data and API contracts** across ingestion, sizing, equipment costing, CAPEX, revenue, OPEX and financial modelling.
5. **Make synthetic versus real methods conspicuous**: a dummy costing factor exists only to test transport and arithmetic, not to assert engineering cost.
6. **Select among implemented methods only.** If the required model is absent, report that openly. Avoid pretending a placeholder index is executable.
7. **Avoid hidden circular dependencies.** Production quantities and schedules are shared; annual revenue is not automatically a cost; avoided costs are a separate adjustment, not product sales.
8. **Validate with focused tests**: equation units, source range, alias/quantity count, purchased vs installed cost, provenance, schema, CAPEX reconciliation and one relevant end-to-end handoff.
9. **Report changes and limitations**: modules/functions edited, index coverage, applicable tags, inputs, source year, result scope, tests executed, remaining unresolved cases, Git commit SHA.
10. **Coordinate changes** through Trello and source control; prefer a working branch and review when collaborating. Do not force-push, overwrite a colleague's changes, mutate a verified baseline or deploy without explicit agreement.

### Definition of an independently usable costing model

A model is **usable**, not merely present, when it has a registered ID/source, a real Python calculation, typed sizing inputs/units, known scope (purchase/installed/unit), price basis year/currency, a documented source, validity/application limits, appropriate factors and at least one independently checked case. If only a generic metal-fabrication mass cost exists, do not label it a complete electrolyser, reactor, tank or turnkey package price.

### Definition of a successful end-to-end test

A real M&E workbook is parsed by the actual parser; equipment and stream identities remain traceable; every intended calculation module executes via its canonical inputs; no required schema conversion silently drops data; all cross-module handoffs reconcile; editable assumptions trigger consistent recalculation; UI/dashboard and exports show the same saved scenario. Where synthetic indexes are used, report success as **software execution only**, not verified financial accuracy.

## 9. Full platform vision that must remain visible during task-specific work

Beyond the currently testable engine, the founder has explicitly described:
- Process intake from simulation outputs, data and/or prompts, with source-specific supported adapters.
- Interactive 2D/3D process representations/connections, with future time-aware 4D/digital twin behaviour.
- Engineering intelligence that identifies equipment, sizes it when necessary and captures the engineer's decisions and justifications.
- Source-linked equipment, materials, installation, construction, staffing, CAPEX/OPEX and full financial/economic analysis.
- A resource/supplier intelligence layer with research, potential vendor choices and **authorised** enquiry/drafting/execution.
- Project-specific pricing and assumptions, user editing, baseline protection, alternatives, sensitivity and Monte Carlo uncertainty.
- Dashboards and auditable editable engineering/economic study outputs and exports.
- Potential actual-plant data connectivity for monitoring, model-versus-actual research and operational integration.
- Robust engineering assurance and eventual independent industrial evaluation.

These goals are *not statements that all features work today*. Preserve the existing 10-point founder framing in the canonical specification and do not rewrite the roadmap based on this brief.

## 10. Suggested first message to the new engineer's Codex

```text
You are joining FlowValue AI as the coding assistant to a chemical engineer.

First read, in order:
1. docs/FLOWVALUE_ENGINEER_ONBOARDING.md (entire file)
2. AGENTS.md
3. docs/analyst-workflow-specification.md
4. docs/product-build-roadmap.md
5. The actual files and source documentation needed for my assigned Trello task.

Do not start coding until you can state:
- The complete intended end-to-end data and calculation flow.
- Which modules are genuinely implemented versus planned.
- The equipment sizing → equipment costing → CAPEX → OPEX/revenue → financial modelling boundaries.
- What the November 2026 synthetic Python integration test actually proved and its four gaps.
- Which work belongs to me and which belongs to the founder.

Then inspect the current branch and assigned task. Make only scoped, reviewable code changes, with explicit engineering evidence and focused tests. No AI guesses or provider calls during deterministic architecture tests. Never copy Charlie's equipment economic answer prices into automatic costing indexes. Keep source provenance, units, cost scopes, manual overrides, and full product vision intact. Report code paths, test results, unresolved assumptions and commit SHA.
```

## 11. Document maintenance

Update this document only when a meaningful founder decision, verified architectural change, corrected scientific method or tested integration result requires it. When updating:
- Date the change and distinguish **reported test outcome** from independently reproduced test evidence.
- Keep historical experiments separate from current source-of-truth code.
- Prefer linking to exact code/modules and existing specifications over copying large dynamic technical manuals into this file.
- Never include credentials, personal financial data, private workbooks, vendor confidential quotations or full proprietary source PDFs.
- Preserve the full product vision; do not replace it with a temporary demo-only milestone.

**Immediate next step for the new engineer:** open Trello Task 1, inspect the equipment register and implemented indexes, specify new dummy-index coverage separately from real price correlations, and use the existing deterministic Python pipeline to identify which equipment design and cost handoffs need work. Report findings before changing other owners' modules.
