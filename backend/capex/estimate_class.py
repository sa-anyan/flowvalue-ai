"""M3.5 AACE estimate class: a proposal for review, never a certification.

AACE International Recommended Practice 18R-97 (Rev. 7 August 2020), section 3,
Table 1, page 3 of 21: the maturity of the project-definition deliverables is
the *sole* determining characteristic of class. End usage, methodology and
accuracy are secondary characteristics.

What is quoted from 18R-97 here is limited to Table 1's class numbers,
maturity percentages, end usage, methodology and accuracy ranges, with the
citation. The deliverable checklist and the rules mapping it to a class are
FlowValue's own, written without 18R-97's Table 3. They are PROVISIONAL until
checked against the purchased document.

Costing evidence (coverage, minimum-size floors, extrapolation, CPI-proxy
escalation) never changes the class. It is reported as reasons the actual
accuracy may sit at the wide end of the class range, or beyond it.
"""

from dataclasses import dataclass

REFERENCE = (
    "AACE International Recommended Practice 18R-97, Cost Estimate "
    "Classification System - As Applied in Engineering, Procurement, and "
    "Construction for the Process Industries, Rev. 7 August 2020, section 3, "
    "Table 1, p. 3 of 21"
)

CHECKLIST_STATUS = (
    "provisional: FlowValue checklist, not AACE 18R-97 Table 3; "
    "check against the purchased recommended practice"
)

# Table 1 (process industries). Accuracy at an 80% confidence interval after
# appropriate contingency; each bound is a range of typical values.
CLASS_MATRIX = {
    5: {
        "maturity_percent": (0, 2),
        "end_usage": "Concept screening",
        "methodology": "Capacity factored, parametric models, judgment, or analogy",
        "accuracy_low_percent": (-20, -50),
        "accuracy_high_percent": (30, 100),
    },
    4: {
        "maturity_percent": (1, 15),
        "end_usage": "Study or feasibility",
        "methodology": "Equipment factored or parametric models",
        "accuracy_low_percent": (-15, -30),
        "accuracy_high_percent": (20, 50),
    },
    3: {
        "maturity_percent": (10, 40),
        "end_usage": "Budget authorization or control",
        "methodology": "Semi-detailed unit costs with assembly level line items",
        "accuracy_low_percent": (-10, -20),
        "accuracy_high_percent": (10, 30),
    },
    2: {
        "maturity_percent": (30, 75),
        "end_usage": "Control or bid/tender",
        "methodology": "Detailed unit cost with forced detailed take-off",
        "accuracy_low_percent": (-5, -15),
        "accuracy_high_percent": (5, 20),
    },
    1: {
        "maturity_percent": (65, 100),
        "end_usage": "Check estimate or bid/tender",
        "methodology": "Detailed unit cost with detailed take-off",
        "accuracy_low_percent": (-3, -10),
        "accuracy_high_percent": (3, 15),
    },
}

STATUSES = ("none", "preliminary", "complete")
_RANK = {s: i for i, s in enumerate(STATUSES)}


@dataclass(frozen=True)
class Deliverable:
    id: str
    label: str
    class_4: str  # minimum status for Class 4 ("none" = not needed)
    class_3: str  # minimum status for Class 3


# FlowValue's own checklist (provisional; see module docstring).
DELIVERABLES = (
    Deliverable("capacity_and_products", "Plant capacity, products and feed basis", "complete", "complete"),
    Deliverable("plant_location", "Plant location (general region / specific site)", "preliminary", "complete"),
    Deliverable("process_flow_diagram", "Block or process flow diagram", "preliminary", "complete"),
    Deliverable("heat_and_material_balance", "Heat and material balance", "preliminary", "complete"),
    Deliverable("equipment_list", "Sized major equipment list", "preliminary", "complete"),
    Deliverable("equipment_datasheets", "Equipment data sheets / specifications", "none", "preliminary"),
    Deliverable("utility_balance", "Utility balance", "none", "preliminary"),
    Deliverable("piping_and_instrument_diagrams", "Piping and instrument diagrams", "none", "preliminary"),
    Deliverable("plot_plan", "Plot plan and layout", "none", "preliminary"),
    Deliverable("major_equipment_quotes", "Vendor quotes for major equipment", "none", "preliminary"),
)
_BY_ID = {d.id: d for d in DELIVERABLES}

# Every CAPEX methodology registered in FlowValue is equipment factored.
FACTORED_METHODS = {"garrett", "nottingham", "nottingham_lang"}

COVERAGE_TARGET = 0.95  # G3: at least 95% of verified scope priced


def _status(value, field):
    if value not in _RANK:
        raise ValueError(f"design_maturity.{field} must be one of {', '.join(STATUSES)}")
    return value


def _maturity(declared, derived):
    """User declarations win; derived evidence fills gaps; otherwise 'none'."""
    unknown = set(declared) - set(_BY_ID)
    if unknown:
        raise ValueError("Unknown design_maturity deliverable: " + ", ".join(sorted(unknown)))
    rows = []
    for d in DELIVERABLES:
        if d.id in declared:
            status, basis = _status(declared[d.id], d.id), "user_declared"
        elif d.id in derived:
            status, basis = derived[d.id]
        else:
            status, basis = "none", "not_stated_treated_as_absent"
        rows.append({"id": d.id, "label": d.label, "status": status, "basis": basis})
    return rows


def _missing(rows, level):
    attr = "class_" + str(level)
    return [
        {"id": r["id"], "label": r["label"], "status": r["status"],
         "needed": getattr(_BY_ID[r["id"]], attr)}
        for r in rows
        if _RANK[r["status"]] < _RANK[getattr(_BY_ID[r["id"]], attr)]
    ]


