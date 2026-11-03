# Equipment-through-financial explorer rollout

The Equipment and CAPEX primary workspaces are retained outside the shared supporting-methods explorer, preserving their card/drawer and capital-investment interactions. OPEX, Revenue and Financial Model now have a common snapshot → category folder → searchable record → field/evidence inspector. Year selection changes the displayed saved period, not the baseline assumptions.

OPEX folders cover materials/catalysts, equipment energy, workforce and the operating ledger. Revenue separates product sales, commercial payments, avoided costs and the annual revenue schedule; an empty commercial folder is shown as empty, without adding assumed income. Financial folders expose cash flow, investment metrics, annual periods and the saved financial basis; the cumulative/annual financial chart remains available.

Existing editors, research consent, specialist review, commercial strategy, source evidence, exports, save/version controls and comparison operations are accessible under Assumptions & methods → Study controls & reviews. Edit assumptions opens this section without issuing a save or AI request. CAPEX comparison shortcuts open the same supporting controls. Equipment's unsaved-edit handling remains unchanged.

Display parsing accepts valid numeric decimal strings for CAPEX rather than labelling saved prices missing; backend calculations are unchanged. Boolean fields remain Yes/No, and absent values remain Not provided. Record detail uses wrapping field cards rather than wide tables. Existing detailed tables remain available inside the supporting controls.

Read-only browser checks on saved assessment 2f2c8ed1d44e49dba0d73d965e81659b passed across Equipment, CAPEX, OPEX, Revenue and Financial Model at desktop/mobile widths. Checks covered record folders, preserved save controls, Equipment drawer access and absence of horizontal page overflow. No saved data mutations or paid calls. TypeScript passed; QA artifacts reside in ignored outputs/stage-explorers.
