# Newly established reference acceptance — METHOD-001

Date: 11 November 2026. Reuse the eleven already corroborated native physical
relationships and inspected-source ledger at
`docs/verification/phase1/closure/evidence/sources_and_scope.md`. The original
publication-of-implementation remains unknown. Replacement-reference acceptance
here is for stated screening identities, not industrial design certification or
an external reviewer's signed approval.

## Compressor — resolve the exact scope of the Z multiplier

The existing arithmetic is

`power = m_dot * (R/MW)*T1*Z*k/(k-1)*[(P2/P1)^((k-1)/k)-1]/eta_s`.

The NASA ideal-gas reference remains applicable at Z=1. An additional direct
reference is the author's [Fluids documentation, isentropic_work_compression](https://fluids.readthedocs.io/fluids.compressible.html#fluids.compressible.isentropic_work_compression),
inspected version 1.3.1. Its explicit constant-property expression and derivation
match the existing equation after molar/mass and J/kW conversion. No implementation
code was imported or copied; its underlying cited textbook was not independently
inspected. The published numerical example supplies an additional independent
reference, COMP-PUBLISHED in `additional_references.json`.

[Joe Honeywell, JM Campbell, May 2009, The Sensitivity of k-Values on Compressor Performance](https://www.jmcampbell.com/tip-of-the-month/2009/05/the-sensitivity-of-k-values-on-compressor-performance/)
provides independent engineering context: property selection affects shortcuts,
Z varies across compression, and stage/property treatment matters. This supports
a qualified approximation, not a universal real-gas validation. No numerical
operating envelope is imported from that discussion.

### Independent derivation

Assume a fixed compression exponent and the surrogate path `p*v^k=constant`.
Let `v1=Z*R_specific*T1/p1`. Integration of reversible pressure work gives

`w = integral(p1,p2) v1*(p1/p)^(1/k) dp`

`= k/(k-1)*p1*v1*[(p2/p1)^((k-1)/k)-1]`.

Substitute the supplied representative Z state approximation, then divide by
isentropic efficiency and multiply by mass rate. This independently establishes
the mathematical shortcut, including its linear Z factor. For k=1.5 and p2/p1=8,
the pressure term is exactly1; the COMP-Z08 and COMP-Z12 fixtures follow directly
using the independent gas constant and supplied synthetic Z values. These do not
claim a real gas actually follows either constant-Z path.

### Why this is not general real-gas isentropic work

For a general fluid, `ds = (cp/T)dT - (partial v/partial T)_p dp`.
When `v=Z(T,p)*R_specific*T/p`, the temperature derivative contains the derivative
of Z as well as Z itself. The ideal-gas temperature/pressure exponent therefore
does not generally follow from a real-gas cp/cv value. The surrogate derivation
must not be described as an exact EOS isentrope. Frozen or effective properties
must be justified for the particular composition, states and purpose.

Use consistent absolute pressures, absolute inlet temperature, molecular weight,
representative compression-path Z, an appropriate effective k and isentropic
rather than polytropic efficiency. Inlet Z alone is not proof of representative
path Z. Variable heat capacity, property variation, near-critical regions,
condensation and multistage/intercooled duties need EOS/enthalpy-based, segmented
or specialist treatment. No universal pressure-ratio, temperature or Z threshold
can be justified from these references. Code guards `1<k<=2` and `0<eta<=1` are
mathematical admission limits, not qualified operating limits. The value is a
preliminary gas-power estimate, not a motor nameplate selection.

**Decision:** PASS as a documented frozen-property preliminary approximation;
NOT ACCEPTED as a generally accurate real-gas compressor model. Native audit
warnings now explicitly carry this distinction; no arithmetic was changed. UI
presentation of those nested warnings is a separate integration responsibility.

## Three active estimators missing from the 12-ID registry count

These were not silently classified as helpers to avoid verification. They are
active recipes in the existing equipment conversion service. Each receives a
new independent numerical case and a conditional applicability record.

1. **vessel_mass:** independently subtract inner from outer cylinder volume,
   multiply by supplied material density, add explicitly supplied head/auxiliary
   mass. The annular-cylinder derivation yields the literal expected value in
   MECH-SHELL. It does not determine thickness, head geometry, pressure-code
   compliance or corrosion allowance. Geometry and density are inputs.
2. **vessel_productivity:** volumetric productivity is production rate per
   relevant working volume. Apply the supplied production allocation, divide by
   supplied productivity, then by working fraction to get gross/design volume.
   PROD-VESSEL is exact rational arithmetic. This is an explicit scenario based
   on qualified productivity, not a kinetics, yield or mass-transfer model.
3. **mixing_power:** multiply the computed gross/design vessel volume by a
   power density explicitly defined per that same volume basis. MIX-POWER uses
   exact rational arithmetic. The native method computes `Q*time/f_working`, so
   its volume is gross/design. The prior wording “working/design” was ambiguous;
   its audit text now says gross/design and warns that a working-volume P/V
   requires basis conversion. No power-density coefficient, design correlation
   or numerical result was changed or invented.

NIST mass/volume/density and SI conventions are reused as dimensional references;
the three equations are independently stated definitions/conservation/geometry,
not claims of recovered textbook design correlations. Their tolerances concern
floating-point arithmetic, not the uncertainty of the supplied assumptions.
