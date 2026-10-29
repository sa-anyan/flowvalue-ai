"""Reproducible parser benchmark. Run with backend venv from backend/.

No workbook mutation, network, AI or macro execution. Output contains timings
and counts, never user workbook content. Uses the real constrained worker.
"""

import argparse
import cProfile
import inspect
import io
import json
import os
import pstats
import statistics
import subprocess
import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory


def summary(values):
    ordered = sorted(values)
    return {
        "median_s": statistics.median(ordered),
        "p95_s": ordered[max(0, int(len(ordered) * 0.95 + 0.999) - 1)],
        "worst_s": max(ordered),
        "runs_s": values,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("workbook", type=Path)
    ap.add_argument("--runs", type=int, default=20)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    content = args.workbook.read_bytes()
    from app.parsers.workbook_pipeline import parse_workbook

    profile = cProfile.Profile()
    profile.enable()
    report = parse_workbook(content, args.workbook.name)
    json.dumps({"report": report.model_dump(mode="json")}, allow_nan=False)
    profile.disable()
    stream = io.StringIO()
    pstats.Stats(profile, stream=stream).strip_dirs().sort_stats(
        "cumulative"
    ).print_stats(25)
    warm = []
    stages = {}
    accepts_metrics = "metrics" in inspect.signature(parse_workbook).parameters
    for _ in range(args.runs):
        start = time.perf_counter()
        metrics = {}
        report = parse_workbook(
            content,
            args.workbook.name,
            **({"metrics": metrics} if accepts_metrics else {}),
        )
        serialize_start = time.perf_counter()
        json.dumps({"report": report.model_dump(mode="json")}, allow_nan=False)
        metrics["serialize_s"] = time.perf_counter() - serialize_start
        for name, elapsed in metrics.items():
            stages.setdefault(name, []).append(elapsed)
        warm.append(time.perf_counter() - start)
    print("Warm-process runs finished", flush=True)
    wrapper = "import runpy,resource,sys;sys.argv=['app.parsers.excel_worker',*sys.argv[1:]];runpy.run_module('app.parsers.excel_worker',run_name='__main__');print('RSS:'+str(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss),file=sys.stderr)"
    env = {
        k: v
        for k, v in os.environ.items()
        if k in ("PATH", "PYTHONPATH", "SYSTEMROOT", "LANG")
    }
    env.update(OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1")
    worker, peaks = [], []
    cold = None
    for index in range(args.runs + 1):
        start = time.perf_counter()
        with TemporaryDirectory(prefix="flowvalue-benchmark-") as folder:
            upload = Path(folder) / "upload"
            upload.write_bytes(content)
            proc = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    wrapper,
                    str(upload),
                    args.workbook.name,
                    "excel",
                ],
                capture_output=True,
                env=env,
                timeout=25,
                check=True,
            )
        result = json.loads(proc.stdout)
        if "report" not in result:
            raise RuntimeError(result)
        # Include deserialization and canonical response validation in wall time.
        from app.parsers.balance.models import BalanceReport

        BalanceReport.model_validate(result["report"])
        elapsed = time.perf_counter() - start
        if index == 0:
            cold = elapsed
        else:
            worker.append(elapsed)
        rss = next(
            line[4:]
            for line in proc.stderr.decode().splitlines()
            if line.startswith("RSS:")
        )
        peaks.append(int(rss) / (1024 * 1024 if sys.platform == "darwin" else 1024))
    output = {
        "workbook": args.workbook.name,
        "bytes": len(content),
        "platform": sys.platform,
        "python": sys.version,
        "warm_process": summary(warm),
        "fresh_worker": summary(worker),
        "stages": {name: summary(values) for name, values in stages.items()},
        "first_fresh_worker_s": cold,
        "peak_worker_rss_mib": max(peaks),
        "stream_count": sum(e.kind == "material" for e in report.entities),
        "equipment_count": sum(e.kind == "equipment" for e in report.entities),
        "profile": stream.getvalue(),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2))
    print(
        json.dumps(
            {
                k: v
                for k, v in output.items()
                if k not in ("profile", "warm_process", "fresh_worker")
            },
            indent=2,
        )
    )
    print(
        "Warm median",
        output["warm_process"]["median_s"],
        "worker median",
        output["fresh_worker"]["median_s"],
        "worker P95",
        output["fresh_worker"]["p95_s"],
    )


if __name__ == "__main__":
    main()
