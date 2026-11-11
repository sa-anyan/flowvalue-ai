# Applicability and boundary review

All 12 functions are preliminary screening calculations. Nominal arithmetic agreement does not establish a safe equipment design. None is fully applicability-approved by this verification. No accepted FV-P1-UNIT-001 report was located; complete unit-contract acceptance remains BLOCKED. Native numerical checks proceed independently.

The test suite covers all methods at nominal/low/high flow, missing required parameters, zero/nonfinite primary inputs, physically invalid negative inputs, negative/nonfinite parameters, extreme flows, repeatability and dimensional mismatch. Additional guards cover fractions, efficiency, pressure ratio, moisture ordering and gamma bounds. Heat duties may legitimately be negative: area uses magnitude and these cases pass. Zero product moisture and zero sensible addition have legitimate meanings; their semantics must not be confused with zero equipment size. Optional pump efficiency may be omitted; phase-change sensible duty defaults to zero, which requires explicit assumption review.

Raw methods accept declared native numbers, not unit-bearing objects. Incorrect units are exercised at the canonical converter/adapter boundary. The converter reports unresolved structured results; the costing adapter raises UnitResolutionError. Initial test-author assumptions about those API error styles were corrected before final testing; those were test harness mistakes, not product defects. Historical exploratory logs are not acceptance results.

## ion_exchange_capacity

Species-specific working capacity, selectivity, competing ions, breakthrough, cycle and freeboard unverified. Not an exhaustion simulation.

## vaporizer_area

Phase-consistent duty, boiling regime, U, fouling, pinch and correction factor need review. Raw method consumes duty, not latent heat.

## gas_compression

Single-stage ideal constant-k screening at Z=1. Multiplying by Z is not a rigorous real-gas compression path; condensation/intercooling and discharge temperature need review.

## phase_change_duty

Properties must match mixture and pressure. Duty magnitude, not a complete signed energy balance. Omitted sensible enthalpy defaults to zero.

## evaporated_water

Wet-basis moisture, conserved dry solids, no solids losses/reaction. Moisture target is an assumption.

## ion_exchange_ebct

Bed contact time is selected, not inferred resin performance; capacity, breakthrough and freeboard need review.

## vessel_hold_up

Steady continuous flow; no kinetic, batch-cycle, gas holdup, geometry or mechanical verification.

## pump_duty

Use differential pressure, not inlet/absolute pressure. Check equivalent total head, efficiency, NPSH, fluid and pump selection separately.

## exchanger_area

Thermal area only; U and F must reflect configuration, fouling and phase behaviour; terminal temperatures must support LMTD.

## filter_area

Hydraulic area only; cake resistance, solids loading, cycle, pressure and effective area may govern.

## gas_volume

Actual single-phase gas volume, not standard flow. Z and mixture MW require justification; no EOS/phase check.

## dryer_chamber

Gas holdup envelope only; particle residence, evaporation, droplet kinetics and vendor geometry may govern.

## Corrective tickets — do not repair in this task

**SIZE-C01:** compressor cancellation inside its declared mathematical domain 1<gamma<=2. At nextafter(1,2), PR=2, MW28, T300 K, 3600 kg/h and eta=.75, expected 82.3306617378 kW, observed 118.7780374022 kW. Review stable evaluation and a physically justified gamma domain. This is an extreme numerical boundary, not proof normal compressor predictions differ by 44%.

**SIZE-C02:** shared area function converts True to 1 before its numerical type guard. Both exchanger and vaporizer accept it and return 0.1 m2 for U500, LMTD20, F1. Validate type before taking magnitude, retaining signed heat-duty support.

**SIZE-C03:** at pump efficiency 1e-320, the main sizing coordinate is finite but auxiliary shaft power is infinite. Reject unsupported efficiency/output overflow explicitly. This tests numerical safety, not a physically realistic operating efficiency.

Unsupported physical scenarios (condensing compressor, wet/dense-gas state, cake-limited filtration, transient or batch hold-up, particle-limited dryer) are not automatically recognised by native scalar equations. Metadata warnings exist but do not prove suitability. These are applicability evidence gaps, recorded separately from confirmed arithmetic/input defects.

## Dimensional review and unresolved acceptance

Flow quantities have dimensions L³/T or M/T; density is M/L³; time T; U is power/(L² temperature); LMTD is a temperature difference; fractions, efficiency, Z and gamma are dimensionless; absolute pressure is force/L². Ion equivalents/capacity must use the same equivalent basis. The equations reduce to volume, area, power, mass/time or volume/time as recorded in the register. Pump output is a historical flow-pressure coordinate proportional to hydraulic power, not bare pump volume or shaft horsepower.

For each of the 12 methods, acceptance of arbitrary source-unit extraction → canonicalisation → sizing → costing is **BLOCKED**, rather than passed by the native-equation examples. The missing prerequisite is an accepted FV-P1-UNIT-001 report. This is an evidence gate, not 12 pytest skips. Five selected alternative-unit examples and one traceable adapter case provide limited executable evidence, not universal converter verification.

All low/high examples scale throughput with assumptions held fixed. No published certified capacity envelope exists in the sizing registry. An extremely large mathematically finite result must not be interpreted as an approved industrial design or permission to extrapolate a cost correlation.
