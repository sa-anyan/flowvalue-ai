from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

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
        raise HTTPException(status_code=422, detail=exc.errors(include_context=False)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
