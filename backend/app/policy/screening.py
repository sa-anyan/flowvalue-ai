"""Versioned preliminary screens. Never a tax eligibility certification."""

from datetime import date
from typing import Literal

from pydantic import Field, HttpUrl

from app.engine.costing import Model

RULE_VERSION = "45v-screen-2026-10-27"
REVIEWED_ON = date(2026, 10, 27)
SOURCES = [
    "https://uscode.house.gov/us/usc/119-124/t26/s45V/",
    "https://www.irs.gov/credits-deductions/clean-hydrogen-production-credit",
    "https://www.irs.gov/forms-pubs/about-form-7210",
]


class PolicyEvidence(Model):
    profile: Literal["custom", "us_45v"] = "custom"
    jurisdiction: Literal["unknown", "US", "other"] = "unknown"
    product: Literal["unknown", "hydrogen_kg", "other"] = "unknown"
    construction_start: date | None = None
    placed_in_service: date | None = None
    emissions_kg_co2e_per_kg_h2: float | None = Field(default=None, ge=0, le=1e6)
    independent_verification: bool | None = None
    owner_trade_sale_use: bool | None = None
    no_conflicting_credit: bool | None = None
    electricity_and_emissions_rules_reviewed: bool | None = None
    wage_apprenticeship_reviewed: bool | None = None
    monetization_reviewed: bool | None = None
    reviewer: str = Field(default="", max_length=150)
    reviewed_on: date | None = None
    source_urls: list[HttpUrl] = Field(default_factory=list, max_length=10)
    evidence_reference: str = Field(default="", max_length=1500)


def screen_policy(evidence: PolicyEvidence, *, today: date | None = None) -> dict:
    today = today or date.today()
    checks = []

    def add(key, label, value):
        checks.append(
            {
                "key": key,
                "label": label,
                "status": "unknown" if value is None else "pass" if value else "fail",
            }
        )

    add(
        "review",
        "Named reviewer, dated evidence and supporting source",
        bool(
            evidence.reviewer.strip()
            and evidence.evidence_reference.strip()
            and evidence.source_urls
        )
        if evidence.reviewed_on
        else None,
    )
    add(
        "review_date",
        "Review is not future-dated and is within 90 days",
        None
        if evidence.reviewed_on is None
        else 0 <= (today - evidence.reviewed_on).days <= 90,
    )
    if evidence.profile == "us_45v":
        add(
            "rules_current",
            "Rule catalog reviewed within 90 days; recheck legislation after this window",
            0 <= (today - REVIEWED_ON).days <= 90,
        )
        add(
            "jurisdiction",
            "Production in the US or qualifying US territory",
            None
            if evidence.jurisdiction == "unknown"
            else evidence.jurisdiction == "US",
        )
        add(
            "product",
            "Model production and credit rate both use kg of hydrogen",
            None
            if evidence.product == "unknown"
            else evidence.product == "hydrogen_kg",
        )
        add(
            "construction",
            "Construction begins before 2028-01-01 (document statutory start-of-construction basis)",
            None
            if evidence.construction_start is None
            else evidence.construction_start < date(2028, 1, 1),
        )
        add(
            "service",
            "Placed in service after 2022, with construction preceding service",
            None
            if evidence.placed_in_service is None or evidence.construction_start is None
            else evidence.placed_in_service > date(2022, 12, 31)
            and evidence.construction_start <= evidence.placed_in_service,
        )
        add(
            "emissions",
            "Lifecycle emissions no greater than 4 kg CO2e/kg H2",
            None
            if evidence.emissions_kg_co2e_per_kg_h2 is None
            else evidence.emissions_kg_co2e_per_kg_h2 <= 4,
        )
        for key, label in [
            (
                "independent_verification",
                "Unrelated-party production, emissions and sale/use verification reviewed",
            ),
            (
                "owner_trade_sale_use",
                "Taxpayer ownership, trade/business and sale/use requirements reviewed",
            ),
            (
                "no_conflicting_credit",
                "45Q / 48(a)(15) and other conflicting elections reviewed",
            ),
            (
                "electricity_and_emissions_rules_reviewed",
                "Applicable GREET/PER and electricity sourcing, timing and geographic requirements reviewed",
            ),
            (
                "wage_apprenticeship_reviewed",
                "Wage/apprenticeship or exception and selected rate basis reviewed",
            ),
            (
                "monetization_reviewed",
                "Tax offset or cash monetization eligibility, timing and treatment reviewed",
            ),
        ]:
            add(key, label, getattr(evidence, key))
    else:
        add(
            "monetization_reviewed",
            "Custom scenario eligibility and monetization reviewed",
            evidence.monetization_reviewed,
        )
    passed = all(x["status"] == "pass" for x in checks)
    return {
        "rule_version": RULE_VERSION
        if evidence.profile == "us_45v"
        else "custom-screen-v1",
        "rules_reviewed_on": REVIEWED_ON.isoformat(),
        "checked_on": today.isoformat(),
        "status": "reviewed_scenario"
        if passed
        else "blocked"
        if any(x["status"] == "fail" for x in checks)
        else "needs_evidence",
        "can_enable": passed,
        "checks": checks,
        "sources": SOURCES
        if evidence.profile == "us_45v"
        else [str(x) for x in evidence.source_urls],
        "notice": "Preliminary screen of user-supplied evidence, not verified eligibility. No automatic rate, emissions certification or inflation adjustment. Partial first/last calendar-year credits are not modeled; choose operating-year timing explicitly. Recheck law and professional advice before relying on benefits.",
    }


def policy_notes(evidence: PolicyEvidence) -> list[str]:
    report = screen_policy(evidence)
    return [
        f"Policy screen: {evidence.profile}; {report['status']}; rules {report['rule_version']}; reviewer {evidence.reviewer or 'not supplied'}; review date {evidence.reviewed_on or 'not supplied'}.",
        f"Policy evidence: {evidence.model_dump_json()}",
        report["notice"],
    ]
