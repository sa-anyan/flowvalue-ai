"""Bounded upload parsing in a killable worker, with bounded concurrency."""

import asyncio
import json
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi import HTTPException

from .balance.models import BalanceReport
from .balance.workbook import safe_filename

slots = asyncio.Semaphore(1)


async def parse_upload(content, filename, source="excel"):
    if source not in ("excel", "aspen-hysys"):
        raise HTTPException(422, "Unsupported Excel import source.")
    try:
        await asyncio.wait_for(slots.acquire(), timeout=1)
    except TimeoutError:
        raise HTTPException(429, "Workbook parser is busy. Retry shortly.")
    try:
        with TemporaryDirectory(prefix="flowvalue-balance-") as folder:
            path = Path(folder) / "upload"
            path.write_bytes(content)
            proc = await asyncio.create_subprocess_exec(
                sys.executable,
                "-m",
                "app.parsers.excel_worker",
                str(path),
                safe_filename(filename),
                source,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
                env={
                    **{
                        k: v
                        for k, v in os.environ.items()
                        if k in ("PATH", "PYTHONPATH", "SYSTEMROOT", "LANG")
                    },
                    "OPENBLAS_NUM_THREADS": "1",
                    "OMP_NUM_THREADS": "1",
                },
            )
            try:
                out, _ = await asyncio.wait_for(proc.communicate(), timeout=25)
            except (TimeoutError, asyncio.CancelledError):
                if proc.returncode is None:
                    proc.kill()
                await proc.wait()
                raise HTTPException(
                    422,
                    "Workbook exceeded the safe parsing time/resource limit; split it into smaller engineering scopes.",
                )
            if proc.returncode != 0 or len(out) > 8_000_000:
                raise HTTPException(
                    422, "Workbook exceeded parser resource limits or is malformed."
                )
            try:
                result = json.loads(out)
            except ValueError:
                raise HTTPException(422, "Workbook could not be read safely.")
            if "error" in result:
                raise HTTPException(422, result["error"])
            try:
                return BalanceReport.model_validate(result["report"])
            except ValueError as exc:
                raise HTTPException(
                    422,
                    "Parsed workbook exceeded structured record limits or contained unsupported values.",
                ) from exc
    finally:
        slots.release()


class WorkbookRequestLimit:
    """Bound the raw multipart/JSON body before Starlette spools or decodes it."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        limits = {
            "/api/streams/parse/excel": 4 * 1024 * 1024 + 65536,
            "/api/process-description/check": 3 * 1024 * 1024,
            "/api/process-description/review": 3 * 1024 * 1024,
            "/api/equipment/interpret": 3 * 1024 * 1024,
            "/api/equipment/match": 3 * 1024 * 1024,
        }
        limit = (
            limits.get(scope.get("path"))
            if scope.get("type") == "http" and scope.get("method") == "POST"
            else None
        )
        if limit is None:
            return await self.app(scope, receive, send)
        from starlette.responses import JSONResponse

        chunks = []
        total = 0
        headers = dict(scope.get("headers", []))
        try:
            length = int(headers.get(b"content-length", b"0"))
        except ValueError:
            length = 0
        if length > limit:
            return await JSONResponse(
                {"detail": "Engineering request exceeds upload/body limit."},
                status_code=413,
            )(scope, receive, send)
        while True:
            event = await receive()
            if event["type"] == "http.disconnect":
                return
            data = event.get("body", b"")
            total += len(data)
            if total > limit:
                return await JSONResponse(
                    {"detail": "Engineering request exceeds upload/body limit."},
                    status_code=413,
                )(scope, receive, send)
            chunks.append(data)
            if not event.get("more_body", False):
                break

        async def bounded_receive():
            if chunks:
                return {
                    "type": "http.request",
                    "body": chunks.pop(0),
                    "more_body": bool(chunks),
                }
            return await receive()

        await self.app(scope, bounded_receive, send)
