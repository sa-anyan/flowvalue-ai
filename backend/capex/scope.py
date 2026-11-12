"""Capital-scope rules (B08 decision C) and the source inclusion matrix.

Three scopes are recognised:

- ``purchased_equipment``: equipment purchase price only. Plant (Lang or
  factorial) factors apply to this scope and to nothing else.
- ``installed_equipment``: equipment plus installation as its source defines
  it. OpenPyTEA bare-module (``module_estimate``) lines belong to this family.
  It receives only indirect, contingency and owner's-cost factors that its
  source is recorded as *excluding*.
- ``unit_capital``: a source-defined package price. It receives no
  installation-type factor; only contingency and owner's costs, again only
  where its source is recorded as excluding them.

An inclusion record states, per source, which breakdown categories the price
already includes and which it excludes. A category in neither list is
*unknown*: no factor is applied and the gap is reported, so nothing is counted
twice and nothing is silently assumed to be included.

This module holds no factor values; factors stay in the registered CAPEX
methods (Garrett, Nottingham detailed, Nottingham Lang).
"""

SCOPES = ("purchased_equipment", "installed_equipment", "unit_capital")

# Source-native scope labels and the decision-C family they belong to.
SCOPE_FAMILY = {
    "purchased_equipment": "purchased_equipment",
    "installed_equipment": "installed_equipment",
    "module_estimate": "installed_equipment",
    "unit_capital": "unit_capital",
}

# Complete capital breakdown (M3.3), in report order.
CATEGORIES = (
    "purchased_equipment",
    "installation",
    "piping",
    "instrumentation_control",
    "electrical",
    "civil_structural",
    "buildings",
    "yard_utilities_offsites",
    "environmental_controls",
    "land",
    "engineering_supervision",
    "construction_overheads",
    "contractor_fee",
    "contingency",
    "owners_costs",
    "startup_commissioning",
    "working_capital",
)

CATEGORY_LABELS = {
    "purchased_equipment": "Purchased equipment",
    "installation": "Installation (incl. insulation, painting)",
    "piping": "Piping",
    "instrumentation_control": "Instrumentation and control",
    "electrical": "Electrical",
    "civil_structural": "Civil / structural",
    "buildings": "Buildings",
    "yard_utilities_offsites": "Yard, utilities and offsites",
    "environmental_controls": "Environmental controls",
    "land": "Land",
    "engineering_supervision": "Engineering and supervision",
    "construction_overheads": "Construction overheads",
    "contractor_fee": "Contractor's fee",
    "contingency": "Contingency",
    "owners_costs": "Owner's costs",
    "startup_commissioning": "Start-up and commissioning",
    "working_capital": "Working capital",
}

# Registered factor id -> breakdown categories it covers. The first category
# receives the amount; later ones are reported as combined into it.
FACTOR_CATEGORIES = {
    "equipment_installation": ("installation",),
    "insulation": ("installation",),
    "painting_fire_safety": ("installation",),
    "piping": ("piping",),
    "instrumentation_controls": ("instrumentation_control",),
    "electrical": ("electrical",),
    "foundations": ("civil_structural",),
    "buildings": ("buildings",),
    "yard_improvements": ("yard_utilities_offsites",),
    "utilities_services": ("yard_utilities_offsites",),
    "offsite_facilities": ("yard_utilities_offsites",),
    "environmental_controls": ("environmental_controls",),
    "land": ("land",),
    # Garrett publishes one combined construction/engineering allowance.
    "construction_engineering": ("engineering_supervision", "construction_overheads"),
    "engineering_supervision": ("engineering_supervision",),
    "construction_expenses": ("construction_overheads",),
    "contractor_fee": ("contractor_fee",),
    "contingency": ("contingency",),
    "startup_expenses": ("startup_commissioning",),
    "working_capital": ("working_capital",),
    # Lang is one overall installed-plant factor on purchased equipment.
    "lang_factor": (
        "installation",
        "piping",
        "instrumentation_control",
        "electrical",
        "civil_structural",
        "buildings",
        "yard_utilities_offsites",
        "engineering_supervision",
        "construction_overheads",
        "contractor_fee",
        "contingency",
    ),
}

