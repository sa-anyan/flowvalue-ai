import json
from datetime import UTC, datetime
from importlib.resources import files
from io import BytesIO
from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from openai import APIError, APIStatusError
from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.agent.availability import (
    ai_status,
    check_connection,
    provider_message,
    require_ai,
)
from app.agent.copilot_research import (
    ResearchRequest,
    ResearchSettings,
    research_events,
)
from app.agent.executive_memo import draft_memo
from app.agent.universal_advisor import (
    AdvisorResult,
    ProjectContext,
    UniversalProcessAdvisor,
)
from app.auth import AuthSettings, authenticated_user, project_rest, public_config
from app.engine.costing import CostingRequest, EquipmentBOM, Model, build_bom
from app.engine.indices import index_catalog
from app.financial.dcf_model import (
    FinancialAssumptions,
    FinancialInputs,
    FinancialResult,
    MonteCarloRequest,
    MonteCarloResult,
    MonteCarloSettings,
    calculate_dcf,
    monte_carlo,
)
from app.financial.sensitivity import tornado
from app.integrations.libraries import (
    BioSTEAMSnapshot,
    OpenPyTEARequest,
    biosteam_project,
    openpytea_equipment,
)
from app.parsers.dwsim_parser import DWSIMImport, parse_dwxml
from app.parsers.stream_parser import StreamTable, parse_csv
from app.reports.excel_builder import build_excel
from app.reports.pdf_builder import build_pdf


class Settings(BaseSettings):
    cors_origins: list[str] = ["http://localhost:3000"]
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
app = FastAPI(title="FlowValue AI API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def protect_api(request: Request, call_next):
    if (
        AuthSettings().require_auth
        and request.url.path.startswith("/api/")
        and request.url.path != "/api/config"
        and request.method != "OPTIONS"
    ):
        try:
            await authenticated_user(request)
        except HTTPException as exc:
            from fastapi.responses import JSONResponse

            return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
    return await call_next(request)


@app.get("/api/config")
def client_config():
    return public_config()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "flowvalue-api"}


@app.post("/api/streams/parse/json", response_model=StreamTable)
def ingest_json(table: StreamTable) -> StreamTable:
    return table


