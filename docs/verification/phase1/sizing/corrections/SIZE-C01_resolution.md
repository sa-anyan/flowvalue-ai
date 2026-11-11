# SIZE-C01 — Compressor numerical stability correction

Date: 10 November 2026. Parent: FV-P1-SIZE-001. Decision: **PASS for SIZE-C01 only**, supported by the completed regression evidence below. The historical parent verification remains FAIL; G1 is not passed. SIZE-C02 and SIZE-C03 are not implemented.

## Original defect and exact reproduction

The original unchanged assertion is `backend/tests/test_sizing_independent_verification.py::test_required_compression_stability_near_unity_gamma`. Before modifying production, it failed with:

- Mass: 3600 kg/h; mixture molecular weight: 28 kg/kmol.
- Inlet: 300 K and 1 bar absolute; outlet: 2 bar absolute.
- Gamma: `math.nextafter(1.0, 2.0)` = 1.0000000000000002.
- Isentropic efficiency: 0.75; compressibility factor: 1.
- Independent 100-digit reference: **82.33066173777114 kW**.
- Before: **118.77803740218916 kW**, approximately **44.2695% high**.
- After: **82.33066173777112 kW**, absolute difference about 1.42e-14 kW, relative difference about 1.73e-16.

The original test and static expected-value fixture were not edited. `SIZE-C01_evidence/before.txt` records the reproduced failure, and `original_case_after.json` records the corrected output.

## Equation, root cause and equivalent correction

The existing physical model is unchanged:

`W = m_dot * (R/MW) * T * Z / eta * gamma/(gamma-1) * (PR^((gamma-1)/gamma) - 1)`.

Here mass flow is converted to kg/s, R/MW is in kJ/(kg K), temperature is K, pressure ratio uses absolute pressures, and output is kW. The returned formula and applicability metadata are preserved.

Set `a = (gamma-1)/gamma` and `L = ln(Pout/Pin)`. The pressure factor is exactly `expm1(a*L)/a`. Production retains `gamma/(gamma-1)` and replaces the unstable subtraction with `expm1(a*L)`. As gamma approaches 1 from above, `expm1(a*L)/a` tends to `L`; therefore the limiting work is `m_dot*(R/MW)*T*Z*ln(PR)/eta`. Gamma exactly 1 remains outside the existing contract and is rejected.

The old expression first rounded `PR^a` extremely close to 1, then subtracted 1, losing significant digits before multiplication by the large reciprocal of gamma minus 1. The independent Decimal calculation, unchanged ordinary-case matches, and convergence to the analytical limit demonstrate numerical cancellation, not a new physical model or empirical correction.

For close absolute pressures, compute `L = log1p((Pout-Pin)/Pin)`. If that relative rise overflows despite both pressures being finite, compute `L = log(Pout)-log(Pin)`. This avoids an overflowing intermediate pressure ratio. A seven-point independent experiment across adjacent floating-point pressures on both sides of this branch confirms agreement and continuity; its inputs are numerical stress conditions, not physically approved compressor duties.

## Exact implementation scope

Only `backend/engineering_sizing/compression.py` changes production behaviour:

1. Import standard-library `expm1`, `log1p`, `log`, `isfinite`.
2. Check `Pout > Pin` directly instead of depending on a divided ratio.
3. Evaluate the equivalent logarithm and exponential-minus-one expressions stably.
4. Convert pressure-term overflow into an explicit ValueError and validate finite positive compressor power at the direct callable boundary, preserving the existing registry guard.

No new dependency, coefficient, unit, empirical multiplier, gamma approximation branch or equipment-design assumption is introduced. No other sizing method, cost correlation, escalation engine, CAPEX/OPEX/Revenue or financial model is changed. The full production diff is retained in `SIZE-C01_evidence/production_change.patch`.

Added `backend/tests/test_compressor_numerical_stability.py`; updated only the SIZE-C01 row of `sizing_calculation_risk_register.csv`; added this resolution and its evidence. The original parent report and numerical-verification CSV remain historical records.

