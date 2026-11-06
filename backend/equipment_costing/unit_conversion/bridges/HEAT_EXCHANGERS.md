# Heat-exchanger input resolution

`heat_exchanger.py` is a workbook-independent adapter used by canonical
`service.evaluate()` and the existing automatic input resolver. No project tags,
source-workbook prices, numeric thermal defaults or new costing correlations are
embedded in it. The legacy `thermal.py` duty/pair route remains compatible.

The LLM selects a structured `thermal_basis`: linked hot/cold inlet/outlet stream
keys, provisional duty side, duty method, flow arrangement, phase-change basis,
reference/steady-flow assumptions, reconciliation policy and rationale. Python
validates source membership and calculates:

- Signed same-side enthalpy-flow differences on an explicitly declared common
  reference; a wrong-sign selected duty is rejected, never silently absoluted.
- LMTD from four source/explicitly assumed terminal temperatures, with the
  equal-terminal-difference limit and positive-temperature-approach checks.
- Alternatively sensible heat from total mass flow, Cp and temperature change;
  latent heat from mass flow, latent heat, phase fraction and an explicit
  sensible allowance; or an explicitly labelled assumed duty.
- Area through the existing sizing registry and conversion to the selected
  canonical costing model's native area unit.

U, correction factor, missing temperatures and property/duty assumptions remain
editable inputs. No thermodynamic package or external research is invoked.
Existing non-thermal user inputs and manual prices are preserved. Source values
retain worksheet/cell evidence; derived inputs and AI assumptions have distinct
statuses. Role choices and calculated thermal warnings are visible in the
Equipment conversion drawer, and warnings are included in the pricing result.

Shared utility descriptions naming multiple exchangers require an explicit
allocation before their total enthalpy difference can be used. Provisional side
selection retains conflicting duties without certifying a balance. Strict
reconciliation instead requires both sides and an explicit tolerance. The
shared-utility detector is heuristic; it cannot prove an engineering boundary.

Limitations: preliminary area only, not mechanical design, phase-equilibrium or
property validation. Countercurrent/parallel terminal models do not validate
multipass arrangements. LLM assumptions and common-reference declarations need
engineering review. Inconsistent source enthalpies can yield extreme provisional
areas/prices; warnings do not establish accuracy. Cost-model applicability,
material/pressure factors, source graph quality, extrapolation and escalation
remain separate canonical costing concerns.

Tests: `backend/tests/test_heat_exchanger_basis.py` plus existing automatic-input
and conversion regression tests. Private project rerun audits remain under the
ignored local `outputs/` directory, not public source control.
