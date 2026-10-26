"""Canonical stream schema: kg/h, degrees Celsius, and absolute bar."""

import csv
import io
from enum import StrEnum

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)


class Phase(StrEnum):
    liquid = "liquid"
    vapor = "vapor"
    gas = "gas"
    solid = "solid"
    mixed = "mixed"


class Stream(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    stream_id: str = Field(min_length=1, max_length=100)
    mass_flow_kg_h: float = Field(ge=0)
    temperature_c: float = Field(ge=-273.15)
    pressure_bar_abs: float = Field(gt=0)
    phase: Phase
    source_unit: str | None = None
    destination_unit: str | None = None

    @field_validator("stream_id")
    @classmethod
    def clean_id(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("stream_id must not be blank")
        return value

    @field_validator("phase", mode="before")
    @classmethod
    def normalize_phase(cls, value):
        return value.strip().lower() if isinstance(value, str) else value


class StreamTable(BaseModel):
    model_config = ConfigDict(extra="forbid")
    streams: list[Stream] = Field(min_length=1, max_length=10000)

    @model_validator(mode="after")
    def unique_streams(self):
        ids = [stream.stream_id for stream in self.streams]
        if len(ids) != len(set(ids)):
            raise ValueError("stream_id values must be unique")
        return self


def parse_json(payload: dict) -> StreamTable:
    return StreamTable.model_validate(payload)


def parse_csv(content: bytes) -> StreamTable:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("CSV must use UTF-8 encoding") from exc
    reader = csv.DictReader(io.StringIO(text), strict=True)
    required = {"stream_id", "mass_flow_kg_h", "temperature_c", "pressure_bar_abs", "phase"}
    allowed = required | {"source_unit", "destination_unit"}
    try:
        headers = reader.fieldnames or []
        if len(headers) != len(set(headers)):
            raise ValueError("CSV contains duplicate column names")
        if not required.issubset(headers) or not set(headers).issubset(allowed):
            raise ValueError("CSV columns must include " + ", ".join(sorted(required))
                             + "; optional: source_unit, destination_unit")
        rows = []
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f"CSV row at line {reader.line_num} has incorrect column count")
            rows.append(row)
            if len(rows) > 10000:
                raise ValueError("CSV exceeds 10000 streams")
        return parse_json({"streams": rows})
    except csv.Error as exc:
        raise ValueError(f"Malformed CSV: {exc}") from exc
    except ValidationError:
        raise
