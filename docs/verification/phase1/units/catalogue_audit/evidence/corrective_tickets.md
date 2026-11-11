# Separate corrective tickets — proposed only

## UNIT-EXT01 — Velocity

- **Workflow classification**: REQUIRED FOR ACTIVE WORKFLOW
- **Usage**: filter_area hydraulic_loading_m_h; m3/m2/h is velocity
- **Current support**: m/h fixed native parameter works; generic m/s->ft/s and m/h unsupported
- **Units**: m/s;ft/s;m/h;m3/m2/h
- **Equation**: v_ft_s=v_m_s/0.3048; v_m_h=3600*v_m_s
- **Physical assumptions**: No fluid assumptions for unit scaling; hydraulic loading must use appropriate area
- **Required independent checks**: Exact foot/time factors; signed/zero policy; parameter adapter tests
- **Proposed action**: Separate active-input normalization enhancement; no equation changes

## UNIT-EXT02 — Dynamic viscosity

- **Workflow classification**: OPTIONAL
- **Usage**: No dynamic viscosity input in 12 native methods or 1063 declared cost coordinate/context records
- **Current support**: No generic viscosity family
- **Units**: Pa*s;mPa*s;cP
- **Equation**: mu_Pa_s=0.001*mu_cP
- **Physical assumptions**: Dynamic-to-kinematic needs density; same-family conversion does not
- **Required independent checks**: NIST definition; zero/sign/type/domain and cross-family rejection
- **Proposed action**: Optional future fluid-property support; no current native blocker

## UNIT-EXT03 — Kinematic viscosity

- **Workflow classification**: OPTIONAL
- **Usage**: No kinematic viscosity input in native/model coordinate contracts
- **Current support**: No generic viscosity family
- **Units**: m2/s;mm2/s;cSt
- **Equation**: nu_m2_s=1e-6*nu_cSt
- **Physical assumptions**: nu=mu/rho only with qualified density
- **Required independent checks**: NIST definition; no accidental dynamic/kinematic matching
- **Proposed action**: Optional future fluid-property support

## UNIT-EXT04 — Heat-transfer coefficient

- **Workflow classification**: REQUIRED FOR ACTIVE WORKFLOW
- **Usage**: exchanger_area and vaporizer_area overall_u_w_m2_k
- **Current support**: Fixed W/m2/K native input supported; generic U conversion absent
- **Units**: W/m2/K;Btu_IT/(h*ft2*delta_degF)
- **Equation**: U_SI=U_IP*1055.05585262/(3600*0.3048^2*(5/9))
- **Physical assumptions**: Same surface/film convention; interval temperature, not absolute offset
- **Required independent checks**: Independent coefficient 5.678263341113488; inverses, offsets rejection and native dispatch
- **Proposed action**: Separate active-input normalization ticket

## UNIT-EXT05 — Standalone time/residence time

- **Workflow classification**: REQUIRED FOR ACTIVE WORKFLOW
- **Usage**: capacity cycle h; EBCT min; vessel hold-up h; dryer seconds
- **Current support**: Fixed native time arithmetic supported; generic min->h unsupported
- **Units**: s;min;h;day
- **Equation**: t_h=t_min/60; tau=V/Q only with valid V/Q
- **Physical assumptions**: Unit conversion requires no extra assumptions; deriving residence time does
- **Required independent checks**: Exact60/3600/86400; boundary/type, source-vs-native parameter tests
- **Proposed action**: Separate time catalogue/adapter ticket; do not invent process residence time

## UNIT-EXT06 — Specific gravity derivation

- **Workflow classification**: OPTIONAL
- **Usage**: Explicit density bridge exists; no native method requires SG
- **Current support**: No SG bridge; density unit conversion supported
- **Units**: SG;kg/m3;g/cm3
- **Equation**: rho=SG*rho_ref(Tref,Pref)
- **Physical assumptions**: Reference substance/density,T/P mandatory; no universal1000
- **Required independent checks**: Independent defined reference cases; missing-reference rejection; density provenance
- **Proposed action**: Separate optional physical derivation, not dimension-only alias

## UNIT-002-C01 — Boiler horsepower historical basis

- **Workflow classification**: REQUIRED FOR ACTIVE WORKFLOW
- **Usage**: Garrett advertised boiler_hp chart coordinate
- **Current support**: Identity supported; thermal watt relationship intentionally blocked
- **Units**: boiler_hp;W only after source basis confirmed
- **Equation**: If source confirms NIST convention, thermalW=boilerhp*9809.50
- **Physical assumptions**: Inspect original source footnote/model meaning before selecting conversion
- **Required independent checks**: Source-specific rating proof, independentW check, reject mechanicalhp confusion
- **Proposed action**: Clarify source coordinate before implementing any new conversion

## UNIT-002-C02 — Unresolved model source coordinates

- **Workflow classification**: REQUIRED FOR ACTIVE WORKFLOW
- **Usage**: 4 Garrett +7 OpenPyTEA contracts; see dependency matrix
- **Current support**: 11 required coordinates remain blocked
- **Units**: Source-specific compounds; not generic arbitrary parsing
- **Equation**: Derive each mapping from source: e.g massflow/Pabs; length*diameter^1.5
- **Physical assumptions**: Confirm source quantity/exponent/surface/rating; no speculative substitutions
- **Required independent checks**: Independent source examples plus dimension and converter dispatch tests per model
- **Proposed action**: Separate model-interface tickets; do not modify equations in this audit

## UNIT-002-C03 — Other fixed native compound parameter units

- **Workflow classification**: REQUIRED FOR FUTURE PLANNED WORKFLOW
- **Usage**: All12 fixed contracts accepted; arbitrary alternate source-parameter unit support incomplete
- **Current support**: Native kJ/kg,kg/kmol,mol_equiv/m3,fraction accepted only in allowlisted forms
- **Units**: J/kg;kJ/kg;kg/mol;kg/kmol;equivalent concentration;dimensionless fraction
- **Equation**: h_kJ_kg=h_J_kg/1000; MW_kg_kmol=1000*MW_kg_mol; chemistry basis explicit
- **Physical assumptions**: Chemical equivalents depend species/charge; fraction vs percent explicit
- **Required independent checks**: Independent factor/chemistry cases and invalid unit rejection before extending adapters
- **Proposed action**: No new catalogue support required to use already-normalized native inputs

## UNIT-002-C04 — Semantic reference/context assurance

- **Workflow classification**: REQUIRED FOR FUTURE PLANNED WORKFLOW
- **Usage**: Opaque standard-gas reference descriptors; pressure roles and rating/capacity conventions
- **Current support**: Current explicit-context guards correct; scientific validity of supplied context remains external
- **Units**: Gas reference T/P/Z/wetness/composition; differential vs absolute; shaft vs driver
- **Equation**: Gas normalization physical bridge; power/efficiency only with declared basis
- **Physical assumptions**: User/context state must be scientifically consistent; no string equality as physical proof
- **Required independent checks**: Structured gas-state validation, same/different-state cases and role lineage
- **Proposed action**: Future typed context enhancement, not a failed arithmetic unit conversion