# Categories each non-purchased scope may receive, if its source excludes them.
ELIGIBLE = {
    "purchased_equipment": frozenset(CATEGORIES),
    "installed_equipment": frozenset(
        {
            "engineering_supervision",
            "construction_overheads",
            "contractor_fee",
            "contingency",
            "owners_costs",
        }
    ),
    "unit_capital": frozenset({"contingency", "owners_costs"}),
}

# Vocabulary used by source evidence -> breakdown category.
_ALIASES = {
    "equipment": "purchased_equipment",
    "purchased_equipment": "purchased_equipment",
    "installation": "installation",
    "equipment_installation": "installation",
    "insulation": "installation",
    "painting": "installation",
    "piping": "piping",
    "instrumentation": "instrumentation_control",
    "instrumentation_controls": "instrumentation_control",
    "instrumentation_control": "instrumentation_control",
    "electrical": "electrical",
    "civil": "civil_structural",
    "structural": "civil_structural",
    "foundations": "civil_structural",
    "civil_structural": "civil_structural",
    "buildings": "buildings",
    "yard_improvements": "yard_utilities_offsites",
    "utilities": "yard_utilities_offsites",
    "utilities_services": "yard_utilities_offsites",
    "offsites": "yard_utilities_offsites",
    "offsite_facilities": "yard_utilities_offsites",
    "yard_utilities_offsites": "yard_utilities_offsites",
    "environmental_controls": "environmental_controls",
    "land": "land",
    "engineering": "engineering_supervision",
    "engineering_supervision": "engineering_supervision",
    "construction": "construction_overheads",
    "construction_expenses": "construction_overheads",
    "construction_overheads": "construction_overheads",
    "contractor_fee": "contractor_fee",
    "fee": "contractor_fee",
    "contingency": "contingency",
    "owners_costs": "owners_costs",
    "owner_costs": "owners_costs",
    "startup": "startup_commissioning",
    "startup_expenses": "startup_commissioning",
    "startup_commissioning": "startup_commissioning",
    "working_capital": "working_capital",
}

_PURCHASE_ONLY = {
    "included": ("purchased_equipment",),
    "excluded": tuple(c for c in CATEGORIES if c != "purchased_equipment"),
}

# Source-level inclusion records. Line-level evidence is merged on top.
INCLUSION_MATRIX = {
    ("garrett", "purchased_equipment"): dict(
        _PURCHASE_ONLY,
        basis="Garrett Ch.3 equipment chart price; the chart's equipment-specific installation factor is reported separately and never enters CAPEX.",
    ),
    ("nottingham", "purchased_equipment"): dict(
        _PURCHASE_ONLY,
        basis="Nottingham CEEDG501 equipment correlation, delivered purchase cost.",
    ),
    ("openpytea", "purchased_equipment"): dict(
        _PURCHASE_ONLY,
        basis="OpenPyTEA purchased-cost correlation; its Towler & Sinnott installation estimate is reported separately and never enters CAPEX.",
    ),
    ("additional_models", "purchased_equipment"): dict(
        _PURCHASE_ONLY, basis="Additional-model purchased-cost correlation."
    ),
    ("manual", "purchased_equipment"): dict(
        _PURCHASE_ONLY, basis="User-approved purchased-equipment price."
    ),
    ("quote", "purchased_equipment"): dict(
        _PURCHASE_ONLY, basis="Vendor quote declared as purchased equipment."
    ),
    ("openpytea", "installed_equipment"): dict(
        included=("purchased_equipment", "installation"),
        excluded=(),
        basis="OpenPyTEA row remark says 'installed'. The dataset does not itemise which indirects are included, so indirects, contingency and owner's costs are unknown and are reported as gaps rather than applied.",
    ),
    ("openpytea", "module_estimate"): dict(
        included=(
            "purchased_equipment",
            "installation",
            "piping",
            "instrumentation_control",
            "electrical",
            "civil_structural",
            "engineering_supervision",
            "construction_overheads",
        ),
        excluded=(
            "buildings",
            "yard_utilities_offsites",
            "contractor_fee",
            "contingency",
            "owners_costs",
        ),
        basis="Bare-module cost convention (Guthrie; Turton et al., Ch.7): equipment plus direct installation materials and labour and the indirect freight, overhead and engineering expenses. Contingency, fee and auxiliary facilities are outside it. Source page not yet re-verified in this repository: provisional.",
    ),
    ("garrett", "installed_equipment"): dict(
        included=("purchased_equipment", "installation"),
        excluded=(),
        basis="Garrett installed unit price (per ft / ft²); no component split. Other inclusions unknown.",
    ),
}


