"""Auditable study foundation. Written requirements, never inspiration-workbook logic."""

import hashlib
import json
from datetime import date
from math import fsum
from typing import Literal

from pydantic import Field, HttpUrl, model_validator

from app.engine.costing import Model


class DesignBasis(Model):
    description: str = Field(default="", max_length=10000)
    product_specification: str = Field(default="", max_length=3000)
    location: str = Field(default="", max_length=300)
    site_type: Literal["unknown", "greenfield", "integrated", "brownfield"] = "unknown"
    operating_hours_per_year: float | None = Field(default=None, gt=0, le=8784)
    requirements: str = Field(default="", max_length=5000)
    unresolved_questions: str = Field(default="", max_length=5000)
    source_context: str = Field(default="", max_length=5000)


class Evidence(Model):
    evidence_id: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=300)
    kind: Literal[
        "assumption", "publication", "quotation", "design_input", "measurement"
    ] = "assumption"
    source_url: HttpUrl | None = None
    reference: str = Field(default="", max_length=2000)
    observed_on: date | None = None
    reviewer: str = Field(default="", max_length=150)
    limitation: str = Field(default="", max_length=1500)

    @model_validator(mode="after")
    def valid_date(self):
        if self.observed_on and self.observed_on > date.today():
            raise ValueError("Evidence observation date cannot be in the future")
        return self


class CostItem(Model):
    item_id: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=300)
    category: str = Field(default="Other", min_length=1, max_length=120)
    cost_type: Literal[
        "capex", "fixed_opex", "feedstock", "utilities", "other_variable"
    ] = "fixed_opex"
    status: Literal[
        "included", "excluded", "not_applicable", "missing", "unsupported"
    ] = "missing"
    quantity: float | None = Field(default=None, ge=0, le=1e12)
    unit: str = Field(default="units/year", min_length=1, max_length=80)
    rate_usd: float | None = Field(default=None, ge=0, le=1e12)
    allocation_fraction: float = Field(default=1, ge=0, le=1)
    cost_arrangement: Literal[
        "incremental", "allocated_existing", "charged_elsewhere"
    ] = "incremental"
    basis: str = Field(default="", max_length=2000)
    evidence_ids: list[str] = Field(default_factory=list, max_length=20)


class OpexApplication(Model):
    ledger_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    reviewer: str = Field(min_length=1, max_length=150)
    applied_on: date
    totals: dict[str, float]


class Study(Model):
    schema_version: Literal["flowvalue-study-v1"] = "flowvalue-study-v1"
    design_basis: DesignBasis = Field(default_factory=DesignBasis)
    evidence: list[Evidence] = Field(default_factory=list, max_length=200)
    cost_items: list[CostItem] = Field(default_factory=list, max_length=500)
    application: OpexApplication | None = None

    @model_validator(mode="after")
    def links(self):
        for values, key in (
            (self.evidence, "evidence_id"),
            (self.cost_items, "item_id"),
        ):
            ids = [getattr(x, key) for x in values]
            if len(set(ids)) != len(ids):
                raise ValueError(f"Duplicate {key}")
        evidence_ids = {e.evidence_id for e in self.evidence}
        for item in self.cost_items:
            if set(item.evidence_ids) - evidence_ids:
                raise ValueError(f"Unknown evidence reference for {item.item_id}")
        return self


