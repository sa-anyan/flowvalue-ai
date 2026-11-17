# AI analyst citations — 17 November 2026

The background analyst now returns its own citation objects and claim-specific
source IDs in the same structured Responses API call. The provider enables at
most two hosted web-search tool calls for that analysis. It retains actual
web-search source URLs and URL-citation annotations separately from model text.
The old frontend Garrett hash-to-publisher lookup and its review document have
been removed. No author, title or hash now causes the UI to manufacture a URL.

The backend joins the AI's citation URLs to tool-returned URLs. An unmatched,
unsafe or credential-bearing URL has no published hyperlink. Claim source IDs
are validated against accepted citation IDs; the UI displays numbered links,
retrieval dates, claimed locations and limitations. Bibliographic identity alone
cannot retain the `source_supported` basis. Project data and engineering
hypotheses remain distinct. Existing records without citations are not backfilled
or presented as researched; a fresh opted-in analysis is needed.

A retrieved URL does **not** prove factual entailment, that a paywalled table was
read, that a locator is correct, or that a chosen factor is appropriate. Source
support levels and locators are model declarations and must be reviewed against
accessible full text. No confidence score or independent engineering approval is
implied. The live synthetic CAPEX test retrieved a publisher book record and
explicitly reported that Table 3-4 was not visible; all factor selections remained
hypotheses without source links. This is a valid evidence-gap result, not a
successful verification of those factors.

Public queries are instructed to contain generic engineering/bibliographic terms
only. Workbook/project-specific text must not be sent as search queries; web
content is untrusted. This is method/source research, not permission to research
revenue prices, contracts, buyers or tax law. Existing AI enablement/background
opt-out and scenario/baseline safeguards remain in effect.

Operationally this adds bounded tool latency and search cost to background
analysis. It makes no request on hover/click and reuses cached analysis. The three
live synthetic calls completed in approximately 17–20 seconds. No existing
project inputs, approved economics or calculations were changed by these tests.

Validation artifacts (ignored local outputs):
`outputs/ai-citations-validation/live-capex.json` is the actual model-generated,
validated response; `synthetic-assessment.json` identifies a separate unapproved
UI test record. It contains no calculated project economics.

Tests cover tool-output provenance vs model-injected metadata, rejection of
unretrieved/unsafe URLs, citation-to-claim mapping, bibliographic limitations,
cached retrieval dates, no additional cached provider call, unchanged input
state, existing background stage application guards and frontend rendering.
