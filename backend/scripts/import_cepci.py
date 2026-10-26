"""Usage: python scripts/import_cepci.py licensed-observation.json

Review source rights and observation before committing the catalog update.
No application endpoint can overwrite indices.
"""

import json
import sys
from pathlib import Path

from app.engine.indices import IndexRecord

record = IndexRecord.model_validate_json(Path(sys.argv[1]).read_text())
path = Path(__file__).resolve().parents[1] / "app/data/cepci.json"
records = json.loads(path.read_text())
# Append-only revisions preserve earlier publications/corrections.
records.append(record.model_dump(mode="json"))
path.write_text(json.dumps(records, indent=2) + "\n")
print(
    f"Appended CEPCI observation {record.period}; review and commit the catalog revision."
)
