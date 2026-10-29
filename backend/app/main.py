import json
from datetime import UTC, datetime
from importlib.resources import files
from io import BytesIO
from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, Form, HTTPException, Request, UploadFile
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
from app.agent.engineering_research import research_unit
from app.agent.equipment_interpretation import (
    InterpretationRequest,
    interpret_equipment,
)
from app.agent.executive_memo import draft_memo
from app.agent.process_description import (
    DescriptionRequest,
    compare_description,
    review_description,
)
from app.agent.universal_advisor import (
    AdvisorResult,
    ProjectContext,
    UniversalProcessAdvisor,
)
from app.auth import AuthSettings, authenticated_user, project_rest, public_config
from app.engine.costing import CostingRequest, EquipmentBOM, Model, build_bom
from app.engine.equipment_catalog import router as equipment_catalog_router
from app.engine.indices import index_catalog
from app.engineering.collaboration import router as engineering_reviews_router
from app.engineering.investigation import investigate, unit_case, unit_digest
from app.engineering.models import EngineeringBaseline
from app.engineering.review import engineering_notes, filter_value, open_challenges
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
from app.parsers.balance.models import (
    BalanceAttachment,
    BalanceReport,
    DescriptionState,
)
from app.parsers.dwsim_parser import DWSIMImport, parse_dwxml
from app.parsers.excel_service import WorkbookRequestLimit, parse_upload
from app.parsers.stream_parser import StreamTable, parse_csv
from app.policy.screening import PolicyEvidence, screen_policy
from app.reports.excel_builder import build_excel
from app.reports.pdf_builder import build_pdf
from app.study.legacy import LegacyReference
from app.study.models import OpexApplication, Study, review_study, study_notes
from app.validation.references import reference_report


class Settings(BaseSettings):
    cors_origins: list[str] = ["http://localhost:3000"]
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
app = FastAPI(title="FlowValue AI API", version="0.1.0")
app.include_router(engineering_reviews_router)
app.include_router(equipment_catalog_router)
app.add_middleware(WorkbookRequestLimit)
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


@app.post("/api/streams/parse/excel", response_model=BalanceReport)
async def ingest_excel(file: UploadFile, source: str = Form("excel")):
    try:
        content = await file.read(4 * 1024 * 1024 + 1)
    finally:
        await file.close()
    if len(content) > 4 * 1024 * 1024:
        raise HTTPException(413, "Workbook exceeds 4 MiB limit")
    return await parse_upload(content, file.filename or "workbook.xlsx", source=source)


@app.post("/api/process-description/check", response_model=DescriptionState)
def check_process_description(body: DescriptionRequest):
    return compare_description(body.report, body.description)


@app.post("/api/process-description/review", response_model=DescriptionState)
async def review_process_description(body: DescriptionRequest):
    config = ResearchSettings()
    require_ai(config)
    try:
        return await review_description(body.report, body.description, config)
    except APIStatusError as exc:
        raise HTTPException(503, provider_message(exc.status_code)) from exc
    except (APIError, TimeoutError) as exc:
        raise HTTPException(
            503, "AI review unavailable. Your workbook and description are retained."
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            422,
            "AI mapping could not be grounded safely or exceeded scope limits. No engineering data changed.",
        ) from exc


@app.post("/api/equipment/interpret")
async def interpret_parsed_equipment(body: InterpretationRequest):
    config = ResearchSettings()
    require_ai(config)
    try:
        return await interpret_equipment(body, config)
    except APIStatusError as exc:
        raise HTTPException(503, provider_message(exc.status_code)) from exc
    except (APIError, TimeoutError) as exc:
        raise HTTPException(
            503, "AI interpretation unavailable. Parsed data is unchanged."
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            422,
            "Interpretation could not be grounded or exceeded input limits. No engineering data changed.",
        ) from exc


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
    legacy_reference: LegacyReference | None = None
    study: Study | None = None
    engineering_notes: list[Annotated[str, Field(max_length=1500)]] = Field(
        default_factory=list, max_length=100
    )
    advisor_context: ProjectContext = Field(default_factory=ProjectContext)
    is_demo: bool = False
    costing: CostingRequest
    financial: FinancialAssumptions
    simulation: MonteCarloSettings | None = None


