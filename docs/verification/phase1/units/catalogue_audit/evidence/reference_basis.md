# Independent reference basis — UNIT-002

Access date: 11 November 2026. No third-party implementation code was incorporated.

- [NIST SP 811 Appendix B.9](https://www.nist.gov/pml/special-publication-811/nist-guide-si-appendix-b-conversion-factors/nist-guide-si-appendix-b9): quantities, thermal and mechanical power distinctions, mole, SI prefixes, time, mass, volume and customary unit factors.
- [NIST SP 811 Appendix B.8](https://www.nist.gov/pml/special-publication-811/nist-guide-si-appendix-b-conversion-factors/nist-guide-si-appendix-b8): definitions and conversion factors for customary units.
- Prior independently checked engineering references remain in `docs/verification/phase1/closure/evidence/sources_and_scope.md`, plus UNIT-001's static fixtures and UNIT-C01's correction evidence. These are reused, not claimed as new publication provenance.

## Oracle and precision

The audit independently constructs a Decimal oracle from exact inch 0.0254 m, foot 0.3048 m, pound 0.45359237 kg, standard gravity 9.80665 m/s², US gallon 231 in³, Imperial gallon 0.00454609 m³, 60 s/min, 3600 s/h and 86400 s/day. Composite dimensions and factors follow multiplication/division of these definitions. Horsepower is 550 ft*lbf/s; metric horsepower is 75 kgf*m/s; refrigeration ton is 12000 Btu_IT/h. Energy rate is power, not energy. Conventional mmHg and Torr are retained as distinct definitions. No production factor is used to create an expected numeric result.

NIST's displayed thermochemical Btu factor is 1054.350 J (seven significant digits). UNIT-002 uses this independently published factor and propagates half its last displayed place (0.0005 J) through the derived rates. It does **not** authenticate every digit of production's 1054.35026444 J. All other factor comparisons use 2e-12 relative tolerance plus small floating-point absolute floors (normally 1e-13 in conversions). Existing UNIT-001 fixture tolerances remain unchanged. Decimal reference precision is 45 digits; binary rounding is allowed only within these stated tolerances.

Boiler horsepower is not independently validated by its production identity multiplier 1. NIST gives a standardized thermal rating of 9809.50 W; the costing source's historical chart/footnote must be shown to use that convention before implementing a W bridge. Its isolated historical coordinate therefore stays PARTIAL.

## Alias oracle

495 symbol aliases are independently interpreted using explicit canonical spellings, a manual special-alias map and a bounded numerator/time spelling grammar. The 67 English-word meanings are manually enumerated. Registry targets are observed values, not expected values. Every binding and physical quantity is checked; numeric meaning is anchored in the independent unit oracle. Normalized keys do not preserve every original raw spelling, so whitespace/superscript/caret/degree and word-case variants are separately exercised. Superscripts are supported; unadvertised Unicode subscripts are rejected. MW and mW remain different. Generic `gal`, `ton`, `Btu`, `gpm`, and `MGD` are not guessed. The finite catalogue is not an arbitrary unit-expression parser.

## No universal-context claim

Equal gas-reference strings are an admission guard, not scientific proof of identical states. Pressure symbols do not determine absolute/gauge/differential design roles. Generic shaft power, fluid power, installed motor rating, working volume, gross volume, actual flow and standardized flow require equipment/source context. Currency exchange and historic cost escalation are separate economic services, never ordinary unit scaling.
