"""Local assessment API. Bind to loopback; cloud authentication is not restored here."""

import os
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel, ConfigDict, Field

from backend.currency_conversion import convert_currency, rate_snapshot
from backend.dashboard_reporting.sizing_trace import project_sizing_traces
from backend.currency_conversion.assessment import currency_view
from backend.equipment_costing.registry import list_equipment_models
from backend.ingestion.limits import (
    MAX_OTHER_REQUEST_BYTES,
    MAX_UPLOAD_REQUEST_BYTES,
    MAX_WORKBOOK_BYTES,
)
from backend.orchestration.pipeline import contracts
from backend.orchestration.service import compare, edit, new_assessment
from backend.orchestration.store import Store
from backend.revenue.authority import MAX_REVENUE_REVIEW_LENGTH

app = FastAPI(title="FlowValue Assessment Orchestration")
store = Store(
    os.environ.get("FLOWVALUE_ASSESSMENT_DB", "outputs/assessments/local.sqlite3")
)
CLOUD = os.environ.get("FLOWVALUE_CLOUD", "false").lower() == "true"
if CLOUD:
    from backend.cloud.runtime import ContextExecutor, WorkspaceProxy

    store = WorkspaceProxy()
    executor = ContextExecutor(max_workers=1)
else:
    executor = ThreadPoolExecutor(max_workers=1)
lock = threading.Lock()


class Edit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: int
    section: str
    value: object
    rationale: str = Field(min_length=1, max_length=2000)
    manual_revenue: bool = False


class Rerun(BaseModel):
    use_ai: bool = False


class EngineeringRun(Rerun):
    analysis_years: int | None = Field(default=None, ge=1, le=60)
    construction_years: int | None = Field(default=None, ge=0, le=10)
    prepare_only: bool = True
    # Entry includes automatic assumption population unless explicitly opted out.
    use_ai: bool = True
    process_description: str | None = Field(default=None, max_length=12000)
    revenue_description: str | None = Field(default=None, max_length=6000)


class RegisterEdit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: int
    action: str
    equipment_key: str | None = Field(default=None, max_length=200)
    tag: str | None = Field(default=None, max_length=128)
    name: str | None = Field(default=None, max_length=256)


@app.patch("/api/assessments/{key}/equipment-register")
def edit_equipment_register(key: str, options: RegisterEdit):
    from backend.blocks.engineering_data.edits import save_edit

    if options.action not in {"add", "update", "remove"}:
        raise HTTPException(422, "Choose add, update or remove")
    return save_edit(
        store, key, options.revision, options.model_dump(exclude={"revision"})
    )


