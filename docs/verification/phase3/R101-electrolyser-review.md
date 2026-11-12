# R101 · Cost basis review for Charlie's R-101 water electrolyser

**Date:** 11 November 2026 · **Owner:** Engineer 1 · **Status:** recommendation for the founder to accept or reject. No production code or coefficients were changed.

**Depends on:** PR #7 (Phase 3 plan and Garrett check), PR #8 (prefer OpenPyTEA), PR #14 (minimum-size floor). The figures below come from the code on the PR #14 branch.

## Why this item matters

R-101 is **$3.44 M of Charlie's $5.06 M** equipment total (68%), as priced in the 11 November AI run with `openpytea:electrolyzer_nrel_2008`. A ±20% change in R-101 moves the whole equipment total by about ±14%, more than every other item put together.

All prices are **CPI-proxy USD, September 2026**: BLS CPI-U (`US_CPI_U_NSA_1982_84`), from the source year's annual average to 2026-09 (336.940). CPI measures consumer purchasing power. It is not CEPCI or a vendor quote, and no CEPCI series is pinned yet. Equipment indices and CPI have diverged since 2020, so the escalation itself carries an error of the order of ±10–15%.

Charlie's hydrogen rate and electrical load are private and are **not** stated here. Only prices, ratios and $/kW appear.

## 1. Models that can price an electrolyser

I searched every costing library in the registry: OpenPyTEA, Garrett (154 curves), Turton, Nottingham and the additional models. **Only the three OpenPyTEA "Electrolysis" models apply.** Garrett has no electrolyser curve. Its nearest entries, electric generators and motors/drives, are not electrolysers.

| Model ID | Equation | Coefficients | Size coordinate | Published bounds | Cost year | Scope (per source) | Reference |
|---|---|---|---|---|---|---|---|
| `openpytea:electrolyzer_nrel_2008` | Offset power law, C = a + b·S^n | a = 0, b = 224,490 $, n = 0.6156 | H₂ production, kg/h | 0.1–100 kg/h | 2008 in OpenPyTEA (see caveat) | Uninstalled electrolyser **system** (stack and BoP, including power electronics, about 22% of cost). Fitted to a pre-2008 literature and vendor survey of mostly small PEM units, with alkaline at larger sizes | Saur (2008), NREL/TP-550-44103, §5.1 Eq. 1, citing the NREL Electrolysis Milestone Report (2008). doi:10.2172/944892 |
| `openpytea:electrolyzer_pem_current_doe_2016` | Power sizing, C = C₀·(S/S₀)^f | C₀ = $2,132,440 at S₀ = 1,500 kg/day, f = 0.9255 (two-point fit) | H₂ production, kg/day | 1,500–50,000 kg/day | 2016 | PEM **total uninstalled capital** = stack ($342/kW) + mechanical BoP ($136/kW) + electrical BoP, rectifier and transformer ($121/kW). Installation is a separate +12%. Assumes **high-volume manufacturing (700 MW/yr)**. 300 psi outlet. 55.8 kWh/kg system, 50.4 kWh/kg stack | Peterson, Vickers & DeSantis, DOE Hydrogen Program Record 19009 (2020), Table 2, "Projected Current (2019)" |
| `openpytea:electrolyzer_pem_future_doe_2016` | Power sizing | C₀ = $1,337,870 at 1,500 kg/day, f = 0.8621 | H₂ production, kg/day | 1,500–50,000 kg/day | 2016 | Same scope, for **2035 technology** (market entry 2040): stack $143/kW, 700 psi outlet, 51.4 kWh/kg system | Same record, "Projected Future (2035)" |

The app tags all three `cost_scope = purchased_equipment`, from the CSV remark "Purchased cost". The sources describe the cost of an uninstalled, packaged **system**. "Purchased" is correct, but it means the whole electrolyser package, not one vessel (see §5).

I checked the sources directly. Saur's Eq. 1 is y = 224.49·x^0.6156, with y in thousands of dollars and x in kg H₂/h, "accurate for the size ranges between 0.1 kg/hr and 100 kg/hr". The DOE Table 2 values match the CSV notes ($599, $379, $460 and $233 per kW, and 3.56, 3.53, 119 and 118 MW).

## 2. R-101 priced with each model