def normalise(categories):
    """Return (known categories, unrecognised terms)."""
    known, unknown = set(), []
    for item in categories or ():
        key = str(item).strip().casefold().replace("'", "").replace(" ", "_")
        if key in _ALIASES:
            known.add(_ALIASES[key])
        else:
            unknown.append(str(item))
    return known, unknown


def source_of(provenance):
    provenance = provenance or {}
    evidence = provenance.get("costing_evidence") or {}
    return provenance.get("source") or evidence.get("source") or "unrecorded"


def inclusion_record(tag, scope, provenance, included_categories=(), excluded=()):
    """Merge the source-level matrix entry with line-level declarations."""
    source = source_of(provenance)
    native = scope
    family = SCOPE_FAMILY.get(scope)
    entry = INCLUSION_MATRIX.get((source, native))
    evidence = (provenance or {}).get("costing_evidence") or {}
    line_included, unknown_in = normalise(
        tuple(included_categories) + tuple(evidence.get("included_categories", ()))
    )
    line_excluded, unknown_out = normalise(
        tuple(excluded) + tuple((provenance or {}).get("excluded_categories", ()))
    )
    included = set(entry["included"]) if entry else set()
    declared_excluded = set(entry["excluded"]) if entry else set()
    included |= line_included
    if family in ("installed_equipment", "unit_capital"):
        # By definition these prices include their own installation.
        included |= {"purchased_equipment", "installation"}
    declared_excluded = (declared_excluded | line_excluded) - included
    return {
        "tag": tag,
        "source": source,
        "native_scope": native,
        "scope": family,
        "included": tuple(c for c in CATEGORIES if c in included),
        "excluded": tuple(c for c in CATEGORIES if c in declared_excluded),
        "unknown": tuple(
            c for c in CATEGORIES if c not in included and c not in declared_excluded
        ),
        "unrecognised_terms": tuple(unknown_in + unknown_out),
        "matrix_entry": bool(entry),
        "basis": entry["basis"]
        if entry
        else "No source-level inclusion record; only line-declared inclusions are known.",
    }


def eligibility(record, factor_id):
    """Decide whether a factor applies to a pre-costed record.

    Returns (applies, status, reason). Status is one of ``applies``,
    ``not_eligible`` (scope rule), ``already_included`` or ``unknown``.
    """
    categories = FACTOR_CATEGORIES.get(factor_id, ())
    family = record["scope"]
    if not categories:
        return False, "not_eligible", "factor has no breakdown category"
    if not set(categories) <= ELIGIBLE[family]:
        return (
            False,
            "not_eligible",
            "plant/installation-type factors apply only to purchased equipment",
        )
    included = set(categories) & set(record["included"])
    if included:
        return (
            False,
            "already_included",
            "source already includes " + ", ".join(sorted(included)),
        )
    if not set(categories) <= set(record["excluded"]):
        return (
            False,
            "unknown",
            "source inclusion of "
            + ", ".join(c for c in categories if c not in record["excluded"])
            + " is not recorded; not applied and reported as a gap",
        )
    return True, "applies", "source excludes " + ", ".join(categories)