def _line_evidence(lines, unpriced):
    priced = floored = extrapolated = proxy = user_priced = 0
    for line in lines:
        if line.get("amount") is None:
            continue
        priced += 1
        calc = line.get("calculation") or {}
        evidence = calc.get("evidence") or {}
        estimate = calc.get("estimate") or {}
        if evidence.get("below_range_floor"):  # key may be present with None
            floored += 1
        if estimate.get("extrapolated"):
            extrapolated += 1
        if (evidence.get("cost_translation") or {}).get("status") == "general_inflation_proxy":
            proxy += 1
        if evidence.get("method") == "reviewed_comparable" or str(line.get("curve_id") or "").startswith("manual:"):
            user_priced += 1
    total = priced + len(unpriced)
    return {
        "items": total,
        "priced": priced,
        "unpriced": len(unpriced),
        "priced_fraction": (priced / total) if total else None,
        "minimum_size_floor": floored,
        "extrapolated": extrapolated,
        "cpi_proxy_escalated": proxy,
        "user_or_quote_priced": user_priced,
    }


def propose_estimate_class(
    *,
    design_maturity=None,
    balance_approved=False,
    equipment_lines=(),
    unpriced=(),
    capex_method=None,
    new_technology=False,
    review=None,
):
    """Propose a class from deliverable maturity; report costing caveats.

    equipment_lines: plain dicts of EquipmentCostLine. review: optional
    {"class": int, "reviewer": str, "rationale": str} from a person.
    """
    declared = dict(design_maturity or {})
    lines = [l for l in equipment_lines if isinstance(l, dict)]
    costing = _line_evidence(lines, list(unpriced))

    derived = {}
    if balance_approved:
        derived["heat_and_material_balance"] = ("preliminary", "derived: engineering data approved in FlowValue")
    if costing["items"]:
        derived["equipment_list"] = ("preliminary", "derived: equipment register with sizes in FlowValue")
    if costing["user_or_quote_priced"]:
        derived["major_equipment_quotes"] = ("preliminary", "derived: user-supplied prices or comparables on some lines")

    rows = _maturity(declared, derived)
    gaps_4, gaps_3 = _missing(rows, 4), _missing(rows, 3)
    proposed = 3 if not gaps_3 else 4 if not gaps_4 else 5
    next_class = {5: 4, 4: 3}.get(proposed)

    if proposed == 5:
        reasons = ["Deliverables do not yet meet the Class 4 checklist"]
    else:
        reasons = [f"Deliverable maturity meets FlowValue's Class {proposed} checklist"]
    reasons.append(
        "Classes 2 and 1 need detailed take-offs, which FlowValue does not produce; "
        "they are never proposed automatically"
    )

    issues = []
    wide_end = []
    if costing["priced_fraction"] is not None and costing["priced_fraction"] < COVERAGE_TARGET:
        wide_end.append(
            f"{costing['unpriced']} of {costing['items']} equipment items unpriced "
            f"({costing['priced_fraction']:.0%} priced; G3 target {COVERAGE_TARGET:.0%})"
        )
    if costing["minimum_size_floor"]:
        wide_end.append(f"{costing['minimum_size_floor']} items priced at a correlation's minimum size (overstates small items)")
    if costing["extrapolated"]:
        wide_end.append(f"{costing['extrapolated']} items extrapolated beyond a correlation's range")
    if costing["cpi_proxy_escalated"]:
        wide_end.append(f"{costing['cpi_proxy_escalated']} items escalated with the CPI proxy, not an equipment cost index")
    if new_technology:
        wide_end.append("New or first-of-a-kind technology: AACE notes high ranges may be two to three times Table 1")
    if capex_method in FACTORED_METHODS and proposed <= 3:
        issues.append(
            "Deliverables support Class 3, but this CAPEX method is equipment factored, "
            "the typical methodology of Class 4. A reviewer should decide whether the "
            "estimate itself, not only the design, supports Class 3."
        )

    status, confirmed = "proposed", None
    if review:
        chosen = review.get("class")
        if chosen not in CLASS_MATRIX:
            raise ValueError("estimate_class_review.class must be 1-5")
        if not str(review.get("reviewer") or "").strip():
            raise ValueError("estimate_class_review.reviewer is required")
        if chosen != proposed and not str(review.get("rationale") or "").strip():
            raise ValueError("A reviewer class different from the proposal needs a rationale")
        status = "confirmed" if chosen == proposed else "reviewer_override"
        confirmed = {"class": chosen, "reviewer": review["reviewer"], "rationale": review.get("rationale", "")}

    effective = confirmed["class"] if confirmed else proposed
    return {
        "status": status,
        "proposed_class": proposed,
        "effective_class": effective,
        "review": confirmed,
        "requires_review": status == "proposed",
        "class_characteristics": {**CLASS_MATRIX[effective], "class": effective},
        "deliverables": rows,
        "gaps_to_next_class": (_missing(rows, next_class) if next_class else []),
        "next_class": next_class,
        "reasons": reasons,
        "wide_end_reasons": wide_end,
        "issues": issues,
        "costing_evidence": costing,
        "capex_method": capex_method,
        "reference": REFERENCE,
        "checklist_status": CHECKLIST_STATUS,
        "notice": (
            "Proposal for review, not a certification. AACE ranges are typical ranges "
            "at an 80% confidence interval after appropriate contingency; actual "
            "outcomes can fall outside them."
        ),
    }
