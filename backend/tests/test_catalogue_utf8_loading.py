"""B04: packaged catalogues load identically on non-UTF-8 hosts (e.g. Windows CP1252).

Garrett, OpenPyTEA, currency and cost-index data are UTF-8 JSON. Reading them
with the platform default encoding garbled labels such as "ft²" on Windows, so
exact catalogue keys no longer matched and valid equipment went unpriced.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

PROBE = r"""
import json
from backend.equipment_costing.indexes.garrett.integrated import _read
from backend.equipment_costing.indexes.garrett.installation import _policies
from backend.currency_conversion.currency_converter import rate_snapshot
from backend.equipment_costing.cost_to_future.cost_translation import catalogue
print(json.dumps({
    "garrett": _read("review_curves.json"),
    "installation": _policies(),
    "rates": rate_snapshot(),
    "indexes": catalogue(),
}, ensure_ascii=True, sort_keys=True))
"""


def load(env_overrides):
    env = {**os.environ, **env_overrides}
    result = subprocess.run(
        [sys.executable, "-c", PROBE],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return json.loads(result.stdout)


def test_garrett_source_contains_non_ascii_labels():
    raw = (ROOT / "backend/equipment_costing/indexes/garrett/data/review_curves.json")
    assert "²" in raw.read_bytes().decode("utf-8")


def test_catalogues_load_identically_under_a_non_utf8_locale():
    utf8 = load({"PYTHONUTF8": "1"})
    legacy = load({"PYTHONUTF8": "0", "LC_ALL": "en_US.ISO8859-1", "LANG": "en_US.ISO8859-1"})
    assert legacy == utf8
    assert "²" in json.dumps(legacy["garrett"], ensure_ascii=False)


def test_no_backend_text_read_relies_on_platform_encoding():
    offenders = [
        f"{path.relative_to(ROOT)}:{n}"
        for path in (ROOT / "backend").rglob("*.py")
        if "tests" not in path.parts
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if ".read_text()" in line
    ]
    assert offenders == []
