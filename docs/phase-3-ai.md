# Phase 3 — AI configuration and acceptance

The dashboard has a secret-free AI connection panel. `GET /api/copilot/status` reports not configured, administrator-disabled, or configured. Configured means a server key exists; it does not claim provider access or billing capacity. `POST /api/copilot/check` explicitly retrieves the configured model to test authentication/model access without generating text. It does not verify generation quota or web-search compatibility. Both endpoints require authentication in public deployment.

## Server configuration

Set `OPENAI_API_KEY` only in the backend hosting provider's environment, never frontend variables, project data, source control or browser storage. `OPENAI_MODEL` defaults to `gpt-5.4-mini`. `AI_ENABLED=false` disables all generation/diagnostics even if a key is present. After a hosting restart, use **Refresh AI status**, then **Check AI connection**. A real research/memo request is still needed to confirm generation/billing/tool access.

The owner previously requested deploying without the key. Cloud activation remains pending explicit authorization; the local backend has its separately configured development key. Adding a key enables AI for signed-in application users and incurs provider usage charges. Application-level budgets/quotas are part of production hardening.

Research sends the computed cost profile, question and optional market context to OpenAI Responses with live web search filtered to primary-source domains. Original files, raw unknown project fields and application authentication tokens are not forwarded. Slider suggestions remain deterministic and only apply on user click. Results have linked citations, evidence status, model and retrieval time; factual claims still need human source review. Interrupted or unsourced output is not presented as an established briefing.

Memos use recomputed BOM/DCF/sensitivity data. An explicit economic summary prevents treating feedstock/utilities as costs additional to variable OPEX. Memos have a generated timestamp, model and computed-scenario evidence label in the UI/download. Incomplete provider output is rejected. A changed scenario marks the prior memo stale and blocks its download. No live research is performed for memos. Both API paths request `store=False`; provider data policies still apply.

## Verification

- Tests cover missing/configured/disabled state, secret non-disclosure, authenticated diagnostics, model access, sanitized provider errors, recomputed memo data, explicit OPEX accounting, provenance and rejection of incomplete provider output.
- Local model-access check succeeded using the existing development configuration.
- Local demo memo generated/downloaded, with $500,000 total annual OPEX (fixed + variable; feedstock and utilities already included). Initial AI double-counting was caught during review and corrected by explicit computed summary/prompt instructions.
- Local live market research completed with clickable primary-source citations, model and retrieval time. Commentary is an AI draft requiring claim-by-claim review.
- Changing utility assumptions blocked the stale memo download.
- Production missing-key state and deployment checks are recorded after rollout. Enabling a cloud key remains a separate owner decision.

API behavior follows the [official web search guide](https://developers.openai.com/api/docs/guides/tools-web-search). Connection checks do not substitute for checking the accuracy or completeness of generated analysis.
