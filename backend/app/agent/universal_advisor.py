"""Domain-independent cost profiling. Research and market forecasts are separate."""

from math import expm1, fsum, isfinite, log1p
from typing import Any, Literal

from pydantic import Field

from app.engine.costing import Model
from app.financial.dcf_model import FinancialInputs, calculate_dcf


class NamedCost(Model):
    name: str = Field(min_length=1, max_length=120)
    annual_cost: float = Field(ge=0, le=1e15)


class ProjectContext(Model):
    name: str = Field(default="Untitled process", max_length=120)
    description: str = Field(default="", max_length=2000)
    classification: Literal[
        "auto",
        "electrochemical",
        "thermal",
        "biological",
        "separation",
        "circular",
        "specialty",
        "general",
    ] = "auto"
    region: str = Field(default="Not specified", max_length=120)
    raw_materials: list[NamedCost] = Field(default_factory=list, max_length=100)
    utilities: list[NamedCost] = Field(default_factory=list, max_length=100)


class CostComponent(Model):
    id: str
    label: str
    annual_cost: float
    share_pct: float
    parameter: str
    parent: str | None = None


class Recommendation(Model):
    id: str
    title: str
    parameter: str
    direction: Literal["increase", "decrease"]
    suggested_change_pct: float
    range_pct: tuple[float, float] = (-50, 50)
    rationale: str
    driver_share_pct: float
    priority: Literal["high", "medium"]
    npv_base_usd: float | None = None
    npv_stressed_usd: float | None = None
    npv_change_usd: float | None = None
    scope: str = "aggregate cost category"
    origin: str = "calculated exposure and screening rule; not a forecast"


class SectorRule(Model):
    classification: str
    keywords: list[str]
    themes: list[str]


RULES = [
    SectorRule(
        classification="electrochemical",
        keywords=["electroly", "electrochemical", "green hydrogen", "electrode"],
        themes=[
            "Regional electricity contract prices and grid congestion",
            "Grid carbon intensity and hydrogen incentive eligibility",
            "Stack replacement and critical-material supply chains",
        ],
    ),
    SectorRule(
        classification="thermal",
        keywords=["thermal", "pyrolysis", "gasification", "furnace", "boiler", "kiln"],
        themes=[
            "Fuel and steam tariffs",
            "Carbon pricing and emissions compliance",
            "Heat integration and refractory replacement",
        ],
    ),
    SectorRule(
        classification="biological",
        keywords=[
            "ferment",
            "biological",
            "bioreactor",
            "protein",
            "biomass",
            "biofuel",
        ],
        themes=[
            "Substrate volatility, yield and contamination risk",
            "Aeration, cooling and downstream separation energy",
            "Product qualification and offtake prices",
        ],
    ),
    SectorRule(
        classification="separation",
        keywords=[
            "separation",
            "adsorption",
            "psa",
            "distillation",
            "membrane",
            "carbon capture",
        ],
        themes=[
            "Regeneration energy, steam and electricity tariffs",
            "Solvent, sorbent and membrane lifetime",
            "Carbon transport, storage and compliance costs",
        ],
    ),
    SectorRule(
        classification="circular",
        keywords=["recycling", "circular", "waste", "sorting", "plastic"],
        themes=[
            "Waste feedstock quality, collection and sorting costs",
            "Gate fees and recycled-product offtake",
            "Recycled-content mandates and competing virgin-material prices",
        ],
    ),
    SectorRule(
        classification="specialty",
        keywords=["specialty", "pharma", "catalyst", "fine chemical"],
        themes=[
            "Specialty raw-material supply concentration",
            "Product qualification and selling-price erosion",
            "Batch yield, solvent recovery and inventory requirements",
        ],
    ),
]


