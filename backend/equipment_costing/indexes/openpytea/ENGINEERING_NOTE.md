# OpenPyTEA integration basis — 6 November 2026

Pin: 9d769ad1583794401e4c441272ba7cccc46aff75 (MIT; licence inspected).
Import complete source CSV, preserving every original key and row, not textbook
pages or a second TEA runtime. Actual pin: 421 rows / 35 categories (docs 417/34).

Six equations follow CostCorrelationDB.evaluate at that pin. No automatic
parallelisation or upstream escalation. Native cost in USD and source cost_year
are the documented dataset convention; original notes/references and ambiguities
are preserved. Source-specific purchased, installed, module and physical-unit
scopes must be distinct. Missing scope/currency ambiguity cannot become purchase
by default. Missing published bounds require explicit provisional acceptance.

Canonical registry, converter, sizing bridges, total-cost calculator, CAPEX and
financial/Monte Carlo paths are reused. Two coordinates remain independently typed.
Composite coordinates require explicitly documented native values until a validated
physical derivation exists. No arbitrary flow/volume/power substitution. Material
and optional generic installation profiles need explicit applicability confirmation;
no implicit material or installation uplift on already installed/module costs.

Parity uses the pinned upstream CostCorrelationDB source, executed only in tests;
no upstream financial engine dependency. Compare at valid positive source-domain
inputs with no parallelisation. Mathematical parity is not engineering validity or
independent verification of each underlying textbook/paper. Report incomplete data,
unsupported dimensional interpretation and rejected physical costs separately.
