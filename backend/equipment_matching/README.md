# Canonical conceptual equipment matcher

`service.match_report` accepts the canonical Engineering data report, project text,
existing provider and response cache. It extracts equipment-only names/tags JSON;
linked stream descriptions are separate context. The catalogue includes names,
configurations and references, without costs, curves or numerical sizing data.

The prompt applies exact-word hints, semantic equivalence, operational knowledge,
process context and conceptual suitability review in one bounded model request per
32 entries. Python checks the response structure, catalogue references and source
IDs; it cannot certify the model's engineering judgement. No second reviewer,
hardcoded family-compatibility matrix or full-design validation is involved.

A conceptual family match may have no selected configuration. Core-equipment
proxies are explicit and component-only suggestions do not count as full matches.
Missing/failed decisions remain visible and do not erase existing costing inputs.
Genuine model changes archive prior coordinate inputs instead of reusing them for
a different curve. Approved manual/quoted prices retain existing protections.

Sizing, unit conversion, factors and arithmetic remain in existing Python modules.
This matcher generates none of them. It neither researches prices nor reads workbook
cost estimates. A match count is not pricing coverage or a unique physical-asset
count; input registers can contain unresolved aliases.

Active equipment execution and older advisor entry points delegate here. The old
`orchestration.equipment_advisor` contains validation/compatibility helpers only;
its former mixed matching/sizing implementation was removed.

Charlie check: 32 canonical entries; one actual configured-provider call, 57.14 s:
25 conceptual matches (including one core proxy), six ambiguous, one absent model
(electrolyser). Three configurations selected; 22 other matches are family-level.
An integrated equipment-stage run reused that same cached response, with identical
matching counts. This is not an independent second AI consistency trial. Baseline
assessment preserved; matching test saved as b4cd73100a2e455c9aff9eb080e8b335.

Tests: focused matching, compatibility, stage integration and engineering-review
suite: 43 passed. Frontend production build passed. Local browser confirmed a
selected spray-dryer model and the matching explanation. New live projects still
need engineering review; a prompt and schema do not guarantee correct matches.
