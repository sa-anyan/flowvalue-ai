# Development-only checks

`development_first_new.txt/xml` preserve the first test-authoring iteration:
1,025 passed and one new test failed because it referenced the nonexistent
CostEstimate.equipment_cost field. The assertion was corrected to the actual
CostEstimate.amount field; no production price calculation changed.

An intermediate affected-suite check also identified the existing expected
“unit mismatch” validation wording. The normalizer now preserves that wording
and includes the detailed issue. All current targeted, legacy, handoff and
alias batches pass. Their selected tests and XML files, rather than this first
prototype check, establish final acceptance. No prior-task evidence was changed.
