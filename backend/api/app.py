"""Local assessment API. Bind to loopback; cloud authentication is not restored here."""

import os
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel, ConfigDict, Field

from backend.equipment_costing.registry import list_equipment_models
from backend.orchestration.pipeline import contracts
from backend.orchestration.service import compare, edit, execute, new_assessment
from backend.orchestration.store import Store

app = FastAPI(title="FlowValue Assessment Orchestration")
store = Store(
    os.environ.get("FLOWVALUE_ASSESSMENT_DB", "outputs/assessments/local.sqlite3")
)
CLOUD = os.environ.get("FLOWVALUE_CLOUD", "false").lower() == "true"
if CLOUD:
    from backend.cloud.runtime import WorkspaceProxy, ContextExecutor

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


class Rerun(BaseModel):
    use_ai: bool = False


class NamedVersion(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class ResearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: int
    kind: str
    target_id: str = Field(min_length=1, max_length=200)
    consent: bool


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
    if not lock.acquire(blocking=False):
        raise HTTPException(
            409, "Another assessment is running; try again when it finishes"
        )

    def work():
        try:
            execute(store, key, **kwargs)
        finally:
            lock.release()

    executor.submit(work)


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
                state, request.kind, request.target_id, EngineeringProvider()
            )
            current = store.get(key)
            current.setdefault("research_drafts", []).append(result)
            current["research_job"] = dict(current["research_job"], status="completed")
        except Exception as exc:  # noqa: BLE001 -- retain existing model on research outage
            current = store.get(key)
            current["research_job"] = dict(
                current["research_job"],
                status="failed",
                notice=str(exc)[:300]
                if isinstance(exc, (ValueError, RevenueAIError))
                else type(exc).__name__,
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
):
    content = await file.read(4 * 1024**2 + 1)
    if not content or len(content) > 4 * 1024**2:
        raise HTTPException(413, "Choose a workbook up to 4 MiB")
    if len(description) + len(revenue_description) > 12000:
        raise HTTPException(422, "Description exceeds 12,000 characters")
    name = Path(file.filename or "workbook").name
    if Path(name).suffix.lower() not in {".xlsx", ".xls", ".xlsm"}:
        raise HTTPException(422, "Choose .xlsx, .xls or .xlsm")
    if lock.locked():
        raise HTTPException(409, "Another assessment is running")
    state = new_assessment(store, content, name, description, revenue_description)
    submit(state["id"], content=content, use_ai=use_ai)
    return {"id": state["id"]}


@app.get("/api/assessments/{key}")
def get(key: str):
    return store.get(key)


@app.patch("/api/assessments/{key}")
def patch(key: str, change: Edit):
    return edit(
        store, key, change.revision, change.section, change.value, change.rationale
    )


@app.post("/api/assessments/{key}/run", status_code=202)
def rerun(key: str, options: Rerun):
    state = store.get(key)
    if state.get("running"):
        raise HTTPException(409, "Assessment already running")
    state["running"] = True
    store.put(state, state["revision"])
    try:
        submit(key, use_ai=options.use_ai)
    except Exception:
        state = store.get(key)
        state["running"] = False
        store.put(state, state["revision"])
        raise
    return {"id": key}


@app.post("/api/assessments/{key}/versions")
def save(key: str, version: NamedVersion):
    return {"id": store.version(key, version.name)}


@app.get("/api/assessments/{key}/versions")
def versions(key: str):
    store.get(key)
    return store.versions(key)


@app.post("/api/versions/{version}/open")
def reopen(version: str):
    return store.load(version)


@app.get("/api/assessments/{key}/compare/{other}")
def comparison(key: str, other: str):
    return compare(store.get(key), store.get(other))


@app.get("/api/catalogue")
def catalogue():
    return {
        "equipment": [
            {k: m[k] for k in ("id", "equipment", "configuration", "size_unit")}
            for m in list_equipment_models()
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
            if int(length) > 5 * 1024**2:
                return JSONResponse(
                    status_code=413, content={"detail": "Request exceeds 5 MiB"}
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
        if int(length) > 5 * 1024**2:
            return JSONResponse(
                status_code=413, content={"detail": "Request exceeds 5 MiB"}
            )
    return await call_next(request)


@app.get("/api/versions")
def all_versions():
    return store.all_versions()


@app.get("/api/assessments/{key}/report")
def study_report(key: str):
    from fastapi.responses import HTMLResponse

    from backend.dashboard_reporting.study_report import render_study

    state = store.get(key)
    if state.get("running"):
        raise HTTPException(409, "Wait for this study calculation to finish")
    return HTMLResponse(render_study(state), headers={"Cache-Control": "no-store"})


@app.get("/api/assessments/{key}/snapshot")
def study_snapshot(key: str):
    import json

    from fastapi.responses import Response

    state = store.get(key)
    if state.get("running"):
        raise HTTPException(409, "Wait for this study calculation to finish")
    return Response(
        json.dumps(state, indent=2, allow_nan=False),
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
    if (
        not (baseline.get("results") or {})
        .get("stages", {})
        .get("financial", {})
        .get("result")
    ):
        raise HTTPException(
            422,
            "A calculated baseline is required for this commercial strategy scenario",
        )
    if not lock.acquire(blocking=False):
        raise HTTPException(409, "Another assessment is running")
    try:
        content = store.workbook(key)
        draft = copy.deepcopy(baseline)
        draft.update(
            description=options.description,
            process_description=options.process_description
            if options.process_description is not None
            else options.description,
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
