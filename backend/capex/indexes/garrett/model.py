"""Independently implemented Garrett Chapter 3 numerical parameters.

Only parameters necessary for calculation are stored; no textbook table layout,
scanned graphics or substantial prose is redistributed here.
"""

from ...models import Factor, Model, Source

SOURCE = Source(
    "Donald E. Garrett, Chemical Engineering Economics (1989), Ch.3 Table 3-4",
    "Chemical Engineering Economics for me.pdf",
    "fe1084a476baece3a8afd4711311780b314b08ca085dbcb766f193903bfe3eff",
    29,
    41,
)
MODEL = Model(
    "garrett",
    "Garrett detailed factorial",
    ("solids", "mixed", "fluids"),
    False,
    SOURCE,
    "detailed",
    (
        "Installation is embedded in the whole-plant direct factors, not a separate equipment installation addition (pp.29–30).",
        "Source ranges are not separate solid/mixed/fluid factor profiles; classification informs review only.",
        "Offsite and startup fractions use core plant cost before additional requirements; no self-referential total.",
    ),
)
DIRECT = {
    "piping": (".15", ".70"),
    "electrical": (".10", ".15"),
    "instrumentation_controls": (".10", ".35"),
    "utilities_services": (".30", ".75"),
    "foundations": (".07", ".12"),
    "insulation": (".02", ".08"),
    "painting_fire_safety": (".02", ".10"),
    "yard_improvements": (".05", ".15"),
    "environmental_controls": (".10", ".30"),
    "buildings": (".05", "1.00"),
    "land": ("0", ".10"),
}
INDIRECT = {
    "construction_engineering": ((".30", ".75"), (".10", ".40")),
    "contractor_fee": ((".10", ".45"), (".03", ".10")),
    "contingency": ((".15", ".80"), (".05", ".20")),
}

APPLICABILITY = {
    "piping": "Lower allowances suit solids conveying; fluids with recycling and heat exchange tend toward the upper range (p.30).",
    "electrical": "Plant wiring, switching, distribution and hookups; distinguish upstream utility supply facilities (p.30).",
    "instrumentation_controls": "Automation and control complexity influence allowance; includes installed controls rather than equipment purchase alone (p.30).",
    "utilities_services": "Utility generation/supply and water-system scope varies; separate shared offsite facilities to avoid overlap (p.33).",
    "foundations": "Equipment support and local ground/structural requirements; source percentage is a preliminary allowance.",
    "insulation": "Thermal duty, process temperature and conservation requirements determine scope (p.30).",
    "painting_fire_safety": "Protective finishes, fire protection and safety provisions appropriate to project hazards (p.32).",
    "yard_improvements": "Site grading, access, drainage and related works; reconcile items also classified as offsite (p.32).",
    "environmental_controls": "Applicable treatment, monitoring and permitting scope; requirements depend on location and process (p.32).",
    "buildings": "Housing, storage, laboratory and support-building needs; climate and containment strongly affect allowance (p.32).",
}
# Source comparison checks, not extra charges or mandatory clamping bounds.
COMPARISON_CHECKS = {
    "direct_multiplier_range": ("1.96", "4.80"),
    "purchase_basis_plant_range": ("2.51", "6.80"),
    "subtotal_basis_plant_range_rounded": ("2.31", "8.16"),
    "usual_solids_mixed_fluids": {"solids": "3.00", "mixed": "4.00", "fluids": "5.50"},
    "lang_reference_only": {"solids": "3.4", "mixed": None, "fluids": "5.2"},
}


def factors(process_type, inputs=None):
    rows = [
        Factor(
            "equipment_installation",
            None,
            None,
            "embedded_in_direct_factors",
            "direct",
            "not additive; installation included in other direct cost categories",
            "Whole-plant estimate only; equipment-specific installation is not added again.",
            SOURCE,
            alternatives=(
                {
                    "reference_average": ".63",
                    "base": "purchased_equipment",
                    "source_page": 30,
                    "condition": "Reference average across equipment charts; not an additive whole-plant factor",
                },
            ),
            additive=False,
        )
    ]
    for name, (low, high) in DIRECT.items():
        conditions = (
            "Select within source range for the actual process and project scope."
        )
        conditions = APPLICABILITY.get(name, conditions)
        alternatives = ()
        if name == "land":
            conditions = "Land is conditional on purchase; zero is permitted by Table 3-4. Prose p.33 gives 3–10% when purchased."
            alternatives = (
                {
                    "minimum": ".03",
                    "maximum": ".10",
                    "base": "purchased_equipment",
                    "condition": "land purchase required",
                    "source_page": 33,
                },
            )
        rows.append(
            Factor(
                name,
                low,
                high,
                "purchased_equipment",
                "direct",
                "fraction * purchased_equipment",
                conditions,
                SOURCE,
                alternatives,
            )
        )
    for name, (purchase, direct) in INDIRECT.items():
        base = inputs.indirect_basis if inputs else "purchased_equipment"
        low, high = direct if base == "direct_costs" else purchase
        alt = (
            {
                "minimum": direct[0],
                "maximum": direct[1],
                "base": "direct_costs",
                "formula": "fraction * direct_costs",
            },
        )
        rows.append(
            Factor(
                name,
                low,
                high,
                base,
                "indirect",
                "fraction * " + base,
                "Choose one complete indirect basis; optional subtotal column is not an extra charge.",
                SOURCE,
                alt,
            )
        )
    rows.extend(
        [
            Factor(
                "offsite_facilities",
                "0",
                ".30",
                "plant_cost",
                "offsite",
                "fraction * plant_cost",
                "Only facilities not already in the battery-limits estimate. Require explicit non-overlap scope confirmation.",
                SOURCE,
            ),
            Factor(
                "startup_expenses",
                ".05",
                ".10",
                "plant_cost",
                "startup",
                "fraction * plant_cost",
                "Additional capitalized startup expense, separate from fixed plant hardware.",
                SOURCE,
            ),
            Factor(
                "working_capital",
                ".10",
                ".20",
                "plant_cost",
                "working_capital",
                "fraction * plant_cost",
                "Alternative: 10–35% of annual manufacturing/operating cost (p.41).",
                SOURCE,
                (
                    {
                        "minimum": ".10",
                        "maximum": ".35",
                        "base": "annual_opex",
                        "formula": "fraction * annual_opex",
                        "source_page": 41,
                    },
                    {
                        "minimum": ".50",
                        "maximum": ".50",
                        "base": "installed_equipment",
                        "formula": "fraction * installed_equipment",
                        "source_page": 41,
                        "condition": "Rough alternative requiring a separately supplied installed-equipment total",
                    },
                ),
            ),
        ]
    )
    return tuple(rows)