## Independent verification

The new test oracle uses 100-digit Decimal arithmetic and the ideal enthalpy route: independently evaluate isentropic outlet temperature and `cp*(T2-T1)/eta`. It uses exact binary representations of the supplied floating-point inputs and R from exact Boltzmann × Avogadro constants. No expected result calls the production compressor.

The 48-point grid combines gamma values immediately above 1, 1+1e-12, 1+1e-8, 1.01, 1.3, 1.4, 1.67 and 2 with pressure ratios immediately above 1, 1+1e-12, 1.01, 2, 8 and 20. The high ratios verify the constant-property screening equation, not thermal/material suitability of a real compressor. Additional cases check the analytical gamma limit, deterministic repetition, adjacent large absolute pressures, overflowing intermediate pressure ratios, invalid/nonfinite pressures and gamma, non-compressing conditions, and explicit nonfinite-output rejection.

Relative tolerance **5e-12**, inherited from the parent compressor numerical verification, is used with zero absolute tolerance for the new reference checks: tiny pressure-rise duties cannot pass solely through an absolute error allowance. This comfortably accommodates binary/libm rounding while exposing the original 44% defect. It is not an engineering uncertainty range. The original assertion retains its original tolerance.

Physical-equation sources and limitations remain those independently cross-checked in [the parent references](../independent_equation_references.md), particularly NASA's ideal constant-specific-heat compression relation. This correction does not retroactively establish original implementation provenance. No third-party implementation was copied.

## Regression results

| Verification | Exact outcome |
| --- | --- |
| Original assertion before correction | 1 failed (reproduced) |
| Compressor-focused suite: 75 new cases, 2 existing bridge cases, original assertion | **78 passed**, 0 failed |
| All 12 independent sizing methods | **301 passed, 3 failed**, 0 skipped |
| Targeted sizing/interfaces and R-01 regressions | **66 passed**, 0 failed |
| Adjacent-pressure log-branch continuity experiment | **7 comparisons passed**, both branches exercised |
| Complete canonical backend | **2114 passed, 3 failed, 3 skipped**, 367 subtests passed; 1 warning; 161.10 seconds |

The complete backend exits nonzero solely for the three unchanged SIZE-C02/SIZE-C03 assertions. The original compressor assertion passes unchanged. All prior nominal sizing cases and R-01 behaviour pass. The three skips remain private Charlie workbook, private Charlie snapshot and optional installed OpenPyTEA reference unavailable; they are not counted as successes. The warning is the existing Starlette/httpx test-client deprecation. `SIZE-C01_evidence/full_files.json` records canonical test selection, including Nottingham smoke tests and legitimate prior untracked verification suites; pre-existing duplicate files were not removed or collected.

Evidence commands are reproducible with the recorded isolated Python interpreter using `SIZE-C01_evidence/run_verification.py before|compressor|new|baseline|full`. The `before` mode now passes after correction; its retained historical log records the original failure. File-selection JSON, raw pytest logs and JUnit XML are retained independently from the parent audit evidence. Real AI/cloud calls and external socket connections were disabled; synthetic assessment storage was isolated.

## Remaining limitations and acceptance

The existing supported input checks remain `1 < gamma <= 2`, positive finite mass, MW, absolute pressures, temperature, Z, and `0 < eta <= 1`, with outlet pressure greater than inlet. Finite numerical agreement is not approval for every value in that mathematical domain. Constant-property, single-stage gas screening assumptions remain; condensation, intercooling, real-gas path accuracy, equipment pressure/temperature limits and property applicability still need engineering review. No arbitrary maximum pressure ratio is invented here.

SIZE-C02 still has two failing boolean-duty assertions; SIZE-C03 still has one infinite pump auxiliary-power assertion. No skip, xfail or weakened expectation hides them. FV-P1-UNIT-001 acceptance remains unconfirmed and wider provenance/applicability gaps remain open. No approved project data was modified; no commit, push, merge or deployment was performed. Stop after SIZE-C01.
