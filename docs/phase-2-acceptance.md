# Phase 2 — core workflow acceptance

Verified locally on 27 October 2026. All examples are synthetic; this is workflow verification, not engineering benchmark validation.

| Workflow | Result |
| --- | --- |
| CSV import with source/destination endpoints | Three validated streams; connected process diagram |
| JSON stream table | Validated stream imported; existing financial/BOM basis retained |
| Full project JSON | Equipment and financial assumptions replaced after validation |
| Native DWSIM XML | Supported heat exchanger priced; incomplete reactor explicitly excluded |
| Native import without supported complete sizing | Existing BOM retained, with mixed/incomplete scope warnings in dashboard and exports |
| Trusted BioSTEAM snapshot | External costs and economics imported; synthetic demo label retained |
| Invalid JSON | Useful error; previous project retained |
| Diagram equipment edit | Applied duty change returned to dashboard; unapplied draft removed prior result display |
| Material dropdown | Carbon steel → stainless changed demo NPV from $6.11M to $5.99M |
| Financial slider | Discount rate changed to 10.5%, with updated metrics and export inputs |
| Calculation service outage | Project retained; downloads blocked; retry restored calculations |
| Excel download | Active assumptions, real NPV/IRR formulas, equipment and scope notes present |
| PDF download | Two pages, active assumptions/results, both critical scope warnings beside capital allocation; both pages visually checked |
| Cloud project workflow | Phase 1 already verified sign-in, save, refresh, history restore and next revision |

Regression coverage: backend parser equivalence and active-scenario report tests; frontend scope recomputation, retained-equipment warnings and malformed browser-draft tests. CI runs both suites.

Operational limitations: CSV/JSON stream tables do not infer equipment sizes; DWSIM needs supported saved sizing inputs. Financial assumptions retained during native/stream-only imports require operator review. BioSTEAM uses trusted result snapshots. Cloud AI remains unconfigured by owner choice. Licensed CEPCI and engineering benchmarking are later phases.
