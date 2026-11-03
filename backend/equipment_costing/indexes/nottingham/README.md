# Nottingham CEEDG501 equipment-price index

Source: University of Nottingham, CEE Design Consultants, *Cost Estimation – Capital Plant*, CEEDG501 revision history Rev 3, 7 November 2017. File SHA-256: `9b626ffe656fdde1c857a978393380f971070dcfaca500927626e7c962584b57`. The PDF page footers identify Rev 2; both statements are retained.

## Implemented equipment correlations (section 4, printed page 11 / PDF page 11)

| Family | IDs | Historical formula | Units/basis | Scope |
|---|---|---|---|---|
| Motor-power pumps | `N501-PUMP-<MATERIAL>` | `C=2000 F P^0.7` (printed `F*P*2000*P^-0.3`) | GBP, 2015; model assumes P in kW because source does not state motor-power units | Preliminary purchased pump, not a specific positive-displacement slurry pump quote |
| Fabricated steelwork | `N501-STEEL-<MATERIAL>` | `C=W*r` | W metric tonnes, GBP, 2016; r=4,000 carbon, 5,000 lined carbon, 12,000 stainless | **Fabrication-only component**, not a complete tank/reactor package |
| Pipe supply | `N501-PIPE-<MATERIAL>` | `C_{GBP/m}=F*e^(0.6*d)` | d nominal inches; F=1.5 PVC/ABS, 6.5 carbon, 50 stainless; GBP, 2017 | Supply-only per unit length; converted to GBP/ft for shared quantity aggregation |

Model parameters use exact declared units; input conversion and engineering suitability remain separate. These estimates are provisional historical amounts. Installation is **not** supplied by these correlations. A full vessel or pressure-rated liquid CO2 package **is not priced solely by fabricated metal weight**.

### Additional selectable graph candidates (section 4.4, PDF page 12)

Two-stage ion-exchange and packaged reverse-osmosis **water-treatment packages** are exposed as `N501-WATER-ION_EXCHANGE_TWO_STAGE` and `N501-WATER-PACKAGED_RO` using approximate manual graph anchor readings for flows 25–200 m3/h, 2012 GBP. These are **low-confidence, visually interpolated**, require `allow_unverified=True`, and are not standalone tank prices. No extrapolation is allowed. They remain optional; users may select another index.

## Index switching in the existing workflow

1. GET `/api/catalogue`: both Garrett and Nottingham models are returned with `source`, `id`, `size_unit` and limitations.
2. For a project equipment plan row select `curve_id="N501-PUMP-CAST_STEEL"`, `source="nottingham"`, `size=5`, `size_unit="kW"`. The pipeline also recognises the `N501-` prefix if `source` is omitted.
3. The shared `calculate_total_cost` calls the registry. The Nottingham correlation calculates GBP(2015) and records its method and source page.
4. Where price translation is enabled, the existing cost-translation module uses ONS UK CPI (2015/2016/2017 base years and September 2026 target) as a **general-inflation proxy**, *not* an equipment-specific index.
5. After translation, the existing dated FX snapshot converts GBP to USD for the study price basis; source GBP and FX audit remain in evidence.
6. Existing CAPEX stage consumes the resulting purchased-equipment components. Installed cost remains unavailable unless supported installation scope is added separately.

Manual prices and documented external comparables remain available through their existing independent paths; legacy Charlie equipment prices are **not** used by this index.

## Other methods extracted (NOT standalone equipment price models)

- Section 3.2, page 5: plant-level Lang factors, already implemented under `backend/capex/indexes/nottingham`; solids 3.1, mixed 3.6, fluids 4.7, bio-processing 7.8, water treatment 3.5. Never apply as an additional equipment purchase price.
- Section 3.3, page 6: `C2=C1*(S2/S1)^n`, generic size exponent approximately 0.6 only when an independent comparable `C1` exists; not an independent base price.
- Section 3.4, page 7: Bridgewater whole-plant step-count capital formula, 2000 USD: `C=3200*N*(Q/s)^0.675` if Q >= 60,000 t/y; else `C=280000*N*(Q/s)^0.3`. Never allocate automatically to individual assets or stack on equipment-factor CAPEX.
- Section 4.4, page 12: two graph-only curves, **two-stage ion exchange** and **packaged RO**, cost in 2012 GBP thousands vs water flow (axis 0–250 m3/h). No printed coefficients/anchor table; optional **approximate manual visual anchors** are coded and marked unverified. They price water-treatment packages, not individual IX vessels. Polishing notes: mixed-bed adds 50% to IX cost; EDI doubles RO plant cost, but these optional allowances are not added automatically.
- Section 4.5, page 12: approximately GBP 10,000/m2 for pharmaceutical/bioprocessing **facility floor area** on a 2015 basis; do not use as reactor equipment purchase cost.
- Section 4.6, page 12: external 2002 US DOE plant-unit cost curves at https://www.osti.gov/scitech/servlets/purl/797810; not inspected or imported.

## Quick focused checks

```python
from backend.equipment_costing.registry import estimate_cost, list_equipment_models
assert any(m['id']=='N501-PUMP-CAST_STEEL' for m in list_equipment_models(source='all'))
p=estimate_cost('N501-PUMP-CAST_STEEL',5,source='nottingham',size_unit='kW')
assert round(p.amount,2)==round(2000*1.5*5**.7,2)
assert p.equipment_cost == p.amount
assert p.installation_cost is None
```

Run one targeted existing pipeline/cost-translation smoke check before deploying. All new formulas have source pages and explicit assumptions; no automatic supplier quotation is asserted.
