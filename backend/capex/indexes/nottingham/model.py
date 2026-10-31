"""CEEDG501 p.5 numerical profiles; detailed and Lang methods stay separate."""

from ...models import Factor, Model, Source

SOURCE = Source(
    "University of Nottingham CEE Design Consultants, CEEDG501 Cost Estimation Rev 3, section 3.2",
    "CEEDG501 Cost Estimation Rev 3 (1).pdf",
    "9b626ffe656fdde1c857a978393380f971070dcfaca500927626e7c962584b57",
    5,
    5,
    "Revision history says Rev 3 (7 Nov 2017); body footer still says Revision 2 / September 2017. Both retained.",
)
MODEL = Model(
    "nottingham",
    "Nottingham detailed factorial",
    ("solids", "mixed", "fluids"),
    True,
    SOURCE,
    "detailed",
    (
        "Published table uses rounded percentages of delivered purchase cost; approximate subtotal relationships are separately selectable.",
        "No separate source factor for insulation/foundations/environmental/startup is invented; these require scope review, not an added Garrett percentage.",
    ),
)
LANG = Model(
    "nottingham_lang",
    "Nottingham Lang overall factor",
    ("solids", "mixed", "fluids", "bioprocessing", "water_treatment"),
    True,
    SOURCE,
    "lang",
    (
        "Alternative overall installed-plant estimate; never add the detailed factorial charges on top.",
    ),
)
# Fractions of delivered purchased equipment. Three independent profiles.
PROFILES = {
    "solids": (
        "0.45",
        "0.09",
        "0.16",
        "0.10",
        "0.25",
        "0.13",
        "0.40",
        "0.06",
        "0.33",
        "0.39",
        "0.17",
        "0.34",
        "0.68",
    ),
    "mixed": (
        "0.39",
        "0.13",
        "0.31",
        "0.10",
        "0.29",
        "0.10",
        "0.55",
        "0.06",
        "0.32",
        "0.34",
        "0.18",
        "0.36",
        "0.74",
    ),
    "fluids": (
        "0.47",
        "0.18",
        "0.66",
        "0.11",
        "0.18",
        "0.10",
        "0.70",
        "0.06",
        "0.33",
        "0.41",
        "0.21",
        "0.42",
        "0.86",
    ),
}
NAMES = (
    "equipment_installation",
    "instrumentation_controls",
    "piping",
    "electrical",
    "buildings",
    "yard_improvements",
    "utilities_services",
    "land",
    "engineering_supervision",
    "construction_expenses",
    "contractor_fee",
    "contingency",
    "working_capital",
)
LANG_FACTORS = {
    "solids": "3.1",
    "mixed": "3.6",
    "fluids": "4.7",
    "bioprocessing": "7.8",
    "water_treatment": "3.5",
}


def factors(process_type, inputs=None):
    rows = []
    for i, (name, value) in enumerate(zip(NAMES, PROFILES[process_type], strict=True)):
        stage = (
            "direct"
            if i < 8
            else ("indirect" if i < 10 else ("fees" if i < 12 else "working_capital"))
        )
        base = "purchased_equipment"
        alternative = ()
        if name in ["contractor_fee", "contingency"]:
            nominal = ".05" if name == "contractor_fee" else ".10"
            alternative = (
                {
                    "minimum": nominal,
                    "maximum": nominal,
                    "base": "direct_and_indirect",
                    "formula": "fraction * direct_and_indirect",
                    "condition": "about-value relationship, not the rounded printed percentage",
                },
            )
            if inputs and inputs.factor_basis_mode == "relationships":
                value, base = nominal, "direct_and_indirect"
        if name == "working_capital":
            alternative = (
                {
                    "minimum": ".15",
                    "maximum": ".15",
                    "base": "total_investment",
                    "formula": "fixed_capital * fraction / (1 - fraction)",
                    "condition": "about 15% of total capital investment; printed column rounded",
                },
            )
        rows.append(
            Factor(
                name,
                value,
                value,
                base,
                stage,
                "fraction * " + base,
                "Published "
                + process_type
                + " profile; exact table number is rounded. Land only if required."
                if name == "land"
                else "Published "
                + process_type
                + " profile; do not infer a min/max range from the three categories.",
                SOURCE,
                alternative,
            )
        )
    for name in (
        "foundations",
        "insulation",
        "environmental_controls",
        "painting_fire_safety",
        "offsite_facilities",
        "startup_expenses",
    ):
        rows.append(
            Factor(
                name,
                None,
                None,
                "not_separately_published",
                "information",
                "no standalone factor in this profile; review scope before adding costs",
                "Not separately itemized on page 5; no Garrett percentage substituted and no zero actual cost asserted.",
                SOURCE,
                additive=False,
            )
        )
    return tuple(rows)


def lang_factors(process_type, inputs=None):
    v = LANG_FACTORS[process_type]
    return (
        Factor(
            "lang_factor",
            v,
            v,
            "purchased_equipment",
            "lang",
            "fraction * purchased_equipment",
            "Overall installed cost/purchase cost; no detailed factorial additions.",
            SOURCE,
        ),
    )
