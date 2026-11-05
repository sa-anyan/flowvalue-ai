# One active assessment pipeline

All workbook types and source ages now use backend.blocks.engineering_workflow → blocks.execution.run_stage → the same registered Engineering data and Equipment runners. The current pipeline identifier is flowvalue-shared-stage-pipeline-v1. Neither worksheet names nor old project IDs select an alternative pricing coordinator.

Entry /engineering/run, the older /run URL, and the public orchestration.service.execute() entry point dispatch to this same coordinator. Engineering data feeds Equipment; CAPEX, OPEX, Revenue and Financial modelling still require their separate selected stage runs. Changing the source creates a new assessment rather than replacing an existing uploaded workbook.

Saved legacy studies are preserved as named versions before an explicit run migrates them. Live current_price_view no longer invokes the retired connected coordinator or cached whole-TEA price-view calculation. Legacy snapshots are explicitly labelled historical and do not appear as freshly executed stage outputs. Explicit historical snapshot access remains available.

Each executed stage records pipeline_id, producer, executed, input_hash/output_hash and completion time. A data-required prerequisite receipt has executed=false. These are run receipts, not certification of engineering correctness. AI-response caching reuses inputs/assumptions, not old result prices; Python still performs numerical calculations when a stage is run. Ordinary page views do not run a calculator.

The former connected coordinator and price-view implementation are private, explicitly named historical regression references. Existing historical numerical tests call those names deliberately. No API, UI, current view or public execute() call dispatches to them. The pure deterministic numerical pipeline remains the shared numerical/reference machinery for scenario/Monte Carlo work, with the same canonical equipment-cost adapter; it is not an alternate workbook/AI orchestration route.

Real-workbook checks: uploaded Team 8 XLSM and Charlie XLSX bytes were newly parsed and calculated through the common public entry using their prior saved assumptions, with no saved result prices supplied and no paid AI calls. Team 8 produced 6/7 priced items; Charlie produced 8/32. Source gaps and unpriced entries remain explicit. This demonstrates uniform execution and deterministic reuse of assumptions, not a new live LLM estimation or industrial validation.

## Initial Entry run: automatic conversion assumptions

The initial `EngineeringRun` API request defaults to `use_ai=true`; an explicit
`false` remains supported. The Entry interface selects AI according to server
availability and sends that checkbox value explicitly. With AI enabled, the same
initial action executes extraction/review, conceptual matching, provisional model
configuration and conversion assumptions, Python derivation/conversion, and
canonical equipment costing. It does not require opening the conversion drawer or
pressing a second run button. Saved user inputs/locks retain their existing rules;
AI estimates remain labelled and editable. Other economic stages remain separate.
A controlled-provider regression exercises this initial path through an actual
Python price without another stage action. This verifies routing, not LLM accuracy.
