# FV-P1-SIZE-001 independent references

Original equation provenance is **SOURCE NOT VERIFIED for all 12**: the implementation contains equations/scope strings but no original authoritative citation. The references below independently cross-check physical identities; they do not establish that these were the original implementation sources or industrial validation.

## Primary references checked

- **DOE-heat:** [DOE Handbook 1012, volume 2](https://www.energy.gov/documents/doe-hdbk-1012-92vol2), PDF page 61, printed page 39: heat-transfer rate and area identity. Rendered page inspected. The independently selected correction factor remains a configuration assumption.
- **DOE-phase:** [DOE Handbook 1012, volume 1](https://www.energy.gov/sites/default/files/2026-04/DOE-HDBK-1012-92_VOL1.pdf), PDF page 70, printed page 44: mixture enthalpy/latent-heat definitions. Rendered page inspected. Constant-property duty follows the first law; mixture properties are not supplied by this method.
- **EPA-EBCT:** [EPA PFAS treatment webinar, April 2024](https://www.epa.gov/system/files/documents/2024-05/epa-sdws-pfas-regtrmt-webinar_slides_april-30-2024.pdf), PDF page 52: contact time and hydraulic loading definitions. Rendered page inspected. Published examples do not establish universal design bounds.
- **EPA-capacity:** [EPA 600/2-77-152](https://nepis.epa.gov/Exe/ZyPURL.cgi?Dockey=20014PLJ.TXT), Appendix A, printed page 36: capacity measured in ionic equivalents per resin volume. Our cycle-load/working-capacity envelope is an independent conservation derivation, not a verified complete resin design correlation.
- **NASA-compressor:** [NASA compressor thermodynamics](https://www.grc.nasa.gov/www/k-12/airplane/compth.html): ideal constant-specific-heat isentropic work and efficiency. Supports Z=1 reference only.
- **NASA-state:** [NASA equation of state](https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/equation-of-state/): ideal gas relation. Do not reuse that webpage's rounded/inaccurate temperature-offset examples; canonical Celsius offset is 273.15 K.
- **Constants:** [NIST CODATA constants](https://physics.nist.gov/cuu/Constants/Table/allascii.txt): gas constant; independent R = exact Boltzmann constant × exact Avogadro constant. [NIST SP 811](https://www.nist.gov/pml/special-publication-811) supplies SI conventions. Pump coordinate reconstructed from defined US gallon, inch, pound and standard gravity; no production converter used for its expected value.
- **Residence:** [TU Dresden, David Kneis, residence times](https://wwwpub.zih.tu-dresden.de/~kneis/teaching/sysan/04_residenceTimes/04_residenceTimes.html): steady hold-up/flow identity and limitations of residence-time models. Does not validate drying kinetics or vessel geometry.
- **Moisture:** [University of Massachusetts moisture analysis teaching material](https://people.umass.edu/~mcclemen/581Moisture.html): moisture/dry-solid basis; evaporation reference independently derived by conserving dry solids.

## Independent numerical evidence

`backend/tests/fixtures/sizing_verification/references.json` records each nominal input, literal independent expected value, units, intermediate calculation and method-specific tolerance. `numerical_verification_results.csv` compares actual values for low/nominal/high throughput and records four failing boundary cases. Low and high mean 0.01× and 100× the chosen example, **not manufacturer-certified ranges**.

Simple product identities use relative tolerance 1e-13; area/water-loss division 1e-12; gas volume 2e-13; compressor 5e-12; pump coordinate 1e-11 for independent unit reconstruction. Absolute floor 1e-14 applies only to these synthetic examples. These are floating-point verification tolerances, not engineering uncertainty or safety margins. Near-unity-gamma expected power uses 100-digit Decimal enthalpy change. No expected result calls production sizing or costing.

PDF files remain temporary; URLs, hashes and inspected pages are recorded in `evidence/pdf_source_manifest.json`. No third-party implementation was copied. No textbook tables were redistributed.
