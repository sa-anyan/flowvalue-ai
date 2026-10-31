"""Independently implemented numerical parameters, not a reproduced textbook table.

Ranges are preliminary historical guidance, not current prices or validated site costs.
Group totals are comparison checks only, never extra additive charges.
"""

from backend.capex.models import Source

from ...models import Category

SOURCE = Source(
    "Donald E. Garrett, Chemical Engineering Economics (1989), Ch.4 Table 4-4",
    "Chemical Engineering Economics for me.pdf",
    "fe1084a476baece3a8afd4711311780b314b08ca085dbcb766f193903bfe3eff",
    52,
    64,
    "Visually checked against PDF p.64. Capital base includes startup and offsite; excludes working capital.",
)

PLANT_BASE = "plant_including_startup_excluding_working_capital"


def category(key, low=None, high=None, base=None, applicability="", **options):
    return Category(key, low, high, base, applicability, SOURCE, **options)


CATEGORIES = (
    category(
        "raw_materials",
        applicability="Itemize annual feed, additives, catalyst makeup/regeneration and losses from engineering evidence. Initial catalyst is CAPEX; inventories are working capital (p.46).",
    ),
    category(
        "utilities",
        applicability="Itemize power, fuel, steam, water, air and other services from balances, operating hours and local tariffs (pp.47–48). No automatic historical tariff.",
    ),
    category(
        "operating_labor",
        applicability="Itemize operating staff only; exclude maintenance, supervisors, laboratory and support staff recovered elsewhere (pp.47–51).",
    ),
    category(
        "interest",
        applicability="Itemize interest on borrowing if applicable; declare no debt explicitly otherwise (p.60). Not unlevered cash OPEX.",
        accounting="financing",
    ),
    category(
        "payroll_overhead",
        ".22",
        ".45",
        "category:operating_labor",
        "Benefits and employer payroll charges; do not add to already loaded salaries (p.53).",
    ),
    category(
        "supervision",
        ".10",
        ".30",
        "category:operating_labor",
        "Supervision and support labor; avoid separate engineering/clerical labor already charged here (p.53).",
    ),
    category(
        "laboratory",
        ".10",
        ".20",
        "category:operating_labor",
        "Includes laboratory labor and supplies, not only consumables (p.57).",
    ),
    category(
        "maintenance",
        ".02",
        ".10",
        PLANT_BASE,
        "Includes maintenance materials, labor and services. Condition, corrosion, wear and automation affect allowance (pp.53–56).",
    ),
    category(
        "operating_supplies",
        ".005",
        ".03",
        PLANT_BASE,
        "Other unlisted plant supplies; exclude supplies already recovered in laboratory/maintenance (p.57).",
    ),
    category(
        "environmental",
        ".005",
        ".05",
        PLANT_BASE,
        "Environmental, safety and hazardous-waste functions; significant hazardous duties may require detailed estimates beyond historical range (pp.57–58).",
    ),
    category(
        "depreciation",
        ".05",
        ".10",
        PLANT_BASE,
        "Table allowance for preliminary estimates only, not a tax depreciation schedule; land is not depreciable. Straight-line asset estimate available separately (pp.58–59).",
        accounting="noncash",
    ),
    category(
        "taxes_insurance",
        ".03",
        ".05",
        PLANT_BASE,
        "Combined local taxes, permits/fees and insurance; income tax is excluded. Separate quotes must replace, not supplement, this combined allowance (pp.59–60).",
    ),
    category(
        "plant_overhead",
        ".01",
        ".05",
        PLANT_BASE,
        "Plant-level overhead only; reconcile corporate administration and support staff to avoid duplicates.",
    ),
    category(
        "royalties",
        "0",
        ".05",
        "annual_revenue",
        "Recurring patents/royalties if applicable; lump-sum licence acquisition is not recurring OPEX. Text p.57 gives narrower indicative .25–2% guidance.",
    ),
    category(
        "packaging_storage",
        "0",
        ".07",
        "annual_revenue",
        "Product packaging and storage. Detail costs when significant; bulk-shipping costs may be allocated elsewhere (p.57).",
    ),
    category(
        "administration",
        ".02",
        ".10",
        "annual_revenue",
        "Allocated corporate/general administration; reconcile plant overhead (pp.61–62).",
    ),
    category(
        "distribution_sales",
        ".02",
        ".10",
        "annual_revenue",
        "Outbound distribution, selling and marketing expenses; reconcile freight and packaging (pp.61–62).",
    ),
    category(
        "research_development",
        ".005",
        ".04",
        "annual_revenue",
        "Allocated ongoing R&D and technical service (pp.61–62).",
        note="Table 4-4 upper bound is 4%; prose p.62 says 5%. Table is default; a 5% proposal requires a documented override.",
    ),
    category(
        "other_manufacturing",
        applicability="Itemize project-specific costs omitted from allowances, with unique cost scopes (Table 4-1 p.45). Explicitly review applicability.",
        required=False,
    ),
)

# Non-additive published checks; never added to the individual rows.
# Printed sales maximum is 37%, whereas the individual maxima sum to 36%.
# Preserve both; calculate the individual rows without forcing reconciliation.
GROUP_CHECKS = (
    (
        "labor_related",
        ("payroll_overhead", "supervision", "laboratory"),
        ".42",
        ".95",
        ".60",
        "category:operating_labor",
    ),
    (
        "capital_related",
        (
            "maintenance",
            "operating_supplies",
            "environmental",
            "depreciation",
            "taxes_insurance",
            "plant_overhead",
        ),
        ".12",
        ".38",
        ".26",
        PLANT_BASE,
    ),
    (
        "sales_related",
        (
            "royalties",
            "packaging_storage",
            "administration",
            "distribution_sales",
            "research_development",
        ),
        ".045",
        ".37",
        ".20",
        "annual_revenue",
    ),
)

MODEL = {
    "id": "garrett",
    "title": "Garrett Chapter 4 manufacturing costs",
    "default": True,
    "activation": "offline_only",
    "source": SOURCE,
}
