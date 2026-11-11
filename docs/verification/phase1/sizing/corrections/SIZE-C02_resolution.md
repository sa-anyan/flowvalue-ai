# SIZE-C02 — Boolean heat-duty input validation

Date: 10 November 2026. Parent: FV-P1-SIZE-001. Decision: **PASS for SIZE-C02 only**, supported by the completed evidence below. The original parent verification report remains historical; neither FV-P1-SIZE-001 nor G1 is declared passed. SIZE-C03 is not implemented.

## Reproduction and root cause

Before production changes, both unchanged `test_required_boolean_heat_duty_rejection` assertions failed: `exchanger_area` and `vaporizer_area` accepted True and returned 0.1 m² for U=500 W/(m² K), LMTD=20 K and F=1. The retained `SIZE-C02_evidence/before.txt` and JUnit XML show two failures.

Both registry IDs call `engineering_sizing.heat_exchangers.calculate`. Previously it applied `abs(duty)` before calling `common.positive`. Python bool is a subclass of int; `abs(True)` becomes integer 1, erasing its boolean type before the shared numerical guard can reject it. False became zero and was rejected as nonpositive, rather than identified as an invalid boolean engineering quantity.

The source adapter already rejected Python booleans in observations, but not NumPy boolean scalars. Its `float(normalized_value)` coercion could erase the latter's type before the area function saw it. Checking only the final area function would leave that supported adapter bypass open.

## Exact correction

Only two production files changed in this ticket:

- `backend/engineering_sizing/heat_exchangers.py`: added `validate_heat_duty_type`, explicitly rejecting Python bool and boolean dtype values (including NumPy bool_) with `ValueError("heat duty kW cannot be boolean")`. Call it before taking the magnitude. TypeError from applying abs to missing/nonnumeric inputs now becomes an informative ValueError. The existing finite/positive magnitude check and heat-transfer equation remain unchanged.
- `backend/engineering_sizing/adapter.py`: call that same guard for heat-duty observations before float coercion. Other observation quantities and the global `common.positive` validator are unchanged.

NumPy is optional in the application, so production inspects its boolean dtype marker without importing it. The canonical sizing engine remains stdlib-only; no dependency or third-party source code was added. The local guard is shared by both area methods and their source-observation pathway. No compressor, pump, cost correlation, coefficient, CAPEX, OPEX, Revenue Box, financial calculation or approved project was changed. `SIZE-C02_evidence/production_change.patch` records the exact diff, and `scope_integrity.json` verifies that compressor code, historical reports and the original independent assertions are unchanged from this ticket's start.

## Preserved engineering behaviour

The equation remains `A = abs(Q_kW)*1000/(U*LMTD*F)` with positive finite U and LMTD and 0<F<=1. Negative numerical duty remains valid, because heating/cooling sign does not make physical surface area negative. Zero duty remains rejected: the existing methods and registry require positive equipment size; this ticket does not introduce a zero-area equipment model or a universal prohibition on signed engineering quantities.

For +100 and -100 kW, U=500 W/(m² K), LMTD=20 K and F=1, the independently calculated area is 100000/(500*20)=**10 m²**. Regression tests check this through the direct callable, registry and source adapter for integer/float, Decimal, Fraction and NumPy integer/float scalar inputs. Relative tolerance 1e-12 and absolute tolerance 1e-14 retain the parent area-reference tolerances; neither expected values nor existing assertions were changed.

Missing, nonnumeric, NaN and ±infinity inputs remain rejected. Unsupported canonical duty units (kg/h, m³ and unnormalised W) remain rejected by the adapter. The native numerical area function does not accept unit-bearing values; ordinary W→kW normalisation remains the responsibility of the existing converter. The full backend exercises its existing tests.

The source adapter retains its established fallback behaviour: an invalid/unavailable duty may lead it to seek independently supplied enthalpy or other supported evidence. The boolean itself is never converted into a physical observation. This ticket does not redesign source-selection or alternate thermal-basis policy.

## Executed verification

| Suite | Exact result |
| --- | --- |
| Original unchanged assertions before correction | 2 failed, reproduced |
| Heat-duty suite: 68 new cases, original assertions and existing exchanger tests | **90 passed**, 0 failed |
| All 12 independent sizing methods | **303 passed, 1 failed**, 0 skipped |
| SIZE-C01 compressor verification and bridge tests | **78 passed**, 0 failed |
| Targeted sizing/interfaces/unit bridges and R-01 regressions | **66 passed**, 0 failed |
| Complete canonical backend | **2184 passed, 1 failed, 3 skipped**, 367 subtests passed; 1 warning; 164.03 seconds |

Compared with the SIZE-C01 baseline (2114 passed, 3 failed, 3 skipped), both original boolean-duty assertions now pass and all 68 added cases pass. The only remaining failure is `test_required_finite_pump_auxiliary_outputs` (SIZE-C03). The complete run appropriately exits nonzero rather than hiding that failure. Skips remain the unavailable private Charlie workbook, private Charlie snapshot and optional installed OpenPyTEA reference. The warning is the existing Starlette/httpx test-client deprecation. None is counted as successful verification.

The original two assertions pass unchanged. New `backend/tests/test_heat_duty_validation.py` covers both Python booleans, both NumPy boolean scalars, direct/shared/registry/adapter/source-observation entry points, valid signed representations, zero/missing/nonnumeric/nonfinite inputs and invalid canonical dimensions. Existing independent low/nominal/high references remain unchanged.

Exact file lists, raw logs and JUnit XML are retained in `SIZE-C02_evidence`. `run_verification.py before|heat|new|compressor|baseline|full` records the commands and canonical file selection using the previously recorded isolated verification interpreter. The retained `before` log is historical; rerunning that command after the fix passes. Real AI/cloud calls and external sockets were disabled and synthetic test assessment storage was isolated. The pre-existing duplicate files were neither deleted nor collected as canonical tests. A preliminary full run was deliberately interrupted to remove an unnecessary NumPy import before final verification; its separate log is retained and is not an acceptance result. All reported suites were rerun on the dependency-free final implementation. A Python `-S` probe also confirmed that the sizing engine imports and calculates signed area without site-packages.

## Remaining limitations and acceptance

This is input validation, not a new thermodynamic or exchanger-design model. Phase behaviour, U/F applicability, material/mechanical design, original equation provenance and the unconfirmed FV-P1-UNIT-001 acceptance remain outside this ticket. Existing numeric-string handling in the adapter and numeric-only native callable are preserved; this does not claim arbitrary coercible objects are supported engineering inputs.

The known SIZE-C03 pump auxiliary-power assertion remains failing and visible. No existing failure was skipped, xfailed or weakened. The historical SIZE-C01 resolution and parent verification report are preserved. No commit, push, merge or deployment was performed. Stop after SIZE-C02.
