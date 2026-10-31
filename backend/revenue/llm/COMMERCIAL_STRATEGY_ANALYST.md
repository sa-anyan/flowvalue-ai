# Commercial Strategy Analyst

Explicit scenario agent, version `commercial-strategy-1`. This is a named FlowValue application agent using the existing configured LLM provider, not a separate model or a Codex subagent.

## Local workflow

On Revenue, enter an updated process/commercial description and click **Run Commercial Strategy Analyst**. The optional checkbox authorises bounded external price research and associated provider charges. The API is `POST /api/assessments/{baseline}/commercial-strategy` with `revision`, `description`, `research_consent`.

A separate assessment is created. The original remains unchanged. The agent reads the updated description, canonical engineering register and existing commercial inputs, identifies distinct receipts and selects stream relationships. It chooses retained prices/terms rather than retyping the existing calculation. Python copies those inputs from the actual saved baseline. For retained cost-plus sales, this prevents additional fees simply lowering the required target water price. This is an explicit comparison policy, not evidence of market sales prices.

Unknown tariffs trigger research only with consent. Recent sourced agent research may be reused for the identical baseline and description for up to24hours; the agent still makes a fresh selection. Evidence from unrelated projects, changed descriptions or expired retrievals is excluded. The existing research tool searches external sources and extracts bounded source-linked candidates. The strategy agent selects a candidate and explains comparability, source date, billing units and price-basis policy. Python checks candidate identity, source membership, currency, billing denominator and canonical units. Python alone calculates rate normalisation, optional explicit CPI purchasing-power comparison, annual income, revenue-dependent OPEX, tax, cash flow and investment metrics through the existing engines.

No generated arithmetic or executable LLM code is accepted. Unknown prices or unsupported currency/date conversions remain unresolved. An unresolved scenario does not display a stale baseline financial result. Research and strategy audits are retained when validation stops a run.

## Current boundaries

This implementation reproduces the analyst task for volumetric treatment services alongside existing sales. It preserves equipment/CAPEX, staffing, other OPEX and financial policies. It does not automatically reassess the entire plant design, certify water quality or claim to negotiate a contract. It can retain saved commercial payment schedules, but broad tariff mechanisms, FX, daily/seasonal contracts and non-volume price normalisation need separately validated extensions.

The optional CPI comparison uses sourced public annual observations (1987,2024,2025). It is an explicit, approximate purchasing-power assumption, not a wastewater-specific price index, observed historical tariff or CEPCI adjustment. Annual1987 versus early1987 costs is approximate. The agent must expose this limitation. No unsupported comparison year or FX rate is invented.

The action creates and calculates a conditional scenario; it does not approve an existing baseline. Saved assumptions remain editable and Python-only reruns do not call an LLM. Review the decisions and sources before use.

## Verification

Unit tests cover price arithmetic, source/date/currency controls, missing candidate handling, baseline quantity/price retention, research refusal, agent-to-Python routing, failure audit and independent-scenario API creation. Broader pipeline tests remain required. Live M&E8 execution records and any failed attempts are in private `outputs/commercial-strategy-agent/`.
