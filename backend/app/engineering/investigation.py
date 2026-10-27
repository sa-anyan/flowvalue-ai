"""Deterministic questions and preliminary sizing; no fabricated suitability claims."""

import hashlib
import json
from datetime import date

from pydantic import TypeAdapter, ValidationError

from app.engine.costing import Equipment, cost_equipment
from app.engineering.models import EngineeringCase

RULE_VERSION = "engineering-investigation-2026-10-27.1"
SOURCES = [
    {
        "id": "materials",
        "title": "Outokumpu — corrosion data and materials selection limits",
        "url": "https://www.outokumpu.com/en/products/corrosion-tables",
        "reviewed_on": "2026-10-27",
        "scope": "General evidence requirements, not compatibility certification for this service.",
    },
    {
        "id": "food",
        "title": "21 CFR 117.40 — equipment and utensils (2025 edition)",
        "url": "https://www.govinfo.gov/content/pkg/CFR-2025-title21-vol2/pdf/CFR-2025-title21-vol2-sec117-40.pdf",
        "reviewed_on": "2026-10-27",
        "scope": "US food-equipment hygiene context; applicability to this project is not inferred.",
    },
]
QUESTIONS = {
    "heat_exchanger": [
        "Check duty, U, LMTD/correction and fouling basis for each side.",
        "Review both-side pressure/temperature, cross-contamination and tube/shell materials.",
    ],
    "pump": [
        "Check flow/head, density and efficiency at the duty point.",
        "Review NPSH/cavitation, seals, solids and wetted materials; these are not calculated by the cost correlation.",
    ],
    "compressor": [
        "Check molecular weight, phase and absolute inlet/outlet pressure.",
        "Review staging, cooling, surge/turndown and seal requirements; the model is single-stage ideal gas.",
    ],
    "vessel": [
        "Check holdup/residence volume, orientation and design pressure.",
        "Review vacuum, fatigue, nozzles, supports and code design separately; thickness is a thin-wall screening estimate.",
    ],
    "reactor": [
        "Check holdup, residence time and reaction/thermal duty.",
        "Vessel-shell cost excludes internals, agitation, catalysts and biology-specific equipment unless separately quoted.",
    ],
    "valve": [
        "Establish flow coefficient, pressure drop, shutoff/leakage, actuation and seal requirements.",
        "No validated valve sizing/cost correlation is implemented. Provide a reviewed assembled-unit quotation for costing.",
    ],
    "other": [
        "Identify the equipment service, design inputs and supported sizing or quotation method.",
        "Unsupported equipment must remain unpriced until a reviewed method/quotation is available.",
    ],
}


def unit_case(project, unit_id):
    if project.study:
        for case in project.study.engineering_cases:
            if case.unit_id == unit_id:
                return case
    existing = next(
        (e for e in project.costing.equipment if e.unit_id == unit_id), None
    )
    if existing:
        kind = existing.kind if existing.kind != "quoted" else "other"
        return EngineeringCase(
            unit_id=unit_id,
            unit_kind=kind,
            proposed_equipment=existing.model_dump(exclude_none=True),
        )
    raise ValueError("Unit is not in the BOM or engineering investigation register")


