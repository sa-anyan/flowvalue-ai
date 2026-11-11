# Independent reference calculations — FV-P1-UNIT-001

11 November 2026. This is bounded verification, not a new conversion engine. Expected values are defined independently in `backend/tests/fixtures/unit_acceptance/references.json` and `aliases.json`; no production conversion factors are imported to create them. A standard-library Decimal generator is retained at `evidence/build_reference_fixtures.py`.

## Basis and substitutions

Use exact international inch=.0254 m, foot=.3048 m, pound=.45359237 kg, standard gravity=9.80665 m/s², US gallon=.003785411784 m³, Imperial gallon=.00454609 m³, litre=.001 m³, minute=60s, hour=3600s and day=86400s. These are unit definitions, not selected plant operating assumptions. All 146 named conversion substitutions and expected outputs are recorded row-by-row in the acceptance CSV/JSON.

Examples:

- **Mass/time:**1 kg/s ×3600 s/h =3600 kg/h.1 lb/h ×.45359237 kg/lb =.45359237 kg/h.1 tonne/h =1000 kg/h. A mass flow does not become a volume flow without a qualified density.
- **Volumetric flow:**1 L/s ×.001 m³/L ×3600 s/h =**3.6 m³/h**.1 US gpm ×.003785411784 m³/gal ×60 min/h =.22712470704 m³/h. Imperial gpm uses.00454609 and yields.2727654 m³/h. Generic gal/gpm remains ambiguous without the selected basis.
- **Pressure:**1 psi =.45359237×9.80665/.0254² Pa.1 bar=100000 Pa.0 barg with an explicitly supplied101325 Pa atmosphere becomes1.01325 bara. This is not a universal local atmosphere or permission to infer an operating/design/differential role.
- **Temperature:**25°C+273.15=298.15 K.18°F difference ×5/9=10 K difference; offsets do not apply to temperature intervals.32°F becomes273.15 K using the absolute relation. Absolute/difference cross-kind conversions remain rejected.
- **Energy and power:**1 kWh=3.6 MJ.24 kWh/day divided by86400 seconds is1 kW; without a time basis, kWh cannot become kW. Mechanical hp uses550 ft·lbf/s; refrigeration ton uses12000 Btu_IT/h, not a mass ton. IT versus thermochemical Btu must be explicit.
- **Geometry/density:**1 ft²=.3048² m²;1 ft³=.3048³ m³.1 lb/ft³=.45359237/.3048³ kg/m³. Equipment capacity and throughput remain distinct despite related names.
- **Contextual liquid derivation D01:**2 kg/s becomes7200 kg/h; divided by explicitly supplied1000 kg/m³ gives7.2 m³/h. Missing density is rejected. Density1000 is a synthetic assumption, not an inferred universal liquid density.
- **Contextual gas derivation D02:**100 actual m³/h at1 bar absolute,300 K and Z1 becomes50 reference m³/h at2 bar absolute,300 K and Z1 for unchanged composition. This arbitrary explicit reference is not a definition of universal standard/normal conditions. Use `Qref=Qactual*(Pactual/Pref)*(Tref/Tactual)*(Zref/Zactual)`. The pure converter does not perform this thermodynamic derivation.

## Native sizing paths

For each of 12 methods, two independently specified source-unit conversions feed the existing registry: mass-flow methods use kg/s or tonne/h; volumetric-flow methods use L/s or L/min; thermal-area methods use W or MW. Expected size follows the static parent reference multiplied by the independently known throughput/duty ratio, with the parent parameters held fixed. These24 numeric source-to-native cases pass. They do not approve arbitrary parameter units, file parsing, model matching or unsafe numerical types.

Native parameters retain the explicit unit contracts in `sizing_native_unit_contract_acceptance.csv`. The five unsupported families remain unsupported even when an equation could be written down: a given U or residence time in native units is not evidence of a general U/time converter.

## Tolerances

Unit definition checks use relative tolerance1e-12 and absolute floor1e-14, covering binary float multiplication/division/offset roundoff against independent decimal definitions. The near-zero absolute/gauge reversal is a particular cancellation case explicitly covered by the absolute floor. These unit checks do not assign an engineering uncertainty or universal machine-design tolerance. Parent method-specific numerical tolerances are retained for the 24 sizing results; they are not changed to obtain acceptance.

The spelling checks assert independently specified synonymous/equivalent unit meanings, not the production alias dictionary's answer.76 explicit raw spellings/equivalences pass:75 noncanonical spellings plus the equivalent canonical power unit kJ/s. Key-normalised aliases may appear more than once in the inventory; row totals are not a count of unique accepted spellings.

## Independent authorities and provenance limits

[NIST SP811 B.9](https://www.nist.gov/pml/special-publication-811/nist-guide-si-appendix-b-conversion-factors/nist-guide-si-appendix-b9) and [B.8](https://www.nist.gov/pml/special-publication-811/nist-guide-si-appendix-b-conversion-factors/nist-guide-si-appendix-b8) establish quantity/factor distinctions. The existing independently checked source ledger in `../closure/evidence/sources_and_scope.md` records their provenance and relevant engineering identities. Unsupported velocity/viscosity/U/time relationships are documented there and in the unsupported register; a published factor is not proof of implementation. No new third-party code or dependency was incorporated.

Dated FX snapshot arithmetic and historical-index/proxy arithmetic are retained as **PARTIAL source/basis acceptance**. The targeted tests confirm algorithmic arithmetic; they do not authenticate external observations or establish a real published equipment index. No live market rate was invented or substituted.

## Reproducibility and known failures

Run the recorded isolated verification interpreter with `evidence/run_verification.py targeted`. It selects the new unit checks and relevant existing converter/bridge/native/currency/escalation regressions, without the complete backend suite. Expected fixtures do not call production to calculate their own expected results. Test logs/XML and file lists are retained. Real AI/cloud calls and external sockets were disabled, and test assessment storage was isolated.

The13 new failing tests expose UNIT-C01: NumPy Boolean assumptions/observations can be converted into valid-looking sizing inputs upstream of the shared converter. The pure converter rejects them. No failing assertion was weakened, skipped or xfailed. The original304 native arithmetic checks remain passing; passing arithmetic does not negate this new type-safety evidence.