def ledger_digest(study: Study) -> str:
    # Evidence changes invalidate prior review, even if quantities stay unchanged.
    payload = {
        "cost_items": [x.model_dump(mode="json") for x in study.cost_items],
        "evidence": [x.model_dump(mode="json") for x in study.evidence],
        "design_basis": study.design_basis.model_dump(mode="json"),
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def review_study(study: Study) -> dict:
    totals = {
        k: []
        for k in ("capex", "fixed_opex", "feedstock", "utilities", "other_variable")
    }
    rows = []
    blockers = []
    warnings = []
    for item in study.cost_items:
        issues = []
        if item.status in ("missing", "unsupported"):
            issues.append(
                "Missing information"
                if item.status == "missing"
                else "Estimate cannot be supported"
            )
        if (
            item.status in ("included", "excluded", "not_applicable")
            and not item.basis.strip()
        ):
            issues.append("Document inclusion, exclusion or applicability basis")
        if item.status == "included":
            if item.quantity is None or item.rate_usd is None:
                issues.append(
                    "Quantity and USD unit rate are required; blank is not zero"
                )
            if item.cost_arrangement == "charged_elsewhere":
                issues.append(
                    "Already charged elsewhere; exclude to avoid duplicate expenditure"
                )
        amount = (
            None
            if item.quantity is None or item.rate_usd is None
            else item.quantity * item.rate_usd * item.allocation_fraction
        )
        if amount is not None and amount > 1e15:
            issues.append("Amount exceeds supported financial range")
        if not issues and item.status == "included":
            totals[item.cost_type].append(amount)
        if issues and item.cost_type != "capex":
            blockers.extend(f"{item.item_id}: {x}" for x in issues)
        if item.status == "included" and not item.evidence_ids:
            warnings.append(f"{item.item_id}: no linked evidence; user assumption only")
        rows.append(
            {
                "item_id": item.item_id,
                "amount_usd": amount,
                "counted": not issues and item.status == "included",
                "issues": issues,
                "status": item.status,
            }
        )
    sums = {k: fsum(v) for k, v in totals.items()}
    if any(v > 1e15 for v in sums.values()):
        blockers.append("Ledger total exceeds supported financial range")
    for cost_type in ("fixed_opex", "feedstock", "utilities", "other_variable"):
        if not any(i.cost_type == cost_type for i in study.cost_items):
            blockers.append(
                f"{cost_type}: add an operating-cost row, or document an excluded/not-applicable row; absence is not zero"
            )
    has_opex = any(i.cost_type != "capex" for i in study.cost_items)
    if not has_opex:
        blockers.append(
            "Add and review operating cost items before replacing model OPEX"
        )
    gaps = []
    b = study.design_basis
    for name, value in (
        ("process description", b.description),
        ("product specification", b.product_specification),
        ("site location", b.location),
        ("operating hours", b.operating_hours_per_year),
        ("source context / balance references", b.source_context),
    ):
        if not value:
            gaps.append(f"Provide {name}")
    if b.site_type == "unknown":
        gaps.append("Confirm greenfield, integrated or brownfield site")
    for name, text in (("Food/hygiene", "food"), ("Biological process", "ferment")):
        if (
            text in (b.description + " " + b.product_specification).lower()
            and not b.requirements.strip()
        ):
            gaps.append(
                f"{name}: document material, hygiene/cleaning and service requirements"
            )
    if any(i.cost_type == "capex" for i in study.cost_items):
        warnings.append(
            "CAPEX register is planning-only in Phase A; it is not added to BOM CAPEX or financial metrics. Total-capital integration follows in Phase C."
        )
    return {
        "digest": ledger_digest(study),
        "totals_usd": sums,
        "rows": rows,
        "opex_application_blockers": blockers,
        "can_apply_opex": not blockers,
        "questions": gaps,
        "warnings": warnings,
        "application_current": bool(
            study.application
            and study.application.ledger_digest == ledger_digest(study)
        ),
        "notice": "Review of user inputs, not independent engineering validation or accreditation. USD rates only. OPEX amounts are annual at the selected utilization; quantity must be annual. CAPEX quantities are one-off.",
    }


def study_notes(study: Study) -> list[str]:
    r = review_study(study)
    notes = [
        f"STUDY REGISTER: {len(study.cost_items)} items; {len(study.evidence)} evidence records. CAPEX register is planning-only; financial CAPEX is the equipment BOM."
    ]
    if study.application:
        notes.append(
            f"OPEX REGISTER APPLICATION: reviewer {study.application.reviewer}; {study.application.applied_on}; {'current' if r['application_current'] else 'STALE — ledger/context changed; financial OPEX is the previous applied snapshot until reviewed and applied again'}."
        )
    elif study.cost_items:
        notes.append(
            "OPEX REGISTER NOT APPLIED: financial model still uses its current manual OPEX inputs."
        )
    notes.extend(f"STUDY GAP: {q}" for q in r["questions"])
    notes.extend(
        f"STUDY COST {i.item_id}: {i.status}; {i.cost_type}; {i.description}; basis {i.basis or 'missing'}"
        for i in study.cost_items[:20]
    )
    if len(study.cost_items) > 20:
        notes.append(
            "Study notes show first 20 items; download full study JSON for all entries and evidence."
        )
    return [n[:1500] for n in notes]
