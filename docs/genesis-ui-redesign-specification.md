# FlowValue Genesis — UI redesign implementation specification (v2)
Date: 2026-11-16
Status: implementation brief; **not evidence that the visual redesign has been completed**
Baseline: `main` at `f711bdc68985da82ee2b555f287d26bac06bdba9`
Primary visual reference: founder-supplied 10.2-second dashboard animation (2000 × 1500, 60 fps)
Supporting reference: Playworks “Main Dashboard – User Activity & Spending Stats UI Animation” (Dribbble shot 27206583)

## 1. Design acceptance: structural fidelity, not recolouring

Genesis means reconstructing the reference's visual grammar while retaining FlowValue data and behaviour. The video shows an inset, rounded white application canvas on a warm-neutral outer background; a thin, light left sidebar; compact breadcrumb, utility controls and profile in the header; a quiet filter-chip row; a dashboard title/subtitle; three matching analytics cards across the top; and a wide, substantially taller analytics chart below. Data and chart changes animate while their surrounding layout remains stable. It is **not** sufficient to add sea-blue colours to the legacy shell.

Deviation from the reference: replace violet/purple with sea blue and offer a carefully designed dark theme. Use proprietary original implementation, not copied third-party source code or assets.

## 2. Current application: correct navigation and user journeys

Do not design against obsolete page inventories. The current frontend source establishes TWO experiences:

### Simple workspace — guided flow (`/flow`)

Six stages in the canonical `guidedStages` order (`frontend/src/lib/guided-flow.ts`):
1. **Entry** (`stage=entry`)
2. **Equipment** (`stage=equipment`)
3. **CAPEX** (`stage=capex`)
4. **OPEX** (`stage=opex`)
5. **Revenue** (`stage=revenue`)
6. **Financial** (`stage=financial`)

Owned by `frontend/src/blocks/guided/flow.tsx`; `/entry` routes into `/flow` unless `classic=1`. Simple displays a horizontal six-stage rail today. Keep status indicators, keyboard focus movement, navigation history, preserved draft edits, reset confirmations, run progress, saved assessment id, and the Advanced workspace handoff. Apply Genesis's spacing, surfaces, type and motion to the **guided experience**, not a transplanted Advanced sidebar.

### Advanced workspace — detailed analyst navigation

`frontend/src/components/workspace-navigation.tsx` defines:
- Entry (`/entry`)
- **TEA overview** (`/main-dashboard`)
- **Engineering data** (`/data/equipment`)
- **Equipment** (`/capex/equipment`)
- **CAPEX** (`/capex`)
- **OPEX** (`/opex`)
- **Revenue** (`/revenue`)
- **Cashflow** (`/cashflow`)
- **Financial model** (`/financial-modelling`)
- **Scenario & Sensitivity Analysis** (`/scenario-and-sensitivity`)
- **Monte Carlo** (`/monte-carlo/setup`); nested **Parameters & setup** (`/monte-carlo/setup`) and **TEA overview** (`/monte-carlo/overview`)

Recommended visual grouping in Genesis (navigation grouping only; do not change URLs or engine stages):
- **Workspace**: Entry, TEA overview
- **Engineering**: Engineering data, Equipment
- **Economics**: CAPEX, OPEX, Revenue
- **Financial analysis**: Cashflow, Financial model, Scenario & Sensitivity Analysis, Monte Carlo and its child pages

Keep the **Simple workspace** return link, the active assessment selection, deep links, and page-specific subnavigation (including CAPEX child pages where actually exposed). Do not present unimplemented modules as navigable products. Code/route-level sections listed above are verified; deployed production navigation could differ if the deployment lags GitHub `main`.

## 3. Target visual composition (match primary video)

### Desktop outer shell
- Warm off-white outer background: initial token `#F1EEE9`.
- Large white inset app canvas: `#FFFFFF`, 18–22px radius, slim border, minimal shadow, 20–28px outer gutter on wide screens.
- Sidebar ~210–235px at reference scale; thin vertical separator, icon+label links, light surface; never reuse the forest-green slab.
- Main area includes ~56–68px contextual top toolbar: breadcrumb at left; utility/theme/profile at right. Maintain one top toolbar in each workspace, not duplicated account/theme controls.
- Content width fills available space with airy 24–32px gaps; avoid huge unexplained whitespace or clutter.

### Advanced TEA overview — above fold
- Row 1: compact chips like the video (Sort, Today, Yesterday, 7D, 30D, 3M, 6M, 12M) **only for meaningful, supported dimensions**. For FlowValue, use actual model years/periods or scenario controls; unsupported date ranges must be disabled/omitted, never fake interactive.
- Row 2: concise `TEA overview` heading and explanatory subheading.
- Row 3: **exactly three balanced cards** in a desktop grid, approximating video proportions, each with title, short subtitle, core metric/chart; preferred content: saved CAPEX metric, compatible revenue/OPEX comparison, and actual-model-year financial trend. Statuses and currency basis visible.
- Row 4: **one large, wide lower analytics panel**, chart with compact legend, light grid, discrete hover/focus marks and restrained sea-blue visual emphasis. Use real saved data; do not invent scatter data, prices or historical time series to mimic reference aesthetics.
- Further detail pages/receipts/tables may follow below fold rather than squeezing every engineering control into the first screen.
- Responsive: KPI row becomes two then one column; chart width, legend and filters adapt without horizontal page overflow.

