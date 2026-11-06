# OpenPyTEA catalogue import and integration report

Source pin: [`9d769ad1583794401e4c441272ba7cccc46aff75`](https://github.com/pbtamarona/OpenPyTEA/tree/9d769ad1583794401e4c441272ba7cccc46aff75). MIT notice retained; original data hashes in `sources.json`.

## Coverage

| Measure | Count |
|---|---:|
| imported | 421 |
| categories | 35 |
| mathematically valid representative | 421 |
| rejected rows | 0 |
| disabled | 18 |
| available provisional | 403 |
| complete metadata | 344 |
| automatically sizeable without project data | 0 |
| dimensionally supported measurement or assumption | 414 |
| manual composite coordinate required | 7 |
| two variable | 7 |
| missing first coordinate bounds | 55 |

Counts overlap. Complete metadata means consistent imported fields, bounds, units and declared cost scope, not independent validation of every textbook/paper. No model can be promised automatically sizeable without project inputs. The 414 dimensionally supported models can use matching measurements or registered conversions/sizing with explicit assumptions; seven composite coordinates require explicit native design values. Project-specific assumption counts cannot be determined from a catalogue alone.

The documentation advertises 417 correlations/34 categories. The pinned CSV contains 421/35; all rows are preserved. No rows were invented or discarded to match a documentation count.

## Equation families

| Form | Rows |
|---|---:|
| offset power-law | 203 |
| ln-ln quadratic | 65 |
| power-sizing | 49 |
| log-log quadratic | 94 |
| 2-var power-law | 7 |
| exponential | 3 |

All 421 original equations pass representative numerical parity against the exact pinned upstream `CostCorrelationDB` implementation, retained solely in tests under MIT. Positive published primary boundaries are compared too; physically nonpositive source outputs are rejected rather than propagated. Optional cubic/quartic terms are tested. Both coordinates, ranges and units are preserved for all seven two-variable correlations.

## Disabled rows

Rows remain visible in the API/audit; automatic model selection excludes them.

| Upstream key | Reason |
|---|---|
| `burner_parkinson_2016` | Cost scope not explicit in upstream Remarks; cannot assume purchased equipment |
| `electric_arc_furnace_parkinson_2016` | Cost scope not explicit in upstream Remarks; cannot assume purchased equipment |
| `pyrolysis_furnace_ulrich_2003` | Cost scope not explicit in upstream Remarks; cannot assume purchased equipment |
| `mea_ccs_technology_2011` | Cost scope not explicit in upstream Remarks; cannot assume purchased equipment |
| `air_blower_manzolini_2006` | Cost scope not explicit in upstream Remarks; cannot assume purchased equipment |
| `co2_compressor_manzolini_2011` | Cost scope not explicit in upstream Remarks; cannot assume purchased equipment |
| `h2_compressor_pandolfo_1987` | Cost scope not explicit in upstream Remarks; cannot assume purchased equipment |
| `gas_multi_cyclone_ulrich_2003` | Cost scope not explicit in upstream Remarks; cannot assume purchased equipment |
| `hx_nexant_2006` | Cost scope not explicit in upstream Remarks; cannot assume purchased equipment |
| `plate_fin_3streams_hx_esdu_1997` | Cost scope not explicit in upstream Remarks; cannot assume purchased equipment; Source notes original GBP; dataset USD conversion basis unverified |
| `plate_fin_4to6_streams_hx_esdu_1997` | Cost scope not explicit in upstream Remarks; cannot assume purchased equipment; Source notes original GBP; dataset USD conversion basis unverified |
| `explosion_proof_motor_ulrich_2003` | Cost scope not explicit in upstream Remarks; cannot assume purchased equipment |
| `totally_enclosed_motor_ulrich_2003` | Cost scope not explicit in upstream Remarks; cannot assume purchased equipment |
| `horizontal_drum_150_psig_perry_1996` | Cost scope not explicit in upstream Remarks; cannot assume purchased equipment |
| `indirect_fluidbed_ulrich_2003` | Cost scope not explicit in upstream Remarks; cannot assume purchased equipment |
| `axial_gas_turbine_ulrich_2003` | Cost scope not explicit in upstream Remarks; cannot assume purchased equipment |
| `radial_expander_ulrich_2003` | Cost scope not explicit in upstream Remarks; cannot assume purchased equipment |
| `steam_turbine_kreutz_2002` | Cost scope not explicit in upstream Remarks; cannot assume purchased equipment |

## Integrated execution

- Existing registry exposes `source="openpytea"` and namespaced IDs `openpytea:<encoded upstream key>`; original key is retained separately. Garrett/custom IDs and equations remain intact.
- Exact, semantic, engineering and contextual matching search all executable libraries without a source/year preference. Full metadata stays canonical; compact transport reduces repeated AI input tokens. No live AI call was used for validation.
- Shared converters handle mass/volume flow, US/Imperial gallons, head, area, volume, power and explicit pressure bases. No ambiguous gallon/ton or gas reference is silently chosen. New pump Q×sqrt(H) sizing uses supplied head or explicit differential pressure and density. Motor efficiency bridges distinguish shaft/electrical power; hydraulic power uses the existing pump method.
- Second-coordinate selection is independent: source ID or explicit value/unit/rationale, with Python conversion and traceability. Saved assumptions remain editable; source cells stay unchanged. Unsupported composite derivations return MISSING_SIZING_INPUT.
- Published bounds are hard constraints: no automatic extrapolation, capacity clamping or parallel splitting. Missing bounds require explicit provisional acceptance. Supplied gauge pressure is checked against explicitly extractable source psig limits. Unprovided/unclear operating conditions remain review limitations.
- Native costs retain USD/source year and do not invoke upstream escalation. Existing same-series indices or an explicitly allowed, labelled CPI proxy handle translation. Official BLS annual source observations were added for the imported years. Upstream CEPCI data is preserved reference-only; no new 2026 CEPCI is asserted and no implicit FX occurs.
- Base material is already included. Optional material ratios and generic installation profiles require explicit applicability confirmation. Unsupported base/target factors and adjustments on installed/module scopes are rejected.
- Purchased, installed, module and per-foot/per-tray costs remain separate. Scoped installed/module totals enter CAPEX once in the existing separate capital bucket; they are not treated as purchased-equipment factor bases. No financial-ledger refactor.
- The existing drawer exposes source/version, original equation/coefficients, input/conversion/derivation trace, bounds, historical and escalated cost, quantity and warnings. Two-coordinate controls and physical quantity units are in the existing workspace, not a new page.
- Monte Carlo uses the same costing/CAPEX/financial pipeline and records cost scopes. New approved-revenue fixture completes 1,000 fixed runs reproducibly without an LLM or baseline mutation.

## Verification and remaining limits

**Recorded acceptance run: 1,081 tests passed in 79.91s**, covering the new bulk catalogue tests and established costing, conversion, matching, CAPEX, financial and stage regressions. The separately diagnosed older Monte Carlo fixture failure is described below.

- Bulk parity/adapter, bounds, invalid inputs, quantities, materials, source scope, pressure, unit conversions and approved Monte Carlo tests are in `backend/tests/test_openpytea_catalogue.py`.
- Production frontend build and TypeScript checks passed. Automated browser interaction/visual review of the new controls was not completed.
- The older `test_monte_carlo.py::test_canonical_financials_and_reproducible_simulation` fixture lacks approved Revenue Box data and produces zero complete runs. Repeating it against the original HEAD Monte Carlo implementation confirms the same issue. Revenue authority was not weakened to make this test pass.
- Mathematical parity is not literature/industrial validation. Source notes, missing applicability bounds, default-material assumptions, generic installation applicability, sterility/pressure/temperature suitability and auxiliary overlaps still require engineering review.
- Seven specialist composite coordinates remain manual design inputs. No mass balance, price, buyer contract or design value is invented.

## Repeatable maintenance

```sh
python -m backend.equipment_costing.indexes.openpytea.audit
python -m backend.equipment_costing.indexes.openpytea.import_catalogue /path/to/pinned/source/files
python -m pytest backend/tests/test_openpytea_catalogue.py -q
```

Importer checks every pinned hash before writing only the OpenPyTEA snapshot. Repeating the same import changes no source files or timestamp; audit output is deterministic. Source version changes require deliberate source review and a new manifest. Never silently update from upstream main.

## Main files

- `backend/equipment_costing/indexes/openpytea/`: pinned CSV, metadata, six evaluators, adapter, factors, notices, audit and importer.
- `backend/tests/openpytea_reference/`: exact test-only upstream evaluator class.
- Canonical registry, unit/sizing bridges, matching, equipment totals/status, CAPEX connector and Monte Carlo scope coverage.
- Existing equipment drawer/assumption controls and catalogue endpoint.
- `THIRD_PARTY_NOTICES.md`: pinned-source attribution.

Local HTTP smoke checks passed: backend health, frontend catalogue proxy and equipment page returned 200. The proxy advertises 421 OpenPyTEA rows (403 available provisionally, 18 disabled). Local app restarted at http://localhost:3001 with AI response caching disabled. No existing assessment was repriced or baseline changed.
