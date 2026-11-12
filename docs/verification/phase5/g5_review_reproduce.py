"""Run the fixed G5 evaluation suite (docs/verification/phase5/benchmark.json).

    python docs/verification/phase5/g5_review_reproduce.py

Each roadmap scenario and acceptance criterion passes only if every listed
test exists and passes. A missing test counts as a failure. Critical
criteria must have zero failures for G5.
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SUITE = json.loads((Path(__file__).parent / "benchmark.json").read_text())


def run(tests):
    proc = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *tests],
                          cwd=ROOT, capture_output=True, text=True)
    lines = proc.stdout.strip().splitlines()
    return {"status": "PASS" if proc.returncode == 0 else "FAIL", "summary": lines[-1] if lines else proc.stderr[-300:]}


def main():
    out = {"suite": SUITE["version"], "scenarios": {}, "acceptance": {}}
    for group in ("scenarios", "acceptance"):
        for name, spec in SUITE[group].items():
            out[group][name] = {**run(spec["tests"]), "critical": spec.get("critical", group == "scenarios")}
    critical_failures = [f"{g}.{n}" for g in ("scenarios", "acceptance") for n, r in out[g].items()
                         if r["critical"] and r["status"] != "PASS"]
    out["critical_failures"] = critical_failures
    out["not_yet_measured"] = SUITE["not_yet_measured"]
    print(json.dumps(out, indent=2))
    return 1 if critical_failures else 0


if __name__ == "__main__":
    sys.exit(main())
