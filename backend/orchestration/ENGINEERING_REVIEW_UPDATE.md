# Engineering-led workbook workflow — 31 October 2026

This update replaces the narrow first orchestration review path. It does not
replace the legacy deterministic parser or the canonical equipment/cost equations.

## What changed

1. Python still detects stream blocks, components and equipment using the restored
   `workbook_pipeline` and engineering register. The checkpoint parser core remains intact.
2. A dedicated OpenAI workbook engineer reads the cell inventory and original Python
   extraction before costing. It can add missed material/energy streams, equipment,
   components, property/unit observations and source-backed semantic connections.
   Its recovery is no longer confined to Python-recognised table bounds, adjacent
   headers, particular tag patterns or a same-row/column test.
3. Python reads every proposed value from the cited cell and normalises supported
   units. The model supplies interpretation and references, not replacement numbers.
   Corrections retain superseded evidence; the original Python report is immutable.
   Bad references reject that observation, rather than all other extracted data.
4. Equipment and CAPEX have a dedicated typed model-selection contract. The LLM can
   choose service-compatible proxies by meaning, regardless of exact catalogue names.
   Equipment installation/module factors and plant CAPEX factors have separate schemas.
5. Sizing may use explicit provisional inputs. Python supports residence-time sizing
   (`V=Q*t/working_fraction`) and direct stream-property adapters. Derived capacity
   supersedes any LLM mental arithmetic and is not clamped to a curve boundary.
6. Python calculation errors feed back to the engineering LLM for **one** bounded
   corrective pass. This can fix units, factor scope and explicit extrapolation choices.
   Unsupported designs or quantities remain visible instead of receiving invented costs.
7. Downstream advisors run by stage with prior Python results: equipment/CAPEX,
   revenue/OPEX, and finance when the necessary upstream values exist. Missing sales
   for a wastewater service are not replaced with invented product revenue.
8. AI boundary and equipment interpretations are preserved instead of reset to unknown.
   Revenue has an explicit conditional `engineering_scenario` mode for disclosed AI
   saleability/quality assumptions. Existing reviewed-mode defaults and physical-flow
   provenance checks remain. AI never becomes a user approval or independent validation.
9. Entry shows the engineering equipment register separately from costing status.
   Engineering Data exposes source streams, components, original/normalised units,
   properties and cells. The connected local AI option is enabled by default and
   remains visible/optional. User edits remain locked; Python-only reruns make no AI calls.

## Validation

- **234 backend tests pass**, including eight new engineering-review/feedback tests.
- New tests cover records outside Python tables, split headers/units, component flows,
  inferred connections, missing/bad sources, corrections, immutable originals, Python
  sizing, interpreted fields, conditional revenue mode and review-before-selection.
- Frontend production build and TypeScript checks pass.
- Actual connected `gpt-6-luna` calls on `Mass Balance Team 8.xlsm` reviewed 1,416
  supplied cells across the workbook, classified all seven equipment items by duty,
  selected seven equipment decisions and corrected Python-reported model errors.
- Six equipment items obtained **provisional** historical Garrett costs after correction;
  the settler remained unpriced for missing sizing. These are not supplier quotations,
  validated material selections, or verified biological design/scale-up calculations.
- The model added no new numeric observations in this particular live review; Python
  had already extracted them. New-record/missed-property recovery is exercised by
  independent irregular-layout tests, not claimed from nonexistent live recoveries.
- Private artifacts: `outputs/engineering-review/python-extraction.json`,
  `llm-review.json`, `llm-advisor.json`, `llm-correction.json`, `all-tests.txt`,
  `frontend-build.txt`. These keep real responses, assumptions, source lineage,
  decisions and Python results for comparison. No secret is included.

## Limits

Workbook decoding and model contexts remain bounded; macros/formulas/external links
are never executed. The current source inventory is capped at 12,000 non-empty cells
with explicit truncation disclosure, and oversized model contexts require a smaller
workbook. This is not a universal workbook compatibility or full-coverage claim.
The AI can still misinterpret a layout or propose an unsuitable proxy/assumption.
Conflicts, cost-factor applicability, material compatibility, extrapolation and
biological design need engineering review. Conditional scenarios remain distinct
from approved baselines. Market research, mechanical certification and operational
company integration are not introduced by this update.

The local OpenAI connection is enabled, tested and uses the configured model. Review
and initial advisor calls are cached; one feedback correction is allowed when necessary.
No autonomous retry loop, arbitrary generated formula or external research is used.
