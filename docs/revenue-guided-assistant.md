# Guided Revenue assistant — 8 November 2026

Local implementation; no production release requested by this task.

Revenue now exposes a primary conversational description and one commercial-review
modal. It reuses saved operating days/hours, currency/period, measured stream IDs,
product prices and sales fractions. The AI interpretation uses the existing explicit
Revenue authority endpoint and polling; it cannot approve its own proposal. The
interpreter prompt requests one combined, consequential clarification per source,
reuses known values and discloses neutral optional contract assumptions.

The modal permits price, sales fractions, operating calendar and product-stream
edits. Commercial lines show saved first-year payment terms and allow an explicit
flat rate across existing annual rows. Detailed annual terms stay in the existing
Revenue drawer. User approval and deterministic Python calculation are combined
in one action; no provider call occurs when calculating reviewed inputs. Errors
remain in the modal. No research is automatically authorized, and missing prices,
quantities or revenue intent are not fabricated. Pending sources still require
resolution; the assistant does not bypass commercial validation.

Browser verification exposed JSON number formatting changing 1.0 to 1 on save.
Revenue approval now applies the same canonical calendar normalization as stage
execution before fingerprinting. A regression test covers browser-style numeric
serialization, manual edit, approval and Python Revenue execution.

Tests cover source identity, true zero prices, no invented income, explicit review,
commercial authority and the calendar approval regression. Live AI question quality
has not been evaluated with paid provider calls in this task; prompt changes alone
do not establish semantic accuracy for all projects. This is a guided workflow
upgrade, not a replacement financial calculator or universal conversational agent.

Browser result: synthetic dashboard-verification.xlsx assessment, user price edit
1 → 2, explicit review, then Python-only coordinated economic execution. After
normalization fix, Revenue displayed Approved, saved calculation, no issues, and
annual year-one income USD 11,454,720 on its retained price/index basis. This is
a synthetic workflow check, not Charlie pricing validation or a market quote.

## Question cards — 9 November 2026
The repeated description inside the commercial review modal is replaced by
one-question cards, radio answer options, a short custom-answer field, back/next
controls and an explicit Apply answers & interpret action. Answers supplement the
original commercial statement; selecting an option alone changes no saved plan.
Related FX questions merge only when their revenue-source identity is unambiguous.
Known engineering records are labelled as project data, not researched options.

FX choices call the existing deterministic converter and disclose its pinned source,
date, original currency and unchanged price-period scenario. External market research
requires per-question consent and uses existing source-validated drafts; no invented
suggestions are presented as research. Explicitly user-stated pending income terms
can be researched without first inventing a calculated payment line. Draft prices
still require scope/unit/currency/period reconciliation and commercial approval.

Browser inspection against the supplied Team8 case verified one combined question,
retrieved the existing ECB reference conversion for GBP100/m3, selected that option
and enabled Apply. No answer was submitted, no paid AI/research was invoked, and
the user's saved commercial inputs remained unchanged. Automatic UI checks cover
ambiguity, zero values, before/after currency notation, deduplication, no repeated
textarea and step navigation. Mocked research tests cover pending-source intent
and unchanged plan; live researched-market suggestions are not verified by these tests.

Automatic suggestions update: currency questions now request the canonical FX
conversion on card opening, not behind an extra Get conversion button. Loading,
errors and retry are explicit; no option is preselected. FX question headings are
shortened and the original wording stays in an expandable evidence section.
Market research has an explicit question-scoped opt-in that starts preparation
immediately and at most once per question in that session. Permission does not
carry into a different question; existing saved candidates remain selectable
without new research. The typed-answer option remains available throughout.

## Upfront preflight and batch calculation — 9 November 2026
The reported second 'question' was actually an optional flat-rate editor after the
rate had already been populated. That editor is now collapsed under Edit saved
rate (optional); resolved values are shown as summaries with readable precision.
A single Confirm & calculate action is the explicit commercial approval action;
there is no separate approval checkbox in the guided modal.

A new read-only revenue-preflight endpoint collects authority, schedule, source,
fraction and canonical per-source calculation problems before review. Complete
projects also receive a cross-source reconciliation check. The review exposes an
index of all known questions, requires all answers together and retains prior
answers when navigating. Supported FX, source and numeric field answers apply as
allowlisted edits to the existing plan and execute the canonical Python pathway,
without sending those answers back through the LLM. Other assumptions stay intact.
Unstructured answers that change commercial meaning still require interpretation
and review; newly supplied facts can expose new issues. This does not promise that
unknown future information can be validated before it is supplied.

New tests verify the complete missing-price/missing-sales-fraction inventory,
ready inputs producing no optional questions, cross-source duplicate detection,
read-only inspection, unchanged inputs and batch field/range validation.
Browser test assessment e91dba68140d42e99463db812c2ef93c used synthetic source data:
two questions were collected up front, price 2 and a disclosed 100% sold fraction
were applied together, and all canonical economic stages completed with use_ai=False.
The saved Revenue dashboard showed USD11,454,720 annual net sales and no extra
question. The real Team8 assessment was inspected read-only; its saved rate was
already populated and the preflight returned ready with no outstanding questions.
