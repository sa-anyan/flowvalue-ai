"""Layout-independent evidence records. Verified means source-supported, not plant certification."""

from typing import Literal

from pydantic import Field

from app.engine.costing import Model

Status = Literal["verified", "inferred", "unresolved"]
Scalar = str | float | int | bool | None


class Evidence(Model):
    id: str
    workbook: str
    sheet: str
    cell: str
    header_cells: list[str] = Field(default_factory=list, max_length=8)
    original_value: Scalar = None
    original_unit: str | None = None
    formula: str | None = None
    cached: bool = False
    property: str
    label: str
    component: str | None = None
    normalized_value: Scalar = None
    normalized_unit: str | None = None
    status: Status = "unresolved"
    note: str = ""


class Entity(Model):
    key: str
    kind: Literal["material", "energy", "equipment"]
    identifier: str
    case: str = ""
    table: str
    id_evidence: Evidence
    values: list[Evidence] = Field(default_factory=list, max_length=256)
    status: Status = "inferred"
    stream_keys: list[str] = Field(default_factory=list, max_length=1500)


class Table(Model):
    id: str
    sheet: str
    range: str
    orientation: Literal["records_in_rows", "records_in_columns"]
    kind: str
    status: Status = "inferred"


class Issue(Model):
    code: str
    status: Status = "unresolved"
    message: str
    evidence_ids: list[str] = Field(default_factory=list)


class Check(Model):
    name: str
    scope: str
    status: Status = "unresolved"
    message: str
    residual: float | None = None
    unit: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)


class Connection(Model):
    key: str
    stream_key: str
    equipment_key: str | None = None
    role: Literal["source", "destination", "mention"]
    basis: Literal["explicit_field", "directional_text", "mention", "missing"]
    evidence_ids: list[str] = Field(default_factory=list, max_length=256)
    status: Status = "unresolved"
    note: str = ""


class BalanceReport(Model):
    schema_version: Literal["flowvalue-balance-v1"] = "flowvalue-balance-v1"
    parser_version: str = "1.0.0"
    filename: str = Field(max_length=255)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    sheets: list[dict[str, str | int | bool]] = Field(max_length=40)
    tables: list[Table] = Field(default_factory=list, max_length=300)
    entities: list[Entity] = Field(default_factory=list, max_length=1500)
    issues: list[Issue] = Field(default_factory=list, max_length=2000)
    checks: list[Check] = Field(default_factory=list, max_length=2000)
    connections: list[Connection] = Field(default_factory=list, max_length=5000)
    declarations: list[Evidence] = Field(default_factory=list, max_length=100)
    coverage: str = "Partial extraction; unsupported and unclassified cells may remain. Review detected tables and source evidence."
    limitations: list[str] = Field(
        default_factory=lambda: [
            "No formula execution or external-link refresh. Cached results may be stale.",
            "No universal simulator/template compatibility claim. Images, drawings, charts, macros, Power Query and embedded objects are not interpreted.",
            "Unknown units, component bases, cases and connections require engineering confirmation.",
            "Closed arithmetic applies only to explicitly declared steady-state complete boundaries. It does not independently validate physical design.",
        ]
    )


class DescriptionState(Model):
    text: str = Field(default="", max_length=6000)
    reviewed_text: str = Field(default="", max_length=6000)
    findings: list[Issue] = Field(default_factory=list, max_length=100)
    questions: list[str] = Field(default_factory=list, max_length=30)
    model: str | None = None
    reviewed_at: str | None = None


class BalanceAttachment(Model):
    report: BalanceReport
    description: DescriptionState = Field(default_factory=DescriptionState)
