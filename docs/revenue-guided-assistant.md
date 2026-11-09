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