### Sidebar detail
- Search only if functional; otherwise omit search rather than inert decoration.
- Semantic grouped section labels, thin-line icons, compact indented children.
- Sea-blue active state with light tinted backing; hover/focus visually distinguishable.
- Desktop collapse reduces the entire sidebar width, not just hides nav entries; mobile becomes keyboard-accessible dismissible drawer.
- Preserve navigation targets and assessment query parameters.

## 4. Theme, typography, and accessibility

Initial theme tokens (calibrate via image comparison):
| Token | Light | Dark |
|---|---|---|
| outer | #F1EEE9 | #0B141B |
| canvas | #FFFFFF | #13232D |
| card | #FFFFFF | #192E3A |
| primary sea blue | #087E9C | #5BC7E4 |
| soft accent | #E7F5F8 | #183C4A |
| primary ink | #182B35 | #EDF7FA |
| muted ink | #647580 | #ACC2CE |
| border | #E5EAED | #35505E |

Use a modern sans-serif with deliberate type scale; KPI digits ~34–44px, dashboard heading ~24–28px, card headings ~15–18px and secondary labels ~12–14px. Shared spacing scale, card radius ~12–16px and near-invisible elevation. Test both themes on charts, drawers, inline validation, tables, badges, disabled buttons and focused elements. Persist preference and prevent a theme flash at initial paint.

## 5. Motion specification

Reference behaviour: changing filters causes smoothly changing KPI digits, bars and chart traces while cards do not jump around. Establish reusable timings: hover 120–180ms; chip selection 150–200ms; panel/navigation 180–300ms; chart transitions 300–500ms. Respect `prefers-reduced-motion`. Never animate fabricated values or imply a completed calculation, approval or verified source before backend confirmation. Display `Not calculated`, `Provisional`, `Stale`, `Awaiting approval` and `Unresolved` when applicable.

## 6. Migration: preserve functionality

- Simple stage layouts: restyle actual `EntryStart`, `EquipmentPlayground`, `CapexPlayground`, `OpexPlayground`, `RevenuePlayground`, `FinancialPlayground`; preserve stage transitions and draft safeguards.
- Advanced engineering: Engineering data and equipment source/identity review, evidence, sizing/edit controls.
- Advanced economics: CAPEX, OPEX, Revenue component trees, financial summaries, evidence and approvals.
- Analysis: Cashflow, Financial model, Scenario & Sensitivity Analysis, Monte Carlo setup/overview.
- Continue using saved Python results; missing numbers stay missing. Preserve statuses, receipts, versions, source lineage and recalculation semantics.
- Preserve current API integration, routes, assessment context and export outputs.

## 7. Implementation checkpoints and review gates

**G-UI-01 Shell**: Replace legacy structural shell with the inset canvas, proportioned sidebar, compact toolbar and responsive navigation. Demonstrate desktop and mobile screenshots for both themes.

**G-UI-02 Advanced overview**: Implement reference-faithful filter/header/three-card/wide-chart composition using real saved assessment data. Capture comparable screenshots at same viewport and reference video frames at ~1, ~3, ~6 and ~9 seconds. Do not call complete until visual composition is reviewed.

**G-UI-03 Simple workspace**: Apply identical Genesis visual language to all six guided stages without changing their process order or navigation semantics.

**G-UI-04 Advanced workspaces**: Apply shell and component language to all 11 Advanced navigation entries, nested Monte Carlo destinations, and applicable subpages.

**G-UI-05 Motion & QA**: Verify real-data transition behaviour, dark mode, drawers, chart expansion, keyboard, focus, mobile widths, reduced motion and loading/error/empty/stale states. Run TypeScript, production build, frontend and selected backend regression tests. Report verification distinctly from code commits.

## 8. Explicit anti-goals and completion criteria

Anti-goals: colour-only redesign; stacked override CSS as the sole architecture; fake KPI data; fabricated historical periods; decorative inactive filters; renaming/rearranging canonical workflow stages; mutating numerical engine logic; breaking existing saved assessments; copying third-party UI source.

Acceptance is **visual and functional**: independently recognisable resemblance to the supplied video in screenshot comparisons; real and legible engineering/financial information; integrated Simple and Advanced experiences; verified browser interaction and regressions. Automated unit tests alone do not establish design acceptance.

## 9. Working practices

The founder has explicitly authorised work on GitHub `main` for Genesis. Fetch/inspect latest remote state before changes, commit small coherent increments, never force-push, keep unrelated changes untouched. Frontend/AGENTS.md and root AGENTS.md continue to apply, except where founder explicitly overrode branch selection. Treat design specification as the implementation contract; do not claim that writing the specification implements the redesign.
