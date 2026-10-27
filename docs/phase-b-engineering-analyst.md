# Phase B — unit investigation and saved-revision peer review

## Delivered behaviour

The engineering analyst panel investigates each BOM unit or explicitly registered unpriced unit. The dashboard and selected-node 2D/3D inspector use the same investigation component and versioned study state. Display geometry remains schematic. Unsupported valves/other equipment stay unpriced until a reviewed assembled-unit quotation is supplied.

A service record contains composition/concentration/impurity basis, phase, normal/design temperature, design pressure, food-contact flag, cleaning regime, corrosion/erosion conditions, material rationale, a hypothesis and counter-evidence. Wetted material, structural shell and lining/cladding are distinct fields. No process conditions are invented from stream order or a process name.

Deterministic investigation rules return prioritized questions and provisional material options, source links, unsupported scope and missing evidence. Supported heat-exchanger/vessel/reactor-shell/pump/compressor sizing reuses existing numerical engines. Stainless factors are generic proxies, not grade-specific quotes. Composite/lining/special-material assemblies and unsupported equipment require assembled quotations and linked quotation evidence. Sizing ranges, pressure mismatches, absent conditions and unreviewed evidence block baseline application.

A user explicitly reviews compatibility and mechanical scope, supplies a reviewer/basis, and confirms a preliminary unit baseline. The server validates the proposal before changing the BOM. Prior baseline records remain in study history. Input fingerprints cover service/proposal, design basis, linked evidence, applicable equipment/cost settings and rule version. Edits can mark a baseline stale; linked engineering edits also invalidate applied OPEX review. Summaries appear in assessment/export notes; full unit/study JSON records retain detail. These records are user reviews, not independent mechanical/material certification.

## Research and source limits

Optional unit research uses the existing configured OpenAI model, one explicit request, at most two tool calls, 2,500 output tokens, no retry and no provider-side response storage request. It sends an allowlisted selected service/hypothesis and bounded design-context excerpt, not raw project/files/tokens. It searches a fixed primary manufacturer/regulator/research domain list. The UI exposes charges/data use before the button, clickable returned citations, timestamp/model/prompt version and stale-input state. Incomplete or uncited results are labelled insufficient evidence. Narrative never changes quantities, costs, suitability decisions or baselines automatically.

The deterministic path works without paid generation. Development tests mock provider responses. Full-depth metallurgy, corrosion testing, hygienic validation, NPSH design, compressor staging and pressure-code certification remain outside the sizing proxies. A source citation or checkbox cannot prove actual-service compatibility.

General sources reviewed 2026-10-27:

- https://www.outokumpu.com/en/products/corrosion-tables — source-condition limits and material-selection evidence requirements.
- https://www.govinfo.gov/content/pkg/CFR-2025-title21-vol2/pdf/CFR-2025-title21-vol2-sec117-40.pdf — dated US food-equipment guidance context; applicability elsewhere is not inferred.
- https://developers.openai.com/api/docs/guides/tools-web-search — research-tool filters, citations and user-visible source links.

The inspiration workbook is not a calculation source, fixture, calibration target or authority.

## Peer-review workflow

1. Save a project revision containing the investigation. Open the engineering review centre from Accounts & saved projects.
2. A reviewer signs into their own FlowValue account and gives the owner the account UUID displayed in that centre. No account is created and no invitation/email/call is sent by this workflow.
3. The owner explicitly grants that exact account read access to the entire selected saved revision, including financials/streams/study evidence. Grants do not include later revisions or permission to edit the owner's saved model. The UI states the scope before confirmation.
4. Authorized reviewers record comments, challenges and agreement. Events use authenticated account IDs and server timestamps. Only the owner can resolve challenges, with an explanation tied to a same-unit/same-revision challenge. Agreement is not certification.
5. Open challenges on the selected saved unit block baseline application. The working dashboard remains a separate editable scenario; a changed revision must be saved/shared explicitly. Refresh to retrieve other reviewers' latest comments.
6. The owner can revoke future revision access. Downloaded copies cannot be recalled. Shared revisions load read-only in project history; a reviewer can save their own separate copy.

Review access/events use row-level security and the caller's bearer token, without a service-role key or SECURITY DEFINER function. Composite foreign keys enforce version ownership and parent-challenge scope. Events have no authenticated UPDATE/DELETE grants. Owner-only project-head write policies remain unchanged. Existing private revisions remain private unless the owner creates a grant.

## Verification

- Independent sizing arithmetic, service/food/composite gates, quotation requirements, evidence/date checks, baseline round-trip/staleness, permission/API failure cases and bounded mocked research.
- Transactional SQL fixture `supabase/tests/engineering_peer_review_rls.sql` exercises synthetic owner/reviewer/stranger identities, exact-revision scope, read-only access, no resharing, no forged authors, append-only events, owner-only same-unit resolution, revocation and anonymous denial. It rolls back all fixtures. Initial cyclic policies were corrected to constraint-based ownership/parent checks before application rollout.
- Existing financial/reference/export tests remain applicable; no financial method was copied from the supplied workbook.
- Database security advisor has an existing leaked-password-protection warning; no new review-table RLS warnings. This does not establish an independently audited security posture. See https://supabase.com/docs/guides/auth/password-security#password-strength-and-leaked-password-protection .
