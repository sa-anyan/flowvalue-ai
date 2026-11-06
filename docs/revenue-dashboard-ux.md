# Revenue exploration UX — 6 November 2026

The Overview stays on the page. A prominent Revenue workspace button beside it
opens a native modal drawer containing Revenue lines, Revenue Box and Ledger.
Extracted revenue starts collapsed; expanding it reveals the existing cards and
source inspector. Interpretation, approval and Python calculation still use the
existing assessment endpoints.

## Research-informed design choices

- Visible, named comparison controls beside the charts reduce reliance on
  remembering options or values between views. This follows the recognition
  rather than recall guidance in [Budiu, 2024](https://www.nngroup.com/articles/recognition-and-recall/).
- Distinct categorical colours identify individual streams across chart controls,
  plotted results and extracted cards. Names, numeric readouts and line patterns
  accompany colour. [Bird et al., 2014, Categorical encoding of color in the brain](https://www.aidanhorner.org/papers/Birdetal_PNAS_2014.pdf)
  provides relevant perceptual research; applying it to this dashboard is a
  design interpretation, not a tested neurological intervention.
- A quiet background and one prominent workspace action establish hierarchy.
  Explicit presets, reversible filters, native disclosure and reduced-motion
  support make exploration user-controlled. No claim of validated addiction,
  dopamine effects or measured analyst productivity is made.

## Calculation and display boundaries

The chart adapter reads saved product net sales, commercial payments and annual
totals from the Python result. It never calculates a price, quantity, contract
payment or forecast from draft assumptions. Selected subtotal is only a display
sum of selected saved stream results. Missing records remain missing; a numeric
zero remains zero. Pending income and avoided OPEX costs are excluded.

Comparisons support individual streams, total, selected subtotal and presets for
total only, streams only, compare all and clear. Filtering changes no assessment
inputs or approval. The year selector and chart points control the inspection
year. Exact values remain available in a compact expandable table and in Ledger.

## Verification

- TypeScript check passed.
- `node --test tests/revenue-series.test.cjs` from `frontend`: four checks cover
  sorted years, saved totals, missing-versus-zero data, pending/cost exclusions,
  subtotals, data immutability, distinct product/contract identities and colours.
- Browser checks on a saved six-method, one-year assessment verified drawer
  opening, Revenue Box and Ledger switching, two-stream plus subtotal comparison,
  streams-only preset and extracted-revenue expansion/collapse. No assessment
  save, AI interpretation, approval or calculation was submitted during these
  checks. Multi-year mapping is covered by the data tests.

## Inline editing refinement

The Overview now has three primary metrics, shorter status text and a collapsible
stream-filter menu. Commercial cards open their method-specific editor inside the
original card; product sales have an inline price/fraction editor. Each editor
saves through the existing revision-checked assessment patch and manual-revenue
validation. Cancel discards the card-local changes. Open card edits block the
footer calculation action until saved or cancelled. New additions still use the
Add Revenue form.

Browser validation on a disposable assessment copy saved a licence fee from
30,000 to 31,000 and a product price from 20 to 21. Cancelling a subsequent price
change to 22 preserved 21. Persisted data and invalidated approval were checked;
the original assessment retained its price of 20, fee of 30,000 and approval.
The browser was returned to the original assessment. TypeScript and the four
chart-data checks passed.
