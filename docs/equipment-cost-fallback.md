# Range-failure cost fallback — 16 November 2026

This change repairs candidate discovery, not equipment design or a new cost correlation.

When a saved Python sizing recipe is valid but its selected cost correlation rejects
its size, `backend/equipment_costing/fallback.py` offers same-family Garrett models
to the existing bounded input-resolution review. The current implementation covers
OpenPyTEA families declared in the existing library crosswalk and the registered
Turton fermenter. Other additional package models are deliberately not mapped to
bare components. Recipe and physical-quantity compatibility are required; a volume
coordinate alone does not establish equipment suitability.

The reviewer must explain service, materials, pressure and included/excluded scope.
An alternative is a provisional costing configuration, not a validated complete
bioreactor package. Invalid/missing sizing, unsuitable matches, manual/external
prices, user-selected models, protected user inputs and disabled graph policy do
not authorize automatic replacement. The existing equipment-stage lock and AI
opt-in gates still apply. No project baseline is rewritten by these tests.

Python retains source bindings, production allocation, productivity, working
fraction, operating mode and other physical inputs. A new target-unit convention
(such as US gallons) must be explicitly proposed; it is not inferred by the fallback.
Existing unit conventions are retained. Out-of-range OpenPyTEA/Turton models remain
strict: no clamping above the maximum, tuned sizing or hidden parallel vessels.

Garrett scaling is performed by the existing canonical registry:
`C2 = C1 * (S2/S1)**n`, at the same price/currency/configuration basis.
The source is Garrett, Chemical Engineering Economics, Appendix 1, p.255;
model-specific sources, exponents, graph-point verification status, boundary anchor,
extrapolation distance and warnings remain attached to the estimate. Printed
exponents take precedence. The existing explicit provisional-graph policy controls
unverified graph estimates and any fitted-exponent extrapolation. No new 0.6 default
or invented reference price is added. The canonical graph engine may fit its
reference cost using several graph points, so its result need not equal a hand
calculation anchored at one visually read point.

Currency/date translation, quantity, installation and CAPEX aggregation remain in
the existing canonical engines. Historical source prices are not relabelled as
current prices. Focused offline tests cover omitted alternatives, preserved 250 m3
size, explicit gallon conversion, printed exponent 0.53, extrapolation evidence,
quantity, price translation, repeatability, rejected recovery and user protections.
Mocked AI decisions test handoffs; they do not establish real-service suitability
or guarantee a live provider will accept a particular candidate.
