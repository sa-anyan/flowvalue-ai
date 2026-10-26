from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.engine.costing import CostingRequest, EquipmentBOM, Model, build_bom
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
from app.parsers.stream_parser import StreamTable, parse_csv


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
    return AssessmentResult(
        bom=bom,
        financial=calculate_dcf(inputs),
        uncertainty=monte_carlo(inputs, request.simulation)
        if request.simulation is not None
        else None,
    )
