"""Isolate untrusted Excel decoding from API and secret-bearing AI process."""

import json
import logging
import os
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

from backend.ingestion.limits import MAX_WORKBOOK_BYTES

ROOT = Path(__file__).resolve().parents[2]
logger = logging.getLogger(__name__)


def parse(content, filename):
    if not 0 < len(content) <= MAX_WORKBOOK_BYTES:
        raise ValueError("Choose a workbook up to 20 MiB")
    filename = Path(filename).name
    if Path(filename).suffix.lower() not in {".xlsx", ".xls", ".xlsm"}:
        raise ValueError("Only .xlsx, .xls and .xlsm are supported here")
    with tempfile.TemporaryDirectory(prefix="flowvalue-parse-") as folder:
        path = Path(folder) / ("input" + Path(filename).suffix.lower())
        path.write_bytes(content)
        process = subprocess.run(
            [sys.executable, "-m", "backend.ingestion.worker", str(path), filename],
            cwd=ROOT,
            env={
                k: v
                for k, v in os.environ.items()
                if k.upper() in {"PATH", "SYSTEMROOT", "LANG"}
            },
            capture_output=True,
            timeout=30,
            check=False,
        )
        if len(process.stdout) > 16 * 1024**2:
            raise ValueError("Parsed workbook output exceeds safe limit")
        try:
            result = json.loads(process.stdout)
        except (ValueError, UnicodeError) as exc:
            logger.error("Workbook worker returned invalid output (exit %s): %s",
                         process.returncode, process.stderr.decode("utf-8", errors="replace")[-2000:])
            raise ValueError("Workbook parser process failed; check the backend logs for details") from exc
        if process.returncode or "error" in result:
            raise ValueError(result.get("error", "Workbook worker failed"))
        result["report"]["extracted_on"] = date.today().isoformat()
        return result
