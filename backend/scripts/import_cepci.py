"""Usage: python scripts/import_cepci.py licensed-observation.json

Append a reviewed observation. Internal-only observations stay out of the API.
Do not commit licensed source data without repository distribution rights.
"""

import json
import sys
from pathlib import Path

from app.engine.indices import IndexRecord


def append_observation(source: Path, catalog: Path):
    record = IndexRecord.model_validate_json(source.read_text())
    records = json.loads(catalog.read_text())
    payload = record.model_dump(mode="json")
    if payload in records:
        raise ValueError("Identical observation already exists; import cancelled")
    records.append(payload)
    temporary = catalog.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(records, indent=2) + "\n")
    temporary.replace(catalog)
    return record


if __name__ == "__main__":
    record = append_observation(
        Path(sys.argv[1]), Path(__file__).resolve().parents[1] / "app/data/cepci.json"
    )
    print(
        f"Appended observation {record.period}. Review distribution rights before committing/deploying."
    )