class AssessmentResult(Model):
    study: Study | None = None
    bom: EquipmentBOM
    financial: FinancialResult
    uncertainty: MonteCarloResult | None = None


@app.post("/api/assessment", response_model=AssessmentResult)
def assessment(request: AssessmentRequest) -> AssessmentResult:
    if request.legacy_reference is not None:
        raise HTTPException(
            409,
            "Legacy workbook reference: cached figures are not validated engine inputs. Use the reference views and snapshot export.",
        )
    try:
        bom = build_bom(request.costing)
        inputs = FinancialInputs(
            total_capex_usd=bom.total_bare_module_cost_usd,
            **request.financial.model_dump(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    bom.assumptions.extend(request.engineering_notes)
    if request.study:
        bom.assumptions.extend(study_notes(request.study))
        bom.assumptions.extend(engineering_notes(request))
    financial = calculate_dcf(inputs)
    financial.warnings.extend(request.engineering_notes)
    if request.study:
        financial.warnings.extend(study_notes(request.study))
        financial.warnings.extend(engineering_notes(request))
    return AssessmentResult(
        study=request.study,
        bom=bom,
        financial=financial,
        uncertainty=monte_carlo(inputs, request.simulation)
        if request.simulation is not None
        else None,
    )


class UnitInvestigation(Model):
    project: AssessmentRequest
    unit_id: str = Field(min_length=1, max_length=100)


@app.post("/api/engineering/investigate")
def engineering_investigate(body: UnitInvestigation):
    if body.project.legacy_reference is not None:
        raise HTTPException(
            409, "Legacy reference contains no validated engineering inputs"
        )
    try:
        return investigate(body.project, body.unit_id)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post("/api/engineering/research")
async def engineering_research(body: UnitInvestigation):
    settings = ResearchSettings()
    require_ai(settings)
    report = engineering_investigate(body)
    try:
        return await research_unit(
            report,
            body.project.study.design_basis.model_dump(mode="json")
            if body.project.study
            else {},
            settings,
        )
    except APIStatusError as exc:
        raise HTTPException(503, provider_message(exc.status_code)) from exc
    except (APIError, TimeoutError) as exc:
        raise HTTPException(
            503,
            "Engineering research unavailable; current design retained. Retry later.",
        ) from exc


class UnitBaselineRequest(UnitInvestigation):
    reviewer: str = Field(min_length=1, max_length=150, pattern=r"\S")
    basis: str = Field(min_length=1, max_length=2000, pattern=r"\S")
    confirm: bool = False
    review_version_id: UUID | None = None


@app.post("/api/engineering/apply-baseline", response_model=AssessmentRequest)
async def engineering_apply_baseline(body: UnitBaselineRequest, request: Request):
    if not body.confirm or body.project.study is None:
        raise HTTPException(
            422, "Confirm the preliminary baseline and create a study register first"
        )
    actor = (
        await authenticated_user(request)
        if AuthSettings().require_auth or request.headers.get("authorization")
        else None
    )
    project = body.project.model_copy(deep=True)
    report = engineering_investigate(body)
    if report["blockers"]:
        raise HTTPException(422, "; ".join(report["blockers"])[:3500])
    if body.review_version_id:
        if actor is None:
            raise HTTPException(401, "Sign in to check saved peer-review challenges")
        rows = await project_rest(
            request, "GET", f"project_versions?id=eq.{body.review_version_id}&select=*"
        )
        if not rows or rows[0]["user_id"] != actor["id"]:
            raise HTTPException(
                403, "Only the saved revision owner can apply this baseline"
            )
        events = await project_rest(
            request,
            "GET",
            f"engineering_review_events?version_id=eq.{body.review_version_id}&unit_id=eq.{filter_value(body.unit_id)}&order=created_at.asc&limit=1000",
        )
        if open_challenges(events):
            raise HTTPException(
                409,
                "Resolve open peer-review challenges for this saved unit before applying its baseline",
            )
    from pydantic import TypeAdapter

    from app.engine.costing import Equipment

    case = unit_case(project, body.unit_id)
    spec = TypeAdapter(Equipment).validate_python(
        case.proposed_equipment | {"unit_id": body.unit_id}
    )
    case.proposed_equipment = TypeAdapter(dict[str, float | str]).validate_python(
        spec.model_dump(mode="json", exclude_none=True)
    )
    existed = any(e.unit_id == body.unit_id for e in project.costing.equipment)
    project.costing.equipment = [
        spec if e.unit_id == body.unit_id else e for e in project.costing.equipment
    ] + ([] if existed else [spec])
    record = EngineeringBaseline(
        digest=unit_digest(project, case),
        reviewed_at=datetime.now(UTC),
        reviewer=body.reviewer.strip(),
        actor_id=actor["id"] if actor else None,
        basis=body.basis.strip(),
        equipment=case.proposed_equipment,
    )
    case.baseline_history.append(record)
    project.study.engineering_cases = [
        c for c in project.study.engineering_cases if c.unit_id != body.unit_id
    ] + [case]
    project.engineering_notes = [
        n
        for n in project.engineering_notes
        if not n.startswith(f"ENGINEERING BASELINE {body.unit_id}:")
    ] + [
        f"ENGINEERING BASELINE {body.unit_id}: user-reviewed preliminary; {body.reviewer}; {body.basis}"[
            :1500
        ]
    ]
    assessment(project.model_copy(update={"simulation": None}))
    return project


@app.post("/api/study/review")
def study_review(request: Study):
    return review_study(request)


class ApplyStudyOpex(Model):
    project: AssessmentRequest
    reviewer: str = Field(min_length=1, max_length=150, pattern=r"\S")
    confirm_replace: bool = False


@app.post("/api/study/apply-opex", response_model=AssessmentRequest)
def apply_study_opex(request: ApplyStudyOpex):
    from datetime import date

    project = request.project.model_copy(deep=True)
    if not request.confirm_replace or project.study is None:
        raise HTTPException(422, "Confirm replacement and provide a study register")
    review = review_study(project.study)
    if not review["can_apply_opex"]:
        raise HTTPException(422, "; ".join(review["opex_application_blockers"])[:3000])
    totals = review["totals_usd"]
    opex = {
        "fixed_opex_usd_per_year": totals["fixed_opex"],
        "variable_opex_usd_per_year": totals["feedstock"]
        + totals["utilities"]
        + totals["other_variable"],
        "feedstock_opex_usd_per_year": totals["feedstock"],
        "utility_opex_usd_per_year": totals["utilities"],
    }
    try:
        project.financial = FinancialAssumptions.model_validate(
            project.financial.model_dump() | opex
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    project.study.application = OpexApplication(
        ledger_digest=review["digest"],
        reviewer=request.reviewer.strip(),
        applied_on=date.today(),
        totals=opex,
    )
    # Existing detailed allocations must not contradict the replacement totals.
    project.advisor_context.raw_materials = []
    project.advisor_context.utilities = []
    assessment(project.model_copy(update={"simulation": None}))
    return project


@app.post("/api/release/check")
def release_check(request: AssessmentRequest):
    # Single deterministic DCF. No Monte Carlo, provider calls or cloud writes.
    result = assessment(request.model_copy(update={"simulation": None}))
    references = reference_report()
    excel = build_excel(result.bom, result.financial)
    risk = monte_carlo(
        result.financial.inputs,
        MonteCarloSettings(iterations=100, variation_fraction=0),
    )
    pdf = build_pdf(result.bom, result.financial, risk, demo=request.is_demo)
    evidence = request.financial.incentive.evidence
    screened = screen_policy(evidence) if evidence else None
    checks = [
        {
            "label": "Engineering references",
            "status": "pass" if references["passed"] else "fail",
            "detail": "Frozen implementation checks; not independent plant validation.",
        },
        {
            "label": "Scenario calculation",
            "status": "pass",
            "detail": "BOM and DCF accepted for current scenario.",
        },
        {
            "label": "Excel and PDF generation",
            "status": "pass"
            if excel.startswith(b"PK") and pdf.startswith(b"%PDF")
            else "fail",
            "detail": "Both report engines generated binaries; CI checks live Excel formulas and PDF pages.",
        },
        {
            "label": "Equipment scope",
            "status": "review"
            if any(
                "INCOMPLETE EQUIPMENT" in n or "MIXED EQUIPMENT" in n
                for n in request.engineering_notes
            )
            else "review"
            if request.is_demo
            else "pass",
            "detail": "Demo or imported scope needs engineering review; absence of a warning is not validation of plant completeness.",
        },
        {
            "label": "CEPCI / estimate basis",
            "status": "review",
            "detail": f"Target {request.costing.settings.cepci_current:g}; {request.costing.settings.cepci_basis}. No licensed live feed connected.",
        },
        {
            "label": "Production incentive",
            "status": "pass" if not request.financial.incentive.enabled else "review",
            "detail": "Disabled"
            if not request.financial.incentive.enabled
            else (
                screened["status"]
                if screened
                else "Manual user-confirmed scenario; no policy screening"
            ),
        },
        {
            "label": "AI configuration",
            "status": "pass"
            if ai_status(ResearchSettings())["can_generate"]
            else "review",
            "detail": "Configuration only; model access, billing and generated output not tested. No provider request made.",
        },
        {
            "label": "Account save/reload",
            "status": "manual",
            "detail": "Run sign-in → save new project → reload and reopen latest revision in the hosted browser. This API does not impersonate a user or verify ownership.",
        },
    ]
    if request.study:
        study_check = review_study(request.study)
        checks.append(
            {
                "label": "Study register",
                "status": "review",
                "detail": f"{len(study_check['questions'])} design questions; {len(study_check['opex_application_blockers'])} OPEX blockers; application {'current' if study_check['application_current'] else 'not applied or stale'}. CAPEX register remains planning-only.",
            }
        )
    return {
        "checked_at": datetime.now(UTC).isoformat(),
        "checks": checks,
        "notice": "Readiness evidence is scoped to this request. Review items do not prevent exploratory use. Production tax eligibility, engineering completeness, licensed data rights and account persistence are not certified by this check.",
    }


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


@app.post("/api/policy/screen")
def policy_screen(request: PolicyEvidence):
    return screen_policy(request)


@app.get("/api/engineering/validation")
def engineering_validation():
    return reference_report()


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


@app.post("/api/integrations/biosteam/import")
def import_biosteam(snapshot: BioSTEAMSnapshot):
    try:
        project = AssessmentRequest.model_validate(biosteam_project(snapshot))
        assessment(project)
        result = project.model_dump(mode="json")
        if snapshot.streams:
            result["streams"] = [s.model_dump(mode="json") for s in snapshot.streams]
        return result
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
    balance_import: BalanceAttachment | None = None


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


@app.post("/api/projects/validate-reference", response_model=AssessmentRequest)
def validate_legacy_reference(project: AssessmentRequest):
    if project.legacy_reference is None:
        raise HTTPException(422, "A legacy reference snapshot is required")
    return project


@app.post("/api/projects")
async def save_project(
    body: SavedProject,
    request: Request,
    user: Annotated[dict, Depends(authenticated_user)],
):
    # Validate before persistence; version insert and revision check are atomic in Postgres.
    if body.project.legacy_reference is None:
        assessment(body.project)
    if body.streams:
        try:
            body.streams = StreamTable.model_validate(
                {"streams": body.streams}
            ).model_dump(mode="json")["streams"]
        except ValidationError as exc:
            raise HTTPException(422, exc.errors(include_context=False)) from exc
    snapshot = {
        "balance_import": body.balance_import.model_dump(mode="json")
        if body.balance_import
        else None,
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