class RevenueClarification(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    question: str = Field(min_length=1, max_length=4_000)
    answer: str = Field(min_length=1, max_length=4_000)


class RevenueAuthorityRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: int
    revenue_description: str | None = Field(default=None, max_length=MAX_REVENUE_REVIEW_LENGTH)
    clarifications: list[RevenueClarification] = Field(default_factory=list, max_length=100)
    approve: bool = False
    reinterpret: bool = False


class NamedVersion(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class ResearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: int
    kind: str
    target_id: str = Field(min_length=1, max_length=200)
    consent: bool
    focus: str = Field(default="", max_length=300)
    recommend_price: bool = False


class ComparablePreview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reference: dict
    target_size: float
    target_unit: str
    exponent: float | None = None
    rationale: str = ""


class ReviewDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: int
    finding_id: str
    decision: str
    comment: str = Field(min_length=1, max_length=2000)


@app.exception_handler(KeyError)
async def not_found(request: Request, exc):
    from fastapi.responses import JSONResponse

    return JSONResponse(
        status_code=404, content={"detail": "Assessment or version not found"}
    )


@app.exception_handler(ValueError)
async def invalid(request: Request, exc):
    from fastapi.responses import JSONResponse

    return JSONResponse(status_code=422, content={"detail": str(exc)[:500]})


def submit(key, **kwargs):
    """Explicit background revenue action; no automatic cross-stage calculation."""
    if not lock.acquire(blocking=False):
        raise HTTPException(409, "Another assessment is running")

    def work():
        try:
            from backend.orchestration.service import execute

            execute(store, key, **kwargs)
        finally:
            lock.release()

    try:
        executor.submit(work)
    except Exception:
        lock.release()
        raise


@app.get("/health")
@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "mode": "cloud" if CLOUD else "local",
        "ai_enabled": os.environ.get("AI_ENABLED", "").lower() == "true",
    }


@app.post("/api/assessments/{key}/research", status_code=202)
def research(key: str, request: ResearchRequest):
    state = store.get(key)
    if request.consent is not True:
        raise HTTPException(
            422, "Explicit consent is required for external research and API usage"
        )
    if request.kind not in {"equipment", "market"}:
        raise HTTPException(422, "Choose equipment or market research")
    if state.get("running") or not lock.acquire(blocking=False):
        raise HTTPException(409, "Wait for the current task to finish")
    try:
        if request.revision != state["revision"]:
            raise ValueError("Assessment changed; reload before researching")
        state["running"] = True
        state["research_job"] = {
            "status": "running",
            "kind": request.kind,
            "target_id": request.target_id,
            "focus": request.focus,
            "consent": "Explicit user-triggered scoped research",
            "plan_changed": False,
        }
        state = store.put(state, state["revision"])
    except Exception:
        lock.release()
        raise

    def work():
        from backend.orchestration.deep_research import research_draft
        from backend.orchestration.provider import EngineeringProvider
        from backend.revenue.advisor import RevenueAIError

        try:
            result = research_draft(
                state,
                request.kind,
                request.target_id,
                EngineeringProvider(),
                focus=request.focus,
            )
            if request.kind == "market" and request.recommend_price:
                from backend.revenue.price_review import propose_review
                result.update(propose_review(state, request.target_id, result, EngineeringProvider()))
            current = store.get(key)
            current.setdefault("research_drafts", []).append(result)
            current["research_job"] = dict(current["research_job"], status="completed")
        except (
            Exception
        ) as exc:  # noqa: BLE001 -- retain existing model on research outage
            current = store.get(key)
            current["research_job"] = dict(
                current["research_job"],
                status="failed",
                notice=(
                    str(exc)[:300]
                    if isinstance(exc, (ValueError, RevenueAIError))
                    else type(exc).__name__
                ),
            )
        finally:
            current["running"] = False
            store.put(current, current["revision"])
            lock.release()

    executor.submit(work)
    return {"id": key}


@app.post("/api/assessments/{key}/comparable-preview")
def preview_comparable(key: str, request: ComparablePreview):
    store.get(key)
    from backend.equipment_costing.quotes import comparable_cost
    from backend.orchestration.codec import plain

    return plain(
        comparable_cost(
            request.reference,
            target_size=request.target_size,
            target_unit=request.target_unit,
            exponent=request.exponent,
            rationale=request.rationale,
        )
    )


@app.post("/api/assessments/{key}/review-decisions")
def record_review(key: str, request: ReviewDecision):
    state = store.get(key)
    if state.get("running") or state["revision"] != request.revision:
        raise HTTPException(409, "Wait for the study, then reload its current revision")
    ids = {
        f["id"] for r in state.get("analyst_reviews", []) for f in r.get("findings", [])
    }
    if request.finding_id not in ids or request.decision not in {
        "agree",
        "challenge",
        "defer",
    }:
        raise ValueError("Select an existing specialist finding and supported decision")
    state.setdefault("review_decisions", []).append(
        dict(
            request.model_dump(),
            actor="local user",
            note="Review recorded; design/cost inputs not changed",
        )
    )
    return store.put(state, state["revision"])


@app.post("/api/assessments", status_code=202)
async def upload(
    file: UploadFile = File(...),  # noqa: B008 -- FastAPI dependency declaration
    description: str = Form(""),
    revenue_description: str = Form(""),
    use_ai: bool = Form(False),
    workflow: str = Form("full"),
    analysis_years: int | None = Form(None),
    construction_years: int = Form(2),
):
    content = await file.read(MAX_WORKBOOK_BYTES + 1)
    if not content or len(content) > MAX_WORKBOOK_BYTES:
        raise HTTPException(413, "Choose a workbook up to 20 MiB")
    if len(description) + len(revenue_description) > 12000:
        raise HTTPException(422, "Description exceeds 12,000 characters")
    name = Path(file.filename or "workbook").name
    if Path(name).suffix.lower() not in {".xlsx", ".xls", ".xlsm"}:
        raise HTTPException(422, "Choose .xlsx, .xls or .xlsm")
    if lock.locked():
        raise HTTPException(409, "Another assessment is running")
    policy = None
    if analysis_years is not None:
        from backend.blocks.cashflow.schedule import make_policy, apply_policy

        policy = make_policy(analysis_years, construction_years)
    state = new_assessment(
        store, content, name, description, revenue_description, workflow=workflow
    )
    if policy is not None:
        state["analysis_schedule"] = policy
        state["plan"].setdefault("operating_economics", {})
        state["plan"]["operating_economics"] = apply_policy(
            state["plan"]["operating_economics"], state["analysis_schedule"]
        )
        state = store.put(state, state["revision"])
    if workflow == "revenue":
        submit(state["id"], content=content, use_ai=use_ai)
        return {"id": state["id"]}
    from backend.blocks.execution import initialize
    import hashlib

    state["source_sha256"] = hashlib.sha256(content).hexdigest()
    state = initialize(state)
    state.update(
        running=False, status="Source loaded. Run a stage explicitly.", progress=[]
    )
    store.put(state, state["revision"])
    return {"id": state["id"]}


class CurrencyConversionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    amount: str
    source_currency: str
    target_currency: str
    rate_date: str | None = None


@app.get("/api/currency/rates")
def currency_rates():
    return rate_snapshot()


@app.post("/api/currency/convert")
def currency_convert(request: CurrencyConversionRequest):
    return convert_currency(
        request.amount,
        request.source_currency,
        request.target_currency,
        rate_date=request.rate_date,
    )


class CashflowPolicyEdit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: int
    policy: dict
    approve_revenue: bool = False


@app.get("/api/assessments/{key}/cashflow")
def cashflow_snapshot(key: str):
    from backend.blocks.cashflow.view import snapshot

    return snapshot(store.get(key))


@app.patch("/api/assessments/{key}/cashflow")
def save_cashflow_policy(key: str, change: CashflowPolicyEdit):
    from backend.blocks.cashflow.schedule import save

    if lock.locked():
        raise HTTPException(409, "Wait for the active calculation to finish")
    return save(
        store,
        key,
        change.revision,
        change.policy,
        approve_revenue=change.approve_revenue,
    )


@app.get("/api/assessments/{key}")
def get(key: str, historical: bool = False, currency: str | None = None):
    saved = store.get(key)
    from backend.blocks.execution import view
    from backend.equipment_resolution.identity import project_assessment_identity

    if historical:
        return project_sizing_traces(project_assessment_identity(saved))
    return project_sizing_traces(
        project_assessment_identity(currency_view(view(saved), currency), saved)
    )


@app.patch("/api/assessments/{key}")
def patch(key: str, change: Edit):
    return edit(
        store,
        key,
        change.revision,
        change.section,
        change.value,
        change.rationale,
        manual_revenue=change.manual_revenue,
    )


from backend.revenue.rate_workspace import RateStudyRequest


@app.post("/api/assessments/{key}/revenue-rates")
def revenue_rates(key: str, request: RateStudyRequest):
    from backend.revenue.rate_workspace import save_rates
    return save_rates(store, key, request)


@app.post("/api/assessments/{key}/revenue-authority")
def revenue_authority(key: str, options: RevenueAuthorityRequest):
    from backend.revenue.authority import update

    if options.reinterpret and options.approve:
        raise HTTPException(422, "Review the AI interpretation before approving it")
    if options.clarifications and not options.reinterpret:
        raise HTTPException(422, "Revenue clarifications must be interpreted and reviewed before approval")
    if options.reinterpret and lock.locked():
        raise HTTPException(409, "Wait for the current assessment to finish")
    state = update(
        store,
        key,
        options.revision,
        text=options.revenue_description,
        approve=options.approve,
        clarifications=[(item.question, item.answer) for item in options.clarifications],
    )
    if options.reinterpret:
        state["running"] = True
        state["status"] = "interpreting_revenue_box"
        state["progress"] = [{"stage": "revenue_planning", "status": "queued"}]
        state = store.put(state, state["revision"])
        try:
            submit(key, use_ai=True, refresh_revenue=True)
        except Exception:
            state = store.get(key)
            state["running"] = False
            state["status"] = "Revenue Box saved; AI interpretation could not start"
            store.put(state, state["revision"])
            raise
    return state


class RevenuePreflight(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: int


@app.post("/api/assessments/{key}/revenue-preflight")
def revenue_preflight(key: str, request: RevenuePreflight):
    from backend.revenue.review import inspect_revenue, preview_annual_continuation

    state = store.get(key)
    if state.get("running") or state["revision"] != request.revision:
        raise HTTPException(409, "Reload the current assessment before reviewing")
    report = (
        state.get("scoped_report")
        or state.get("effective_report")
        or state.get("parsed", {}).get("report", {})
    )
    config = state.get("plan", {}).get("operating_economics", {})
    text = state.get("revenue_description", "")
    result = inspect_revenue(config, text, report)
    if result["questions"]:
        result["annual_projection"] = preview_annual_continuation(config, text, report)
    return {**result, "revision": state["revision"]}


class RevenueLinePreview(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: int
    method: str
    subtype: str
    inputs: dict
    identity: str | None = None


@app.post("/api/assessments/{key}/revenue-line-preview")
def preview_revenue_line(key: str, options: RevenueLinePreview):
    from backend.revenue.method_forms import build_line

    state = store.get(key)
    if state.get("running") or state["revision"] != options.revision:
        raise HTTPException(409, "Wait for completion and reload the current revision")
    years = (
        state.get("plan", {})
        .get("operating_economics", {})
        .get("financial", {})
        .get("operating_years")
    )
    config = state.get("plan", {}).get("operating_economics", {})
    old = next(
        (
            line
            for line in config.get("commercial_lines", [])
            if line.get("id") == options.identity
        ),
        None,
    )
    if old and not old.get("method_form"):
        terms = old.get("years", [])
        fields = (
            "quantity",
            "rate",
            "fixed_payment",
            "minimum_quantity",
            "minimum_payment",
            "availability",
            "escalation",
        )
        if any(
            y.get("minimum_quantity") or y.get("minimum_payment") for y in terms
        ) or any(
            any(y.get(field) != terms[0].get(field) for field in fields)
            for y in terms[1:]
        ):
            raise HTTPException(
                422,
                "This line has annual variations or minimum-payment terms. Use the advanced annual editor to preserve them.",
            )
        if options.method != "capacity_availability" and any(
            y.get("availability", 1) != 1 for y in terms
        ):
            raise HTTPException(
                422,
                "This line has a separate availability adjustment. Use its advanced annual editor to preserve it.",
            )
    line = build_line(
        options.method,
        options.subtype,
        options.inputs,
        years,
        identity=options.identity,
    )
    if old and not old.get("method_form"):
        line["method_form"]["previous_inputs"] = old
    return line


@app.get("/api/catalogue/revenue-forms")
def revenue_form_catalogue():
    from backend.revenue.method_forms import catalogue

    return catalogue()


@app.get("/api/catalogue/{stage}-factors")
def cost_factor_catalogue(
    stage: str, model_id: str = "garrett", process_type: str = "mixed"
):
    if stage == "capex":
        from backend.capex import get_factor_ranges

        return get_factor_ranges(model_id, process_type)
    if stage == "opex":
        from backend.opex import get_factor_ranges

        return get_factor_ranges(model_id)
    raise HTTPException(404, "Unknown cost catalogue")


@app.post("/api/assessments/{key}/run", status_code=202)
def rerun(key: str, options: Rerun):
    if store.get(key).get("workflow") == "revenue":
        submit(key, use_ai=options.use_ai)
        return {"id": key}
    # Older clients and saved Team 8 projects enter the exact same workflow.
    return run_engineering_workflow(key, EngineeringRun(use_ai=options.use_ai))


class EngineeringApproval(BaseModel):
    revision: int


@app.post("/api/assessments/{key}/engineering-approval")
def approve_engineering_data(key: str, options: EngineeringApproval):
    from backend.blocks.stage_workflow import approve
    from backend.blocks.execution import view

    return view(approve(store, key, options.revision))


@app.post("/api/assessments/{key}/run-all-stages", status_code=202)
def run_all_stages(key: str, options: Rerun):
    return submit_stage_group(key, options)


def submit_stage_group(key: str, options: Rerun, *, economic_only=False):
    from backend.blocks.stage_workflow import queue, run

    if not lock.acquire(blocking=False):
        raise HTTPException(409, "Another stage is running")
    try:
        queue(store, key, economic_only=economic_only)
    except Exception:
        lock.release()
        raise

    def work():
        try:
            run(store, key, use_ai=options.use_ai)
        finally:
            lock.release()

    try:
        executor.submit(work)
    except Exception:
        state = store.get(key)
        state["running"] = False
        state["stage_workflow"]["status"] = "failed"
        store.put(state, state["revision"])
        lock.release()
        raise
    return {"id": key}


@app.post("/api/assessments/{key}/stages/{stage}/run", status_code=202)
def run_individual_stage(key: str, stage: str, options: Rerun):
    if stage in {"capex", "opex", "revenue"}:
        return submit_stage_group(key, options, economic_only=True)
    from backend.blocks.execution import queue_stage, run_stage

    if not lock.acquire(blocking=False):
        raise HTTPException(409, "Another stage is running")
    try:
        from backend.blocks.stage_workflow import approved

        if stage != "engineering_data" and not approved(store.get(key)):
            raise ValueError(
                "Review and approve Engineering Data before running downstream stages"
            )
        queued = queue_stage(store, key, stage)
    except Exception:
        lock.release()
        raise

    def work():
        try:
            run_stage(store, key, stage, use_ai=options.use_ai)
        finally:
            lock.release()

    try:
        executor.submit(work)
    except Exception:
        state = store.get(key)
        state["running"] = False
        store.put(state, state["revision"])
        lock.release()
        raise
    return {"id": key, "stage": stage}


@app.post("/api/assessments/{key}/stages/{stage}/prepare", status_code=202)
def prepare_stage_assumptions(key: str, stage: str):
    if stage not in {"capex", "opex"}:
        raise HTTPException(422, "Choose CAPEX or OPEX")
    if not lock.acquire(blocking=False):
        raise HTTPException(409, "Another stage is running")
    try:
        state = store.get(key)
        if state.get("running"):
            raise ValueError("Another stage is running")
        store.version(key, "Before " + stage.upper() + " assumption preparation")
        state["running"] = True
        store.put(state, state["revision"])
    except Exception:
        lock.release()
        raise

    def work():
        try:
            from backend.blocks.preparation import prepare_stage

            prepare_stage(store, key, stage)
        except Exception as exc:
            current = store.get(key)
            current["running"] = False
            current.setdefault("stage_preparations", {})[stage] = {
                "status": "needs_review",
                "notice": str(exc),
            }
            store.put(current, current["revision"])
        finally:
            lock.release()

    try:
        executor.submit(work)
    except Exception:
        current = store.get(key)
        current["running"] = False
        store.put(current, current["revision"])
        lock.release()
        raise
    return {"id": key, "stage": stage}


@app.post("/api/assessments/{key}/engineering/run", status_code=202)
def run_engineering_workflow(key: str, options: EngineeringRun):
    from backend.blocks.engineering_workflow import queue, run

    if not lock.acquire(blocking=False):
        raise HTTPException(409, "Another stage is running")
    try:
        state = store.get(key)
        if state.get("running"):
            raise HTTPException(409, "Another stage is running")
        changed_process = (
            options.process_description is not None
            and options.process_description
            != state.get("process_description", state.get("description", ""))
        )
        changed_revenue = (
            options.revenue_description is not None
            and options.revenue_description != state.get("revenue_description", "")
        )
        if changed_process or changed_revenue:
            store.version(key, "Before Entry engineering context update")
        if changed_revenue:
            from backend.revenue.authority import update

            state = update(
                store, key, state["revision"], text=options.revenue_description
            )
        if changed_process:
            state.update(
                description=options.process_description,
                process_description=options.process_description,
            )
            store.put(state, state["revision"])
        if options.analysis_years is not None:
            from backend.blocks.cashflow.schedule import make_policy, apply_policy

            current = state.get("analysis_schedule")
            policy = make_policy(
                options.analysis_years,
                (
                    options.construction_years
                    if options.construction_years is not None
                    else (current or {}).get("construction_years", 2)
                ),
                current,
            )
            if policy != current:
                state = store.get(key)
                store.version(key, "Before Entry analysis horizon change")
                state["analysis_schedule"] = policy
                state["plan"]["operating_economics"] = apply_policy(
                    state["plan"].get("operating_economics", {}), policy
                )
                state.pop("revenue_approval", None)
                state = store.put(state, state["revision"])
        queue(store, key)
    except Exception:
        lock.release()
        raise

    def work():
        try:
            run(store, key, use_ai=options.use_ai, prepare_only=options.prepare_only)
        finally:
            lock.release()

    try:
        executor.submit(work)
    except Exception:
        state = store.get(key)
        state.update(running=False, engineering_workflow={"status": "failed"})
        state.pop("queued_stage", None)
        store.put(state, state["revision"])
        lock.release()
        raise
    from backend.blocks.execution import PIPELINE_ID

    return {
        "id": key,
        "workflow": (
            "engineering_data_to_equipment_review"
            if options.prepare_only
            else "engineering_data_to_equipment"
        ),
        "pipeline_id": PIPELINE_ID,
    }


@app.post("/api/assessments/{key}/versions")
def save(key: str, version: NamedVersion):
    return {"id": store.version(key, version.name)}


@app.get("/api/assessments/{key}/versions")
def versions(key: str):
    store.get(key)
    return store.versions(key)


@app.post("/api/versions/{version}/open")
def reopen(version: str):
    from backend.equipment_resolution.identity import project_assessment_identity

    return project_sizing_traces(project_assessment_identity(store.load(version)))


@app.get("/api/assessments/{key}/compare/{other}")
def comparison(key: str, other: str):
    return compare(store.get(key), store.get(other))


@app.get("/api/catalogue")
def catalogue():
    from backend.engineering_sizing import list_methods
    from backend.engineering_sizing.registry import PARAMETER_UNITS

    return {
        "engineering_sizing_methods": list_methods(),
        "sizing_parameter_units": PARAMETER_UNITS,
        "equipment": [
            {
                "id": m["id"],
                "equipment": m.get("equipment", m.get("category", "Equipment")),
                "configuration": m["configuration"],
                "size_unit": m["size_unit"],
                "source": m.get("source", "garrett"),
                "limitations": m.get("limitation"),
                "availability": m.get("status", "available"),
                "input_requirements": m.get("input_requirements", []),
                "cost_scope": m.get("cost_scope"),
                "source_year": m.get("source_year"),
            }
            for m in list_equipment_models(source="all")
        ],
        "contracts": contracts(),
    }


@app.middleware("http")
async def local_request_guard(request: Request, call_next):
    from urllib.parse import urlsplit

    from fastapi.responses import JSONResponse

    origin = request.headers.get("origin")
    host = request.headers.get("host", "").split(":")[0]
    if CLOUD:
        if request.method in {"POST", "PATCH"}:
            length = request.headers.get("content-length")
            if length is None or not length.isdigit():
                return JSONResponse(
                    status_code=411, content={"detail": "Content length required"}
                )
            if int(length) > (
                MAX_UPLOAD_REQUEST_BYTES
                if request.method == "POST" and request.url.path == "/api/assessments"
                else MAX_OTHER_REQUEST_BYTES
            ):
                return JSONResponse(
                    status_code=413,
                    content={"detail": "Request exceeds upload or request size limit"},
                )
        if request.url.path in {"/health", "/api/health"}:
            return await call_next(request)
        from backend.cloud.runtime import verified_workspace, workspace

        authorization = request.headers.get("authorization", "")
        if not authorization.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"detail": "Sign in required"})
        import asyncio

        try:
            scoped = await asyncio.to_thread(verified_workspace, authorization[7:])
        except PermissionError:
            return JSONResponse(status_code=401, content={"detail": "Sign in required"})
        handle = workspace.set(scoped)
        try:
            return await call_next(request)
        finally:
            workspace.reset(handle)
    if host not in {"localhost", "127.0.0.1", "testserver"}:
        return JSONResponse(status_code=403, content={"detail": "Local workspace only"})
    if origin and urlsplit(origin).netloc not in {
        "localhost:3000",
        "127.0.0.1:3000",
        "localhost:8000",
        "127.0.0.1:8000",
    }:
        return JSONResponse(
            status_code=403,
            content={"detail": "Cross-origin assessment requests are not allowed"},
        )
    if request.method in {"POST", "PATCH"}:
        length = request.headers.get("content-length")
        if length is None or not length.isdigit():
            return JSONResponse(
                status_code=411, content={"detail": "Content length required"}
            )
        if int(length) > (
            MAX_UPLOAD_REQUEST_BYTES
            if request.method == "POST" and request.url.path == "/api/assessments"
            else MAX_OTHER_REQUEST_BYTES
        ):
            return JSONResponse(
                status_code=413,
                content={"detail": "Request exceeds upload or request size limit"},
            )
    return await call_next(request)


@app.get("/api/versions")
def all_versions():
    return store.all_versions()


@app.get("/api/assessments/{key}/report")
def study_report(key: str, currency: str | None = None):
    from fastapi.responses import HTMLResponse

    from backend.dashboard_reporting.study_report import render_study

    state = store.get(key)
    if state.get("running"):
        raise HTTPException(409, "Wait for this study calculation to finish")
    from backend.blocks.execution import view

    viewed = view(state)
    saved_equipment = ((state.get("results") or {}).get("stages") or {}).get("equipment")
    if saved_equipment and not viewed["results"]["stages"].get("equipment"):
        viewed["results"]["stages"]["equipment"] = saved_equipment
    state = currency_view(viewed, currency)
    return HTMLResponse(render_study(state), headers={"Cache-Control": "no-store"})


@app.get("/api/assessments/{key}/snapshot")
def study_snapshot(key: str, currency: str | None = None):
    import json

    from fastapi.responses import Response

    state = store.get(key)
    if state.get("running"):
        raise HTTPException(409, "Wait for this study calculation to finish")
    from backend.blocks.execution import MODE, view

    if state.get("execution_mode") == MODE or not state.get("results"):
        state = view(state)
    state = currency_view(state, currency)
    return Response(
        json.dumps(project_sizing_traces(state), indent=2, allow_nan=False),
        media_type="application/json",
        headers={
            "Content-Disposition": 'attachment; filename="FlowValue-TEA-assessment.json"',
            "Cache-Control": "no-store",
        },
    )


class CommercialStrategyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: int
    description: str = Field(min_length=10, max_length=12000)
    process_description: str | None = Field(default=None, max_length=12000)
    revenue_description: str | None = Field(default=None, max_length=6000)
    research_consent: bool = False


@app.post("/api/assessments/{key}/commercial-strategy", status_code=202)
def commercial_strategy(key: str, options: CommercialStrategyRequest):
    import copy

    from backend.revenue.llm.commercial_strategy_analyst import execute_strategy

    baseline = store.get(key)
    if baseline.get("running") or baseline["revision"] != options.revision:
        raise HTTPException(
            409, "Wait for assessment completion or reload current revision"
        )
    if not baseline.get("plan", {}).get("operating_economics"):
        raise HTTPException(
            422,
            "An operating-study draft is required before interpreting a new commercial scenario",
        )
    if not lock.acquire(blocking=False):
        raise HTTPException(409, "Another assessment is running")
    try:
        content = store.workbook(key)
        draft = copy.deepcopy(baseline)
        draft.update(
            description=options.description,
            process_description=(
                options.process_description
                if options.process_description is not None
                else options.description
            ),
            revenue_description=options.revenue_description or "",
            results=None,
            running=True,
            parent_assessment=key,
            status="Commercial Strategy Analyst: queued",
            progress=[],
            commercial_strategy={
                "name": "Commercial Strategy Analyst",
                "status": "queued",
            },
        )
        from backend.revenue.authority import bind

        draft.pop("revenue_approval", None)
        bind(draft)
        created = store.create(draft, content)

        def work():
            try:
                execute_strategy(
                    store,
                    created["id"],
                    baseline,
                    research_consent=options.research_consent,
                )
            finally:
                lock.release()

        executor.submit(work)
    except Exception:
        lock.release()
        raise
    return {"id": created["id"]}


# Monte Carlo uses the existing owner-scoped assessment store and background executor.
from backend.scenarios_and_uncertainty.monte_carlo.models import (
    Settings as MonteCarloSettings,
)


def require_stage_output(key, stage):
    from backend.blocks.execution import view, fresh

    state = view(store.get(key))
    if not fresh(state, stage):
        raise HTTPException(
            422, "Data required: run " + stage.replace("_", " ") + " first."
        )
    return state


@app.get("/api/assessments/{key}/monte-carlo/discover")
def monte_discover(key: str):
    from backend.scenarios_and_uncertainty.monte_carlo.discovery import discover

    return discover(require_stage_output(key, "engineering_data"))


@app.post("/api/assessments/{key}/monte-carlo/run", status_code=202)
def monte_run(key: str, settings: MonteCarloSettings):
    require_stage_output(key, "financial")
    from backend.scenarios_and_uncertainty.monte_carlo.service import start, work

    if not lock.acquire(blocking=False):
        raise HTTPException(409, "Another calculation is running")
    try:
        job = start(store, key, settings)
    except Exception:
        lock.release()
        raise

    def task():
        try:
            work(store, job["id"])
        finally:
            lock.release()

    try:
        executor.submit(task)
    except Exception:
        lock.release()
        raise
    return job


@app.get("/api/assessments/{key}/monte-carlo/jobs")
def monte_jobs(key: str):
    store.get(key)
    return [
        {
            k: j.get(k)
            for k in (
                "id",
                "status",
                "completed",
                "total",
                "settings",
                "summary",
                "baseline_revision",
            )
        }
        for j in store.related_states(key)
        if j.get("kind") == "monte_carlo_job"
    ]


@app.get("/api/assessments/{key}/monte-carlo/jobs/{job_id}")
def monte_job(key: str, job_id: str):
    from backend.scenarios_and_uncertainty.monte_carlo.service import get_job

    return get_job(store, key, job_id)


@app.get("/api/assessments/{key}/monte-carlo/jobs/{job_id}/runs/{index}")
def monte_sample(key: str, job_id: str, index: int):
    from backend.scenarios_and_uncertainty.monte_carlo.service import get_results

    result = get_results(store, key, job_id)
    if not 0 <= index < len(result["runs"]):
        raise HTTPException(404, "Run not found")
    return result["runs"][index]


@app.get("/api/assessments/{key}/monte-carlo/jobs/{job_id}/export")
def monte_export(key: str, job_id: str, format: str = "csv"):
    from fastapi.responses import Response

    from backend.scenarios_and_uncertainty.monte_carlo.exports import export
    from backend.scenarios_and_uncertainty.monte_carlo.service import get_results

    if format not in {"csv", "xlsx"}:
        raise HTTPException(422, "Choose csv or xlsx")
    data, mime = export(get_results(store, key, job_id), format)
    return Response(
        data,
        media_type=mime,
        headers={
            "Content-Disposition": f'attachment; filename="FlowValue-Monte-Carlo.{format}"',
            "Cache-Control": "no-store",
        },
    )


@app.post("/api/assessments/{key}/monte-carlo/jobs/{job_id}/cancel")
def monte_cancel(key: str, job_id: str):
    from backend.scenarios_and_uncertainty.monte_carlo.service import (
        get_job,
        update_job,
    )

    job = get_job(store, key, job_id)
    if job["status"] in {"queued", "running"}:
        job = update_job(store, job_id, {"cancel_requested": True})
    return job


@app.post("/api/assessments/{key}/monte-carlo/prepare", status_code=202)
def monte_prepare(key: str, request: Rerun):
    if not request.use_ai:
        raise HTTPException(422, "Explicit AI preparation request required")
    from backend.orchestration.design_handoff import complete
    from backend.orchestration.pipeline import run
    from backend.orchestration.provider import EngineeringProvider
    from backend.orchestration.register import register

    state = store.get(key)
    if state.get("running") or not lock.acquire(blocking=False):
        raise HTTPException(409, "Another calculation is running")
    try:
        draft = store.create(
            {
                **state,
                "parent_assessment": key,
                "running": True,
                "status": "Preparing Monte Carlo engineering assumptions",
            },
            store.workbook(key),
        )

    except Exception:
        lock.release()
        raise

    def task():
        current = store.get(draft["id"])
        try:
            report = (
                current.get("scoped_report")
                or current.get("effective_report")
                or current["parsed"]["report"]
            )
            current["plan"], current["design_handoffs"] = complete(
                report,
                current["description"],
                current["plan"],
                current["locked"],
                store,
                EngineeringProvider(),
            )
            from backend.scenarios_and_uncertainty.monte_carlo.advisor import recommend

            current["mc_assumption_proposals"], current["mc_range_review"] = recommend(
                current, store, EngineeringProvider()
            )
            current["results"] = run(report, current["description"], current["plan"])
            current["assumption_register"] = register(
                current["plan"], current["assumptions"]
            )
            current["status"] = (
                "Engineering draft prepared; review ranges before simulation"
            )
        except Exception as exc:  # noqa: BLE001 -- persist independent draft failure
            current["error"] = str(exc)[:1000]
        finally:
            current["running"] = False
            store.put(current, current["revision"])
            lock.release()

    try:
        executor.submit(task)
    except Exception:
        lock.release()
        raise
    return {
        "id": draft["id"],
        "notice": "Independent engineering draft; approved baseline untouched. No external research is invoked.",
    }


@app.get("/api/assessments/{key}/monte-carlo/jobs/{job_id}/audit")
def monte_audit(key: str, job_id: str):
    from backend.scenarios_and_uncertainty.monte_carlo.service import get_results

    result = get_results(store, key, job_id)
    return {
        "audit": result["audit"],
        "input_hash": result["input_hash"],
        "baseline_revision": result["baseline_revision"],
        "baseline_id": result["baseline_id"],
    }


@app.post("/api/assessments/{key}/monte-carlo/preflight")
def monte_preflight(key: str, settings: MonteCarloSettings):
    from backend.scenarios_and_uncertainty.monte_carlo.service import preflight

    return preflight(require_stage_output(key, "financial"), settings)


@app.get("/api/catalogue/equipment-knowledge")
def equipment_knowledge():
    from backend.equipment_resolution.knowledge import library

    return library()


@app.get("/api/assessments/{key}/equipment-resolution")
def equipment_resolution(key: str):
    from backend.equipment_resolution.review import review

    state = store.get(key)
    report = (
        state.get("scoped_report")
        or state.get("effective_report")
        or state["parsed"]["report"]
    )
    return review(report, state["plan"], state.get("results"))


@app.get("/api/assessments/{key}/equipment-conversion")
def equipment_conversion_context(
    key: str, equipment_key: str, model_id: str | None = None
):
    from backend.equipment_costing.unit_conversion.bridges.service import describe

    state = store.get(key)
    report = state.get("effective_report") or state.get("parsed", {}).get("report", {})
    try:
        return describe(report, equipment_key, model_id)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


class ConversionPreview(BaseModel):
    equipment_key: str
    specification: dict


@app.post("/api/assessments/{key}/equipment-conversion/preview")
def equipment_conversion_preview(key: str, request: ConversionPreview):
    from backend.equipment_costing.unit_conversion.bridges.service import evaluate

    state = store.get(key)
    report = state.get("effective_report") or state.get("parsed", {}).get("report", {})
    try:
        return evaluate(report, request.equipment_key, request.specification)
    except (ValueError, TypeError, KeyError) as exc:
        raise HTTPException(422, str(exc)) from exc