class AdvisorResult(Model):
    project_description: str
    equipment_summary: list[dict[str, Any]]
    incentive_scenario: dict[str, Any] = Field(default_factory=dict)
    financial_basis: dict[str, float]
    stream_summary: dict[str, Any]
    project_name: str
    classification: str
    classification_basis: str
    region: str
    annualized_capital_cost: float
    total_annualized_cost: float
    lcop: float | None
    cost_components: list[CostComponent]
    category_shares_pct: dict[str, float]
    top_drivers: list[CostComponent]
    recommendations: list[Recommendation]
    research_themes: list[str]
    warnings: list[str]
    assumptions: list[str]
    probability_of_capex_overrun: float | None = None
    probability_basis: str = (
        "Not estimated: no calibrated CAPEX uncertainty distribution was supplied."
    )


def number(value: Any, label: str, default: float | None = None) -> float:
    if value is None:
        if default is None:
            raise ValueError(
                f"Missing {label}; stream tables alone do not establish project economics"
            )
        return default
    if isinstance(value, bool):
        raise TypeError(f"{label} must be a finite nonnegative number")
    try:
        result = float(value)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"{label} must be numeric") from exc
    if not isfinite(result) or result < 0 or result > 1e15:
        raise ValueError(f"{label} must be finite and between zero and 1e15")
    return result


