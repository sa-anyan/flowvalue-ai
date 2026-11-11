# UNIT-003 — Boiler horsepower source review

**Decision: PARTIAL.** Source-native identity remains usable for the small
package boiler chart; conversion to thermal watts remains unsupported.

Inspected the actual Garrett Appendix 1 PDF, printed page 262 / PDF page 12,
including the small-capacity axis, steam-capacity axis and footnote. The local
PDF and SHA-256 are recorded in `evidence/source_pdf_manifest.json`. Page images
were rendered at 1600 pixels and visually inspected; full page text/images are
not redistributed in this report. Text extraction alone was not used to repair
the ambiguous footnote.

The small-package curve uses an HP-labelled capacity axis; large boilers use a
separate steam mass-rate axis. The footnote associates one HP with a Btu figure,
but the scan displays ambiguous digits/punctuation and does not supply a clear
per-hour denominator. That is insufficient to establish a unique thermal-power
conversion. The steam axis does not establish feed-water/steam enthalpies,
pressure/quality or a universal evaporation-to-thermal-power relationship.

The exact affected model is **G262-018**, small package / 150 psi. Its current
contract is `boiler_power` in `boiler_hp`, identity multiplier 1. Explicitly
supplied source-native capacity can reach that existing model, preserving its
source convention. This is not mechanical horsepower and is not approved as a
universal thermal rating. Other boiler configurations using a supplied steam
mass rate retain their own contracts.

[NIST SP 811 B.9](https://www.nist.gov/pml/special-publication-811/nist-guide-si-appendix-b-conversion-factors/nist-guide-si-appendix-b9)
lists a standardized thermal boiler-horsepower convention (9809.50 W). Its
existence does not prove that this historical chart uses that exact convention.
No generic standardized factor, guessed Btu/h factor, steam-enthalpy assumption
or mechanical horsepower factor was attached to Garrett's `boiler_hp`.

To close **UNIT-002-C01**, recover a clearer original/erratum or author/publisher
statement establishing the footnote's number, time basis, Btu convention and
whether this is thermal output or another boiler-rating convention. Then verify
a source-specific bridge against independent thermal reference examples and
retain the distinction from purchased fuel input and mechanical power.

Regression: boiler_hp -> boiler_hp remains recognized; boiler_hp -> W remains
unresolved. No boiler equation, chart reading, coefficient, source range or
source registry was changed. The catalogue's remaining historical boiler
classification is deliberately not promoted to PASS.