def unit_digest(project, case):
    evidence = [
        e.model_dump(mode="json")
        for e in (project.study.evidence if project.study else [])
        if e.evidence_id in case.evidence_ids
    ]
    existing = next(
        (
            e.model_dump(mode="json")
            for e in project.costing.equipment
            if e.unit_id == case.unit_id
        ),
        None,
    )
    payload = {
        "rules": RULE_VERSION,
        "case": case.model_dump(mode="json", exclude={"baseline_history"}),
        "design_basis": project.study.design_basis.model_dump(mode="json")
        if project.study
        else None,
        "evidence": evidence,
        "equipment": existing,
        "cost_settings": project.costing.settings.model_dump(mode="json"),
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def investigate(project, unit_id):
    case = unit_case(project, unit_id)
    service = case.service
    questions = list(QUESTIONS[case.unit_kind])
    blockers = []
    warnings = []
    for label, value in (
        ("equipment duty/service", service.duty_description),
        ("fluid composition", service.fluid_composition),
        ("concentration/impurity basis", service.concentration_basis),
        ("corrosion/erosion conditions", service.corrosion_conditions),
        ("material-selection rationale", service.material_rationale),
    ):
        if not value.strip():
            blockers.append(f"Document {label}")
    for label, value in (
        ("normal temperature (°C)", service.normal_temperature_c),
        ("design temperature (°C)", service.design_temperature_c),
        ("design pressure (barg)", service.design_pressure_barg),
        ("food contact", service.food_contact),
    ):
        if value is None:
            blockers.append(f"Confirm {label}; unknown is not zero/false")
    if service.phase == "unknown":
        blockers.append("Confirm process phase")
    if service.wetted_material == "unknown" or service.shell_material == "unknown":
        blockers.append("Choose wetted and structural/external materials separately")
    if not service.compatibility_reviewed:
        blockers.append(
            "Review actual-service material compatibility and supporting evidence"
        )
    if not service.mechanical_scope_reviewed:
        blockers.append("Review mechanical requirements and excluded sizing scope")
    if not case.hypothesis.strip():
        blockers.append("Record the engineering hypothesis and how it will be checked")
    if service.food_contact and not service.cleaning_regime.strip():
        blockers.append(
            "Document cleaning/sanitization/sterilization conditions; material name alone does not establish sterility"
        )
    if (
        service.food_contact
        and service.wetted_material == "carbon_steel"
        and not service.lining_or_cladding.strip()
    ):
        blockers.append(
            "Unlined carbon-steel food-contact proposal requires a different documented wetted design; no automatic suitability inferred"
        )
    evidence = [
        e
        for e in (project.study.evidence if project.study else [])
        if e.evidence_id in case.evidence_ids
    ]
    supporting = [
        e
        for e in evidence
        if e.kind != "assumption" and (e.reference.strip() or e.source_url)
    ]
    if not supporting:
        blockers.append(
            "Link an applicable publication, design input, measurement or quotation; an assumption alone is insufficient for a reviewed material baseline"
        )
    if any(not e.reviewer.strip() or e.observed_on is None for e in supporting):
        blockers.append(
            "Record reviewer and observation date for supporting engineering evidence"
        )
    media = (
        service.fluid_composition
        + " "
        + service.corrosion_conditions
        + " "
        + service.cleaning_regime
    ).lower()
    if any(k in media for k in ("chloride", "chlorine", "acid", "caustic", "solids")):
        questions.insert(
            0,
            "Prioritize impurity/concentration, temperature and cleaning compatibility. Generic stainless grades cannot be declared suitable from a keyword.",
        )
    composite = (
        bool(service.lining_or_cladding.strip())
        or service.wetted_material != service.shell_material
        or service.wetted_material in ("polymer", "other")
    )
    spec = None
    sizing = None
    proposal = dict(case.proposed_equipment)
    if proposal:
        proposal["unit_id"] = case.unit_id
        try:
            spec = TypeAdapter(Equipment).validate_python(proposal)
            if spec.kind != "quoted" and case.unit_kind != spec.kind:
                blockers.append("Investigation kind and sizing model disagree")
            if (
                spec.kind == "quoted"
                and (composite or case.unit_kind in ("valve", "other"))
                and not any(e.kind == "quotation" for e in supporting)
            ):
                blockers.append(
                    "Link a reviewed assembled-unit quotation record for this composite or unsupported equipment"
                )
            if composite and spec.kind != "quoted":
                blockers.append(
                    "Composite/lining/special-material assembly requires an assembled-unit quotation; generic material factors do not price it"
                )
            if spec.kind != "quoted":
                expected = (
                    "carbon_steel"
                    if service.wetted_material == "carbon_steel"
                    else "stainless_steel"
                )
                if spec.material != expected:
                    blockers.append(
                        "Costing material proxy disagrees with the proposed wetted material"
                    )
                if service.wetted_material in ("ss304", "ss316l"):
                    warnings.append(
                        "Stainless cost factor is a generic screening proxy, not a 304/316L-specific quotation."
                    )
                design_pressure = getattr(spec, "design_pressure_barg", None)
                if (
                    service.design_pressure_barg is not None
                    and design_pressure is not None
                    and abs(service.design_pressure_barg - design_pressure) > 1e-6
                ):
                    blockers.append(
                        "Sizing design pressure differs from the service design pressure"
                    )
                if (
                    spec.kind == "compressor"
                    and service.design_pressure_barg is not None
                    and service.design_pressure_barg + 1.01325
                    < spec.outlet_pressure_bar_abs
                ):
                    blockers.append(
                        "Service design pressure is below compressor discharge pressure"
                    )
            result = cost_equipment(spec, project.costing.settings)
            sizing = result.model_dump(mode="json")
            warnings.extend(result.warnings)
        except (ValueError, ValidationError) as exc:
            if isinstance(exc, ValidationError):
                blockers.extend(
                    "Sizing input: "
                    + ".".join(str(x) for x in e["loc"])
                    + " — "
                    + e["msg"]
                    for e in exc.errors(include_context=False)[:15]
                )
            else:
                blockers.append(str(exc))
    else:
        blockers.append(
            "Provide complete supported sizing inputs or an assembled-unit quotation; no equipment is invented from stream order"
        )
    if len(case.baseline_history) >= 20:
        blockers.append(
            "Baseline history limit reached; preserve this study and create a new versioned investigation"
        )
    digest = unit_digest(project, case)
    baseline = case.baseline_history[-1] if case.baseline_history else None
    options = [
        {
            "material": "carbon_steel",
            "role": "Candidate for documented compatible non-food service or a quoted structural shell; review corrosion allowance and lifecycle requirements.",
            "source_ids": ["materials"],
        },
        {
            "material": "ss304 / ss316l",
            "role": "Candidate wetted grades for investigation; chemistry, impurities, temperature, cleaning and fabrication determine suitability. Neither grade guarantees sterility.",
            "source_ids": ["materials", "food"]
            if service.food_contact
            else ["materials"],
        },
    ]
    return {
        "unit_id": unit_id,
        "unit_kind": case.unit_kind,
        "rule_version": RULE_VERSION,
        "checked_on": date.today().isoformat(),
        "digest": digest,
        "case": case.model_dump(mode="json"),
        "questions": questions,
        "hypothesis": case.hypothesis or None,
        "counter_evidence": case.counter_evidence or None,
        "material_options": options,
        "evidence": [e.model_dump(mode="json") for e in evidence],
        "sources": SOURCES,
        "sizing": sizing,
        "blockers": list(dict.fromkeys(blockers)),
        "warnings": list(dict.fromkeys(warnings)),
        "can_apply_baseline": not blockers,
        "baseline_status": "not_reviewed"
        if baseline is None
        else "current_user_review"
        if baseline.digest == digest
        else "stale_review",
        "notice": "Source-linked preliminary investigation, not material certification, pressure-code design, food-safety approval or institutional accreditation. Baseline selection is separate from later value engineering.",
    }