class UniversalProcessAdvisor:
    """Accept assessment results or generic JSON with explicit economic units.

    Generic keys: total_capex_usd, fixed_opex_usd_per_year,
    variable_opex_usd_per_year, feedstock_opex_usd_per_year,
    utility_opex_usd_per_year, operating_years, discount_rate,
    plant_capacity_units_per_year, capacity_factor; or opex_breakdown with
    fixed/variable/raw_materials/utilities. Named costs use name/annual_cost.
    Missing totals are rejected or explicitly disclosed, never inferred from mass flow.
    """

    rules = RULES

    def __init__(self, project: dict[str, Any]):
        if not isinstance(project, dict):
            raise TypeError("Project must be a JSON object")
        self.project = project
        self.context = ProjectContext.model_validate(
            project.get("advisor_context", project.get("context", {}))
        )
        state = project.get("financial", project)
        if not isinstance(state, dict):
            raise TypeError("financial must be an object")
        self.financial = state.get("inputs", state)
        if not isinstance(self.financial, dict):
            raise TypeError("financial must be an object")
        self.warnings: list[str] = []

    def analyze(self) -> AdvisorResult:
        self.warnings = []
        p, f = self.project, self.financial
        if str(p.get("currency", "USD")).upper() != "USD":
            raise ValueError(
                "Advisor economic inputs use USD. Convert other currencies before profiling; no FX conversion is inferred."
            )
        bom = p.get("bom", p.get("equipment_bom", {}))
        items = bom.get("items", []) if isinstance(bom, dict) else bom
        if not isinstance(items, list) or len(items) > 1000:
            raise ValueError("Equipment BOM must have at most 1000 items")
        item_costs = []
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                raise TypeError("Equipment BOM entries must be objects")
            unit_cost = item.get("bare_module_cost_usd", item.get("cost_usd"))
            if unit_cost is not None:
                item_costs.append(
                    (
                        str(item.get("unit_id", item.get("name", f"Unit {index + 1}")))[
                            :120
                        ],
                        number(unit_cost, "equipment cost")
                        * number(item.get("quantity", 1), "quantity"),
                    )
                )
        capex_value = f.get("total_capex_usd", p.get("total_capex_usd"))
        if capex_value is None and isinstance(bom, dict):
            capex_value = bom.get("total_bare_module_cost_usd")
        if capex_value is None and item_costs:
            capex_value = fsum(cost for _, cost in item_costs)
        capex = number(capex_value, "total_capex_usd")
        years = number(f.get("operating_years"), "operating_years", 20)
        rate = number(f.get("discount_rate"), "discount_rate", 0.1)
        if not 1 <= years <= 100 or years != int(years) or rate > 10:
            raise ValueError(
                "Operating years must be an integer from 1-100 and discount rate a decimal from 0-10"
            )
        if f.get("operating_years") is None or f.get("discount_rate") is None:
            self.warnings.append(
                "Missing plant life/discount rate uses 20 years and 10% defaults where absent"
            )
        crf = 1 / years if rate == 0 else rate / -expm1(-years * log1p(rate))
        capital_charge = capex * crf
        breakdown = p.get("opex_breakdown", {})
        if not isinstance(breakdown, dict):
            raise TypeError("opex_breakdown must be an object")
        fixed = number(
            f.get("fixed_opex_usd_per_year", breakdown.get("fixed")), "fixed OPEX", 0
        )
        raw = number(f.get("feedstock_opex_usd_per_year"), "raw material OPEX", 0)
        utilities = number(f.get("utility_opex_usd_per_year"), "utility OPEX", 0)
        raw_items = self.context.raw_materials or [
            NamedCost.model_validate(x) for x in breakdown.get("raw_materials", [])
        ]
        utility_items = self.context.utilities or [
            NamedCost.model_validate(x) for x in breakdown.get("utilities", [])
        ]
        raw = (
            max(raw, fsum(x.annual_cost for x in raw_items))
            if f.get("feedstock_opex_usd_per_year") is None
            else raw
        )
        utilities = (
            max(utilities, fsum(x.annual_cost for x in utility_items))
            if f.get("utility_opex_usd_per_year") is None
            else utilities
        )
        if (
            fsum(x.annual_cost for x in raw_items) > raw + 1e-6
            or fsum(x.annual_cost for x in utility_items) > utilities + 1e-6
        ):
            raise ValueError(
                "Named raw-material/utility costs must be components of their category totals"
            )
        variable = number(
            f.get("variable_opex_usd_per_year", breakdown.get("variable")),
            "variable OPEX",
            raw + utilities,
        )
        if raw + utilities > variable + 1e-6:
            raise ValueError(
                "Raw materials and utilities must be included in variable OPEX, not additional costs"
            )
        total = capital_charge + fixed + variable
        if total <= 0:
            raise ValueError("Total annualized production cost must be positive")
        for key in ("fixed_opex_usd_per_year", "variable_opex_usd_per_year"):
            if (
                f.get(key) is None
                and breakdown.get("fixed" if key.startswith("fixed") else "variable")
                is None
            ):
                self.warnings.append(
                    f"{key} not supplied; profile uses the supplied component totals or zero, not a verified full OPEX estimate"
                )
        components = []

        def add(key, label, cost, parameter, parent=None):
            if cost > 0:
                components.append(
                    CostComponent(
                        id=key,
                        label=label,
                        annual_cost=cost,
                        share_pct=100 * cost / total,
                        parameter=parameter,
                        parent=parent,
                    )
                )

        # Leaves sum to 100%. Aggregate categories are reported separately.
        named_capital = fsum(cost for _, cost in item_costs)
        if named_capital > capex + 1e-6:
            raise ValueError("BOM line totals exceed supplied total CAPEX")
        for i, (name, cost) in enumerate(item_costs):
            add(
                f"capex-{i}",
                f"{name} annual capital charge",
                cost * crf,
                "capex",
                "capex",
            )
        add(
            "capex-remainder",
            "Other annual capital charge",
            (capex - named_capital) * crf,
            "capex",
            "capex",
        )
        add("fixed", "Fixed operating costs", fixed, "fixed_opex")
        for group, named, aggregate, parameter in (
            ("raw_materials", raw_items, raw, "feedstock"),
            ("utilities", utility_items, utilities, "utility"),
        ):
            for i, entry in enumerate(named):
                add(f"{group}-{i}", entry.name, entry.annual_cost, parameter, group)
            add(
                f"{group}-other",
                "Raw materials"
                if group == "raw_materials"
                else "Utilities (unspecified split)",
                aggregate - fsum(x.annual_cost for x in named),
                parameter,
                group,
            )
        add(
            "other-variable",
            "Other variable operating costs",
            max(0, variable - raw - utilities),
            "other_opex",
        )
        shares = {
            "capex": 100 * capital_charge / total,
            "fixed_opex": 100 * fixed / total,
            "variable_opex": 100 * variable / total,
            "raw_materials": 100 * raw / total,
            "utilities": 100 * utilities / total,
        }
        if not utility_items and utilities:
            self.warnings.append(
                "Utility expense is aggregated; electricity, steam and water exposure cannot be inferred without a utility breakdown"
            )
        text = " ".join(
            [self.context.name, self.context.description]
            + [name for name, _ in item_costs]
        ).lower()
        classification, basis = self.context.classification, "declared by user"
        matched = [rule for rule in self.rules if any(k in text for k in rule.keywords)]
        if classification == "auto":
            classification = matched[0].classification if matched else "general"
            basis = (
                "inferred from project/BOM keywords; confirm with engineering context"
                if matched
                else "insufficient sector evidence; general process economics"
            )
        themes = next(
            (r.themes for r in self.rules if r.classification == classification),
            [
                "Equipment procurement and supply-chain inflation",
                "Raw-material and utility contracts",
                "Product demand and offtake pricing",
            ],
        )
        if len(matched) > 1 and self.context.classification == "auto":
            self.warnings.append(
                "Multiple process classes match; classification is provisional"
            )
        top = sorted(components, key=lambda x: x.annual_cost, reverse=True)[:3]
        recommendations = []
        candidates = list(top)
        # Threshold rules complement the top three and never double count the profile.
        candidates += [
            c
            for c in components
            if (
                c.parameter == "utility"
                and any(word in c.label.lower() for word in ("power", "electric"))
                and c.share_pct > 30
            )
            or (c.parameter == "feedstock" and c.share_pct > 25)
        ]
        seen = set()
        for driver in candidates:
            parameter = driver.parameter
            if parameter in seen:
                continue
            seen.add(parameter)
            effective_share = shares.get(
                {
                    "capex": "capex",
                    "utility": "utilities",
                    "feedstock": "raw_materials",
                    "fixed_opex": "fixed_opex",
                }.get(parameter, ""),
                driver.share_pct,
            )
            swing = (
                40
                if parameter == "utility" and effective_share > 30
                else 30
                if effective_share >= 25
                else 20
            )
            recommendation = Recommendation(
                id=f"stress-{parameter}",
                title="Stress-test total capital cost"
                if parameter == "capex"
                else f"Stress-test {driver.label}",
                parameter=parameter,
                direction="increase",
                suggested_change_pct=swing,
                rationale=f"{driver.label}: {driver.share_pct:.1f}% of annualized production cost. This action applies +{swing}% to the whole {parameter} category; its total cost share is {effective_share:.1f}%.",
                driver_share_pct=effective_share,
                priority="high" if effective_share >= 25 else "medium",
                scope="all raw materials"
                if parameter == "feedstock"
                else "all utilities"
                if parameter == "utility"
                else "aggregate cost category",
            )
            self._impact(recommendation, capex, fixed, variable, raw, utilities)
            recommendations.append(recommendation)
        # Revenue downside matters even when it is not a production-cost component.
        price_rec = Recommendation(
            id="stress-selling-price",
            title="Test product-price downside",
            parameter="selling_price",
            direction="decrease",
            suggested_change_pct=-20,
            rationale="Cost share alone does not measure revenue exposure. Test a 20% selling-price reduction at fixed output; this is a scenario, not a price forecast.",
            driver_share_pct=0,
            priority="medium",
        )
        self._impact(price_rec, capex, fixed, variable, raw, utilities)
        if price_rec.npv_base_usd is not None:
            recommendations.append(price_rec)
        if number(f.get("capacity_factor"), "capacity factor", 1) > 1:
            raise ValueError("Capacity factor must not exceed one")
        production = number(
            f.get("plant_capacity_units_per_year"), "plant capacity", 0
        ) * number(f.get("capacity_factor"), "capacity factor", 1)
        streams = p.get("streams", [])
        if isinstance(streams, dict):
            streams = streams.get("streams", [])
        if (
            not isinstance(streams, list)
            or len(streams) > 10000
            or any(not isinstance(x, dict) for x in streams)
        ):
            raise ValueError("Streams must be a list of at most 10000 objects")
        phases = {}
        for stream in streams:
            phase = str(stream.get("phase", "unspecified"))[:40]
            phases[phase] = phases.get(phase, 0) + 1
        stream_summary = {
            "count": len(streams),
            "phase_counts": phases,
            "basis": "Stream observations only; no energy duties, chemistry, yields or cost inferred from flow rates",
        }
        return AdvisorResult(
            incentive_scenario=f.get("incentive", {"enabled": False}),
            stream_summary=stream_summary,
            project_description=self.context.description,
            equipment_summary=[
                {
                    "unit_id": str(item.get("unit_id", item.get("name", "Unknown")))[
                        :120
                    ],
                    "category": str(item.get("kind", item.get("type", "unspecified")))[
                        :80
                    ],
                    "quantity": number(item.get("quantity", 1), "quantity"),
                }
                for item in items
            ],
            financial_basis={
                "total_capex_usd": capex,
                "operating_years": years,
                "discount_rate": rate,
                "fixed_opex_usd_per_year": fixed,
                "variable_opex_usd_per_year": variable,
                **{
                    key: number(f[key], key)
                    for key in (
                        "plant_capacity_units_per_year",
                        "capacity_factor",
                        "product_selling_price_usd_per_unit",
                        "tax_rate",
                    )
                    if f.get(key) is not None
                },
            },
            project_name=self.context.name,
            classification=classification,
            classification_basis=basis,
            region=self.context.region,
            annualized_capital_cost=capital_charge,
            total_annualized_cost=total,
            lcop=total / production if production > 0 else None,
            cost_components=components,
            category_shares_pct=shares,
            top_drivers=top,
            recommendations=recommendations,
            research_themes=themes,
            warnings=self.warnings,
            assumptions=[
                "Cost leaves sum to 100%; raw materials and utilities are subsets of variable OPEX",
                "Economic amounts are USD; capacity factor defaults to one when absent; no FX conversion is inferred",
                "CAPEX annualized using the capital recovery factor; LCOP uses the same pre-tax cost basis as the financial engine",
                "Missing region or sector is not inferred from stream temperature or product names alone",
                "Suggested 20-50% swings are screening stress scenarios, not calibrated probability bounds",
                "Named expense recommendations apply the category-wide slider; individual commodity targeting requires a detailed operating model",
            ],
        )

    def _impact(self, rec, capex, fixed, variable, raw, utilities):
        try:
            baseline = FinancialInputs.model_validate(
                {
                    **{
                        k: v
                        for k, v in self.financial.items()
                        if k in FinancialInputs.model_fields
                    },
                    "total_capex_usd": capex,
                    "fixed_opex_usd_per_year": fixed,
                    "variable_opex_usd_per_year": variable,
                    "feedstock_opex_usd_per_year": raw,
                    "utility_opex_usd_per_year": utilities,
                }
            )
        except ValueError:
            return
        values = baseline.model_dump()
        factor = 1 + rec.suggested_change_pct / 100
        parameter = rec.parameter
        if parameter == "capex":
            values["total_capex_usd"] *= factor
        elif parameter == "fixed_opex":
            values["fixed_opex_usd_per_year"] *= factor
        elif parameter == "selling_price":
            values["product_selling_price_usd_per_unit"] *= factor
        else:
            amount = (
                raw
                if parameter == "feedstock"
                else utilities
                if parameter == "utility"
                else max(0, variable - raw - utilities)
            )
            values["variable_opex_usd_per_year"] += amount * (factor - 1)
            if parameter == "feedstock":
                values["feedstock_opex_usd_per_year"] *= factor
            if parameter == "utility":
                values["utility_opex_usd_per_year"] *= factor
        try:
            rec.npv_base_usd = calculate_dcf(baseline).npv_usd
            rec.npv_stressed_usd = calculate_dcf(
                FinancialInputs.model_validate(values)
            ).npv_usd
            rec.npv_change_usd = rec.npv_stressed_usd - rec.npv_base_usd
        except ValueError:
            return
