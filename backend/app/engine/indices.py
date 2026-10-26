"""Versioned, operator-maintained index catalog. No unlicensed live-data scraping."""

import json
from datetime import date
from importlib.resources import files

from pydantic import Field, HttpUrl, model_validator

from app.engine.costing import Model


class IndexRecord(Model):
    period: str = Field(pattern=r"^\d{4}(-(?:0[1-9]|1[0-2]))?$")
    value: float = Field(gt=0, le=1e6)
    source_url: HttpUrl
    source_title: str = Field(min_length=1, max_length=300)
    retrieved_on: date
    reviewed_by: str = Field(min_length=1, max_length=150)
    status: str = Field(pattern=r"^(verified|assumption)$")
    note: str = Field(default="", max_length=1500)

    @model_validator(mode="after")
    def dates(self):
        if self.retrieved_on > date.today() or self.period[:4] > str(date.today().year):
            raise ValueError("Index date cannot be in the future")
        return self


def index_catalog() -> dict:
    records = json.loads(files("app.data").joinpath("cepci.json").read_text())
    return {
        "records": [
            IndexRecord.model_validate(x).model_dump(mode="json") for x in records
        ],
        "live_feed": False,
        "notice": "CEPCI is subscription data. Import licensed source observations through the operator CLI; the 800 default remains an assumption, not a verified current value.",
    }