Each model was run through `backend.equipment_costing.registry.estimate_cost` with default options (`below_range_policy = "minimum_size_floor"`, from PR #14). The result was translated with `cost_to_future.translate_cost` under the default policy, the same path the app uses. The NREL result reproduces the saved run exactly ($3,442,121).

| Model | Range status | Historical price | CPI multiplier | **2026-09 price** | Equipment total | Change in total | R-101 share |
|---|---|---|---|---|---|---|---|
| NREL 2008 (current choice) | **In range** | $2.20 M (2008) | 1.565 | **$3.44 M** | **$5.06 M** | — | 68% |
| DOE PEM current (2019 tech) | **Below range, floored** at 1,500 kg/day (Charlie is about 1.5× smaller) | $2.13 M (2016) | 1.404 | **$2.99 M** | $4.61 M | −$0.45 M (−8.9%) | 65% |
| DOE PEM future (2035 tech) | Below range, floored | $1.34 M (2016) | 1.404 | **$1.88 M** | $3.49 M | −$1.56 M (−30.9%) | 54% |

**Spread:** $1.88–3.44 M on R-101, a ratio of 1.8. The equipment total ranges from $3.49 M to $5.06 M.

For information only, outside the app's policy: if the two DOE curves were extrapolated down to Charlie's size instead of floored, they would give $2.01 M (current) and $1.30 M (future). The app refuses that extrapolation, and the source fit has only two points, both well above Charlie's size.

## 3. First-principles check: implied $/kW

**Assumption:** the cost is divided by the electrolyser's **system** electrical load at **55 kWh/kg H₂**. This is close to DOE's 55.8 kWh/kg for current PEM, and corresponds to about 50 kWh/kg at the stack plus about 5 kWh/kg of BoP. System load is the right divisor because all three correlations price a system. A stack-only basis of 50 kWh/kg raises each figure by 10%.

| Model | Scope | Year basis | 2026-09 price | **Implied $/kW (55 kWh/kg)** | At 50 kWh/kg | Native $/kW in source year |
|---|---|---|---|---|---|---|
| NREL 2008 | Uninstalled system, small-unit 2007/08 market | 2008 | $3.44 M | **$1,536/kW** | $1,690/kW | $982/kW (Saur's own 62.8 kWh/kg gives $860/kW, matching his Table 2 at 42 kg/h, about $850/kW) |
| DOE PEM current | Uninstalled system, high-volume manufacturing | 2016 | $2.99 M | **$1,336/kW** | $1,470/kW | $952/kW. The source states $599/kW, but for a 3.56 MW unit; the floor charges that unit's price to a smaller load |
| DOE PEM future | Uninstalled system, 2035 technology | 2016 | $1.88 M | **$838/kW** | $922/kW | $597/kW (source $379/kW at 3.53 MW) |

### Comparison with current public sources (2022–2026)

| Source | Figure | Scope |
|---|---|---|
| DOE HFTO PEM technical targets, 2022 status | **$1,000/kW system**, of which $450/kW stack | Uninstalled |
| DOE Hydrogen Program Record 24005 (May 2024, 2022$) | About $2,000/kW installed. Installation roughly equals the uninstalled cost, so about **$1,000/kW uninstalled** | Installed / uninstalled |
| IEA Global Hydrogen Review 2025 (2024 costs) | **$2,000–2,600/kW** outside China; $600–1,200/kW made and installed in China | Installed, large projects |
| IEA commentary on GHR 2026 (Oct 2026, 2025 costs) | Alkaline $1,900–2,500/kW outside China; $500–1,100/kW in China | Large projects, probably installed |
| Fraunhofer ISE for CATF (2021) | 5 MW about 1.4× the $/kW of 100 MW (alkaline) | Small-scale penalty |

The current **uninstalled-system** benchmark for a Western PEM unit is about **$1,000/kW (2022$)**. A ~2 MW unit carries a small-scale premium of 0–40%, which gives $1,000–1,400/kW (2022$). CPI-escalated to 2026-09 (×1.151, BLS 2022 annual average 292.655; this observation is not yet in the app's catalogue), the band is **about $1,150–1,610/kW**. On Charlie's load that is **$2.6–3.6 M for R-101** and **$4.2–5.2 M for the equipment total**.

- **NREL 2008 ($1,536/kW)** sits inside the band, near its upper end. That is plausible for a ~2 MW Western unit. The agreement is partly coincidence: costs fell from 2008 to about 2020, and the general CPI escalation roughly offsets that fall.
- **DOE current ($1,336/kW)** also sits inside the band. But it reaches that figure by charging Charlie the price of a 3.56 MW unit (the floor), while assuming 700 MW/yr factory economics. These two biases partly cancel.
- **DOE future ($838/kW)** is **below** today's uninstalled-system cost for a Western supplier. It describes 2035 technology and should not be used for a plant built now.

## 4. Recommendation

**Keep `openpytea:electrolyzer_nrel_2008` as the base case for R-101 ($3.44 M, CPI-proxy 2026-09).** Report DOE PEM current ($2.99 M) as the low-side sensitivity. Do not use DOE PEM future for a current-build estimate.

Why NREL 2008 is the most defensible of the three for a preliminary (AACE Class 4/5) estimate:

1. **It is the only model in its published range** at Charlie's size. Both DOE models need the below-range floor, a documented assumption, not validated data.
2. **Its scope is clear and correct**: a complete uninstalled electrolyser system, with stack, power electronics and BoP in one line.
3. **Its implied $/kW sits inside today's public band** for uninstalled Western PEM or alkaline systems at small scale.
4. **It is not optimistic.** DOE's figures assume high-volume manufacturing that a ~2 MW purchase will not get.

What the founder should know when accepting it:

- **The source data is old** (a 2007/08 survey of mainly small units). Its current agreement with the market comes from offsetting effects, not a recent fit.
- **Dollar-year ambiguity.** OpenPyTEA labels the curve 2008. Saur's H2A analysis used 2005 dollars, and the Milestone Report fit does not state a year. On a 2005 basis (CPI 195.3, BLS annual average, not in the catalogue) R-101 would be **$3.79 M** ($1,694/kW) and the total **$5.41 M (+7%)**. This is unresolved until the Milestone Report is checked.
- **CPI is not CEPCI.** A pinned CEPCI series could move every Charlie item, R-101 most of all.
- **A Chinese alkaline system** could cost 50–60% less ($0.6–1.2 k/kW installed per IEA), roughly **$1.5–2.0 M** off R-101. If Charlie is likely to buy one, the decision should be explicit.

If rejected, the alternative is to **replace the model with a sourced $/kW basis**: the current DOE $1,000/kW (2022$) status × CPI × Charlie's system load, giving about $2.6 M (total about $4.2 M). The code would need a new, cited "unit-rate" model. That is outside this review.

## 5. What a vendor quote or current public source must confirm

To replace this estimate, a quote (or a dated public source at ~2 MW) must state:

1. **Rated power** (MW DC at the stack and MW AC at the grid) and **specific energy** (kWh/kg) at beginning and end of life, so the $/kW is on a known basis.
2. **Technology and origin**: PEM or alkaline; Western or Chinese stack and BoP.
3. **Scope split**: stack(s); power supply (transformer and rectifier); gas–liquid separation; H₂ purification (deoxo, dryer) to the purity the gas fermentation needs; water treatment; cooling; controls; enclosure. Also what is **excluded**: installation and EPC, civil works, compression, O₂ handling, commissioning, spares.
4. **H₂ outlet pressure** and turndown range, which must match the fermenter feed (no compressor is priced separately in Charlie).
5. **Delivery terms and price date** (ex-works or DDP; currency; validity), so the right index is applied without double-escalating.
6. **Stack warranty, degradation and replacement interval.** These are OPEX and replacement CAPEX, not purchase price, but they set the true cost.

### Scope checks for Charlie's estimate (follow-ups, not changed here)

- **Possible double counting**: all three models already include water treatment in their BoP. Charlie also prices separate ion-exchange units (T-101AB, T-102AB, about $42 k together). If those units feed only R-101, one of the two is counted twice. This is small either way.
- **Installation factor**: DOE adds only 10–12% to install a packaged electrolyser (Record 24005 assumes about 100% for a full EPC site). A generic process Lang or Hand factor of 3–5× applied to $3.44 M would add an implausible $7–14 M. The CAPEX stage should treat R-101 as a packaged system with its own installation factor.

## Reproduction

```python
# Python, repo root, PR #14 branch; size from the private run file (not committed)
from backend.equipment_costing.registry import estimate_cost
from backend.equipment_costing.cost_to_future.cost_translation import translate_cost
r = estimate_cost("openpytea:electrolyzer_pem_current_doe_2016", size_kg_per_h, size_unit="kg/h")
translate_cost(r.historical_amount, currency="USD", source_period="2016",
               method_id="openpytea:electrolyzer_pem_current_doe_2016").amount
```

Sources checked on 11 November 2026: Saur (2008) NREL/TP-550-44103 §5.1 and Table 2; DOE Record 19009 Table 2; DOE HFTO PEM electrolysis technical targets; DOE Record 24005; IEA Global Hydrogen Review 2025 executive summary; IEA commentary on Chinese electrolysers (15 Oct 2026). The IEA 2024 and BNEF figures were seen only through press coverage and are not used above.
