# FlowValue AI specialists: responsibilities and authority (M5.1)

**Date:** 12 November 2026 · **Owner:** Engineer 1

These rules apply to every specialist:

- **No tools.** The only exception is user-triggered research, which is limited to bounded web search.
- **Bounded output.** Answers come back in a strict JSON schema that Python validates.
- **No arithmetic or code.** Python does every calculation. AI text is never executed (benchmark: `no_ai_formula_executes`).
- **Proposals only.** Nothing an AI proposes changes an approved baseline, a locked section, a user's model choice, an approved price or an alias confirmation (benchmark: `no_autonomous_baseline_change`, `zero_approval_bypass`).
- **Logged.** Every call and cache hit is recorded in the AI decision log ([`ai_audit.py`](../../../backend/orchestration/ai_audit.py)) with the model, prompt version and content fingerprints.
- **Model-pinned cache.** The response cache key includes the model.

| Specialist (roadmap role) | Module | May propose | May not | Output goes to |
|---|---|---|---|---|
| Workbook engineer (process engineering) | `orchestration/workbook_review.py` | Stream, equipment and product identities and names; cell citations; aliases to confirm; scope notes | Change a numeric value or unit; merge separate sheets or cases; assume extra units from supporting sheets | Engineering data review; the user approves |
| Equipment matcher (equipment) | `equipment_matching/service.py` | A catalogue model family and configuration per item, with its reason | Choose a model outside the catalogue; size, price or pick factors; override a user's model choice | Equipment register; the user can confirm or switch per item |
| Input router (equipment) | `equipment_costing/unit_conversion/bridges/automatic.py` | Which workbook observation feeds each model input | Do arithmetic (Python derives sizes); cite a source that doesn't exist | Python sizing |
| Design handoff (equipment → chemical engineer) | `orchestration/design_handoff.py` | A preliminary design value, unit and rationale for an input that can't be derived | Rewrite locked or priced equipment; present a value as measured | Labelled assumption, editable; assumption tier (M3.7) |
| Assumption completion (chemical engineer) | `.../bridges/assumption_completion.py` | Only the missing parameters, with unit, rationale and limitations | Replace an existing input or price | Labelled assumption, editable |
| Reference repair | `orchestration/reference_repair.py` | Fixes to invalid register references | Change any number | Register |
| Capital adviser (cost) | `orchestration/capital_advisor.py` (via `advisor.py`) | CAPEX method and factor selection from the registered methods | Invent a source-backed price | CAPEX section, reviewable |
| Operating adviser (operations) | `orchestration/operating_advisor.py` (via `advisor.py`) | OPEX quantities, prices and staffing as labelled assumptions; finance planning defaults | Execute arithmetic; mark an assumption as verified | OPEX and finance sections; the user reviews |
| Commercial interpreter (commercial) | `revenue/llm/commercial_interpreter.py`, `revenue/advisor.py` | Payment lines only for mechanisms stated in the Revenue Box | Create revenue without Revenue Box authority; invent buyers, licences or prices | Revenue section; requires revenue approval (fingerprint) |
| Commercial strategy analyst | `revenue/llm/commercial_strategy_analyst.py` | Scenario-only payment, research and pricing policies | Change the baseline; execute formulas; give a contract probability without a basis | Scenario drafts |
| Price review / research | `revenue/price_review.py`, `orchestration/deep_research.py` | Dated, sourced comparable prices, only after consent | Apply a price; use an unsourced number | Drafts the user accepts |
| Analyst team (engineering review) | `orchestration/analyst_team.py` | Independent reviews for contradictions, missing scope and unsupported decisions, with disclosed ownership | Edit the plan; use fabricated evidence | Review findings feeding the proposals |
| Uncertainty adviser | `scenarios_and_uncertainty/monte_carlo/advisor.py` | Ranges for parameters that have none, with source and rationale | Overwrite an existing central value; call the AI per iteration | Monte Carlo settings, reviewable |

## Known limits

- **Per-assumption approval (M5.4).** Approval records for each OPEX and CAPEX assumption are not yet built; those sections are approved by section edit.
- **Live-model quality.** It has not yet been measured on a clean held-out project (M5.5, M5.7).
