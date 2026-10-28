# FlowValue AI — repository instructions for Codex and other development agents

## Source-of-truth reading order

1. [Canonical founder product specification](docs/analyst-workflow-specification.md): full unchanged product vision, scope and acceptance requirements.
2. [Complete A–I build roadmap](docs/product-build-roadmap.md): phases, dependencies, test gates and status. Read the **R39 cross-phase roadmap** before implementing natural-language opportunities.
3. For relevant implementation work: [AI/research](docs/phase-3-ai.md), [calculation basis](docs/calculation_basis.md), [process/engineering integration](docs/phase-4-engineering.md), [unit analyst](docs/phase-b-engineering-analyst.md), and [future release gate](docs/phase-5-release.md).
4. Under `frontend/`, also follow [Next.js instructions](frontend/AGENTS.md).

These are product requirements and proposed acceptance criteria, **not proof of implemented functionality**. Respect the founder's existing broad end-to-end platform scope; do not silently narrow, expand or discard it. Historical phase acceptance docs report past checks and must not be rewritten as newly delivered claims.

## R39 — planned natural-language commercial opportunity workflow

Founder example: **“We get revenue from food. Could we sell our wastes?”**

- Interpret the idea into a **reviewable draft additional revenue scenario** linked to the actual waste/by-product stream where known. Capture material quality, saleable quantity, volume sold, location, price/units/basis, extra logistics/processing cost and evidence. Missing information remains explicit; never invent a mass balance, market price, or signed contract.
- If the user supplies a price, record it as a **user assumption** and calculate a preview. If price is missing, **ask permission** before any external research. Return possible comparable prices with dated citations, and prospective buyers and buyer requirements where verifiable.
- Evaluate the **likelihood of winning a buyer/contract**, but give a numeric probability only with an explicit defensible calibrated basis; otherwise mark numerical probability not estimable. Public listings are neither commitments nor signed contracts.
- Hand user-reviewed assumptions to **validated deterministic engineering/economics engines**. Recompute separate revenue, incremental costs, cash flow, NPV/IRR and other affected metrics. Refresh Revenue, Scenario, Main dashboard charts and applicable 2D/3D stream annotations; preserve baseline-versus-preview comparison and the original project/version history.
- Build and test across **A structured proposals → B real stream mapping → C multi-revenue economics → D opted-in sourced research → E visual/report reconciliation**. The acceptance cases in the spec and roadmap (price given, price missing, refusal, insufficient market/stream data, unsupported contract probability, scenario editing and baseline restoration) are mandatory gates.

## General safeguards

Do not replace engineering analysis with AI-generated arithmetic or unsupported confidence scores. Do not silently modify an approved baseline, create physical connections from an economic idea, or contact buyers/suppliers without separate authorisation. Reconcile financial outputs and exports from the same saved scenario; test source lineage, user permissions, invalid units, incomplete data, versioning, and end-to-end UI behaviour before declaring any feature complete.

## Canonical Entry-file parser scaffolds (17 methods; deliberately empty)

Before implementing or changing ingestion, read [the input parser directory index](backend/app/parsers/inputs/README.md) and the UI source `frontend/src/lib/import-methods.ts`. Exactly one **headed but otherwise empty** Python module now exists for each dropdown selection at `backend/app/parsers/inputs/`. These are **future adapter stubs**, not working parsers, registered routes or a promise of support. Implement them **one at a time with the founder**, keeping source provenance and the canonical stream/balance models intact. Preserve the current working Excel, CSV, JSON, DWSIM and trusted BioSTEAM paths until independent tests and a reviewed migration justify replacement. Do not execute uploaded simulator scripts or claim PDF/Word/image/OCR capabilities from the existence of a stub.