@app.post("/api/streams/parse/csv", response_model=StreamTable)
async def ingest_csv(file: UploadFile) -> StreamTable:
    limit = 5 * 1024 * 1024
    try:
        content = await file.read(limit + 1)
    finally:
        await file.close()
    if len(content) > limit:
        raise HTTPException(status_code=413, detail="CSV exceeds 5 MiB limit")
    try:
        return parse_csv(content)
    except ValidationError as exc:
        raise HTTPException(
            status_code=422, detail=exc.errors(include_context=False)
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/costing/bom", response_model=EquipmentBOM)
def equipment_bom(request: CostingRequest) -> EquipmentBOM:
    try:
        return build_bom(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/financial/dcf", response_model=FinancialResult)
def financial_dcf(request: FinancialInputs) -> FinancialResult:
    return calculate_dcf(request)


@app.post("/api/financial/monte-carlo", response_model=MonteCarloResult)
def financial_monte_carlo(request: MonteCarloRequest) -> MonteCarloResult:
    return monte_carlo(request.financial, request.simulation)


class AssessmentRequest(Model):
    engineering_notes: list[Annotated[str, Field(max_length=1500)]] = Field(
        default_factory=list, max_length=100
    )
    advisor_context: ProjectContext = Field(default_factory=ProjectContext)
    is_demo: bool = False
    costing: CostingRequest
    financial: FinancialAssumptions
    simulation: MonteCarloSettings | None = None


class AssessmentResult(Model):
    bom: EquipmentBOM
    financial: FinancialResult
    uncertainty: MonteCarloResult | None = None


@app.post("/api/assessment", response_model=AssessmentResult)
def assessment(request: AssessmentRequest) -> AssessmentResult:
    try:
        bom = build_bom(request.costing)
        inputs = FinancialInputs(
            total_capex_usd=bom.total_bare_module_cost_usd,
            **request.financial.model_dump(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    bom.assumptions.extend(request.engineering_notes)
    financial = calculate_dcf(inputs)
    financial.warnings.extend(request.engineering_notes)
    return AssessmentResult(
        bom=bom,
        financial=financial,
        uncertainty=monte_carlo(inputs, request.simulation)
        if request.simulation is not None
        else None,
    )


@app.get("/api/demo", response_model=AssessmentRequest)
def demo_assessment() -> AssessmentRequest:
    return AssessmentRequest.model_validate(
        json.loads(files("app.data").joinpath("demo_assessment.json").read_text())
    ).model_copy(update={"is_demo": True})


def export_response(request: AssessmentRequest, format: str, *, demo: bool = False):
    result = assessment(request)
    demo = demo or request.is_demo
    if format == "excel":
        content = build_excel(result.bom, result.financial, demo=demo)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        extension = "xlsx"
    else:
        risk = result.uncertainty or monte_carlo(result.financial.inputs)
        content = build_pdf(result.bom, result.financial, risk, demo=demo)
        media_type, extension = "application/pdf", "pdf"
    return StreamingResponse(
        BytesIO(content),
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="flowvalue-{"demo-" if demo else ""}assessment.{extension}"',
            "Cache-Control": "no-store",
        },
    )


@app.post("/api/export/excel")
def export_excel(request: AssessmentRequest):
    return export_response(request, "excel")


@app.get("/api/export/excel")
def export_demo_excel():
    return export_response(demo_assessment(), "excel", demo=True)


@app.post("/api/export/pdf")
def export_pdf(request: AssessmentRequest):
    return export_response(request, "pdf")


@app.get("/api/export/pdf")
def export_demo_pdf():
    return export_response(demo_assessment(), "pdf", demo=True)


def advisor_profile(project: dict) -> AdvisorResult:
    if len(json.dumps(project)) > 300000:
        raise HTTPException(status_code=413, detail="Advisor payload exceeds 300 KB")
    try:
        if "costing" in project:
            request = AssessmentRequest.model_validate(
                {
                    k: v
                    for k, v in project.items()
                    if k in AssessmentRequest.model_fields
                }
            )
            result = assessment(request)
            project = {
                "bom": result.bom.model_dump(),
                "financial": result.financial.inputs.model_dump(),
                "advisor_context": request.advisor_context.model_dump(),
                "streams": project.get("streams", []),
                "engineering_notes": request.engineering_notes,
            }
        return UniversalProcessAdvisor(project).analyze()
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/assessment/universal-suggestions", response_model=AdvisorResult)
def universal_suggestions(project: dict) -> AdvisorResult:
    return advisor_profile(project)


@app.get("/api/copilot/status")
def copilot_status():
    return ai_status(ResearchSettings())


@app.post("/api/copilot/check")
async def copilot_check():
    return await check_connection(ResearchSettings())


@app.post("/api/copilot/research-sensitivities")
def research_sensitivities(request: ResearchRequest):
    profile = advisor_profile(request.project)
    config = ResearchSettings()
    require_ai(config)
    return StreamingResponse(
        research_events(profile, request, config),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
    )


@app.post("/api/streams/parse/dwxml", response_model=DWSIMImport)
async def ingest_dwxml(file: UploadFile):
    try:
        content = await file.read(5 * 1024 * 1024 + 1)
    finally:
        await file.close()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(413, "DWSIM file exceeds 5 MiB")
    try:
        return parse_dwxml(content)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post("/api/assessment/tornado")
def assessment_tornado(request: AssessmentRequest):
    return tornado(assessment(request).financial.inputs)


@app.get("/api/indices/cepci")
def cepci_catalog():
    return index_catalog()


@app.get("/api/integrations/catalog")
def integration_catalog():
    from importlib.metadata import version

    from openpytea.equipment import COST_DB_DF

    rows = (
        COST_DB_DF[["category", "type", "units", "s_lower", "s_upper"]]
        .fillna("")
        .to_dict(orient="records")
    )
    return {
        "openpytea_version": version("openpytea"),
        "correlations": rows,
        "biosteam_mode": "Validated JSON snapshot from an already simulated trusted environment",
    }


@app.post("/api/integrations/openpytea/equipment")
def library_equipment(request: OpenPyTEARequest):
    try:
        return openpytea_equipment(request)
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post("/api/integrations/biosteam/import", response_model=AssessmentRequest)
def import_biosteam(snapshot: BioSTEAMSnapshot):
    try:
        return AssessmentRequest.model_validate(biosteam_project(snapshot))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post("/api/copilot/executive-memo")
async def executive_memo(request: AssessmentRequest):
    result = assessment(request)
    settings = ResearchSettings()
    require_ai(settings)
    try:
        memo = await draft_memo(
            {
                "project": request.advisor_context.model_dump(),
                "is_demo": request.is_demo,
                "as_of_utc": datetime.now(UTC).isoformat(),
                "economic_summary": {
                    "total_capex_usd": result.bom.total_bare_module_cost_usd,
                    "total_annual_opex_usd": result.financial.inputs.fixed_opex_usd_per_year
                    + result.financial.inputs.variable_opex_usd_per_year,
                    "annual_revenue_usd": result.financial.cash_flows[1].revenue_usd,
                    "npv_usd": result.financial.npv_usd,
                    "irr": result.financial.irr,
                    "lcop_usd_per_unit": result.financial.lcop_usd_per_unit,
                    "cost_accounting_basis": "Total OPEX = fixed + variable. Feedstock and utilities are included within variable OPEX, never added again.",
                },
                "financial": result.financial.model_dump(),
                "bom": result.bom.model_dump(),
                "sensitivity": tornado(result.financial.inputs),
            },
            settings,
        )
    except APIStatusError as exc:
        raise HTTPException(503, provider_message(exc.status_code)) from exc
    except (APIError, ValueError) as exc:
        raise HTTPException(
            502, "Memo provider unavailable or returned no text; retry later"
        ) from exc
    return {
        "markdown": memo,
        "model": settings.openai_model,
        "review_required": True,
        "generated_at": datetime.now(UTC).isoformat(),
        "evidence_basis": "computed_scenario_only",
    }


class SavedProject(Model):
    name: str = Field(min_length=1, max_length=120)
    project_id: UUID | None = None
    expected_revision: int = Field(default=0, ge=0)
    project: AssessmentRequest
    streams: list = Field(default_factory=list, max_length=10000)
    native_import: DWSIMImport | None = None


@app.get("/api/projects")
async def list_projects(
    request: Request, user: Annotated[dict, Depends(authenticated_user)]
):
    return await project_rest(
        request,
        "GET",
        "project_versions?select=id,project_id,name,revision,created_at&order=created_at.desc&limit=100",
    )


@app.get("/api/projects/{version_id}")
async def load_project(
    version_id: UUID,
    request: Request,
    user: Annotated[dict, Depends(authenticated_user)],
):
    rows = await project_rest(
        request, "GET", f"project_versions?id=eq.{version_id}&select=*"
    )
    if not rows:
        raise HTTPException(404, "Project version not found")
    return rows[0]


@app.post("/api/projects")
async def save_project(
    body: SavedProject,
    request: Request,
    user: Annotated[dict, Depends(authenticated_user)],
):
    # Validate before persistence; version insert and revision check are atomic in Postgres.
    assessment(body.project)
    if body.streams:
        try:
            body.streams = StreamTable.model_validate(
                {"streams": body.streams}
            ).model_dump(mode="json")["streams"]
        except ValidationError as exc:
            raise HTTPException(422, exc.errors(include_context=False)) from exc
    snapshot = {
        "project": body.project.model_dump(mode="json"),
        "streams": body.streams,
        "native_import": body.native_import.model_dump(mode="json")
        if body.native_import
        else None,
    }
    if len(json.dumps(snapshot)) > 2_000_000:
        raise HTTPException(413, "Project snapshot exceeds 2 MB")
    return await project_rest(
        request,
        "POST",
        "rpc/save_project_version",
        body={
            "p_name": body.name,
            "p_project_id": str(body.project_id) if body.project_id else None,
            "p_expected_revision": body.expected_revision,
            "p_payload": snapshot,
        },
    )
