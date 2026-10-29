"""Versioned catalog with explicit rights; licensed feeds are an unconnected holder."""

import json
from datetime import date
from importlib.resources import files
from typing import Literal

from pydantic import Field, HttpUrl, model_validator

from app.engine.costing import Model


class IndexRecord(Model):
    period: str = Field(pattern=r"^\d{4}(-(?:0[1-9]|1[0-2]))?$")
    value: float = Field(gt=0, le=1e6)
    source_url: HttpUrl
    source_title: str = Field(min_length=1, max_length=300)
    retrieved_on: date
    reviewed_by: str = Field(min_length=1, max_length=150)
    status: Literal["verified", "assumption"]
    note: str = Field(default="", max_length=1500)
    publication_date: date | None = None
    license_reference: str = Field(default="", max_length=500)
    distribution_rights: Literal[
        "assumption_only", "redistribution_authorized", "internal_only"
    ] = "assumption_only"
    rights_reviewed_on: date | None = None
    rights_expires_on: date | None = None

    @model_validator(mode="after")
    def dates(self):
        today = date.today()
        if self.retrieved_on > today or self.period > today.strftime("%Y-%m"):
            raise ValueError("Index date cannot be in the future")
        if any(
            d is not None and d > today
            for d in (self.publication_date, self.rights_reviewed_on)
        ):
            raise ValueError("Publication/review date cannot be in the future")
        if self.status == "verified" and (
            not self.license_reference.strip()
            or self.publication_date is None
            or self.rights_reviewed_on is None
            or self.distribution_rights == "assumption_only"
        ):
            raise ValueError(
                "Verified records require publication date, license reference and reviewed source rights"
            )
        if self.distribution_rights == "redistribution_authorized" and (
            not self.license_reference.strip()
            or self.rights_reviewed_on is None
            or self.rights_expires_on is None
        ):
            raise ValueError(
                "Redistribution requires a rights reference, review and expiry date"
            )
        return self


def index_catalog() -> dict:
    records = [
        IndexRecord.model_validate(x)
        for x in json.loads(files("app.data").joinpath("cepci.json").read_text())
    ]
    # This API serves all authenticated users: never expose internal-only data.
    visible = [
        r
        for r in records
        if r.distribution_rights != "internal_only"
        and (
            r.distribution_rights == "assumption_only"
            or r.rights_expires_on >= date.today()
        )
    ]
    return {
        "records": [r.model_dump(mode="json") for r in visible],
        "live_feed": False,
        "license_holder": {
            "status": "not_connected",
            "provider": "Chemical Engineering / CEPCI (operator procurement pending)",
            "purchase_required_now": False,
            "required_before_activation": [
                "Provider agreement",
                "Application redistribution rights",
                "Dated observations and source",
                "Named rights reviewer and expiry",
                "Operator-reviewed import and deployment",
            ],
            "activation": "Use the operator import CLI after rights review. No credentials or licensed numbers are bundled; purchasing a personal subscription does not automatically authorize SaaS redistribution.",
        },
        "notice": "No live subscription feed. The 800 default is an assumption. Internal-only or expired licensed observations are withheld from this shared catalog; saved project snapshots require their own rights review.",
    }
