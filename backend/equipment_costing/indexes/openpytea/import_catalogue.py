"""Re-import the pinned local snapshot only; idempotent, no catalogue auto-updates.

Usage: python -m backend.equipment_costing.indexes.openpytea.import_catalogue SOURCE_DIR
Download the four pinned files using URLs in sources.json first. No network at runtime.
"""

import hashlib, json, sys
from pathlib import Path
from .registry import ROOT, catalogue
from .audit import audit


def import_snapshot(folder):
    source = Path(folder)
    manifest = json.loads((ROOT / "sources.json").read_text(encoding="utf-8"))
    destinations = {
        "LICENSE": "LICENSE_NOTICE.md",
        "cost_correlations.csv": "correlations.csv",
        "cepci_values.csv": "upstream_cost_indices.csv",
    }
    # Validate ALL before writing any; do not replace local Garrett/custom data.
    for name, expected in manifest["files"].items():
        if hashlib.sha256((source / name).read_bytes()).hexdigest() != expected:
            raise ValueError("Pinned-source hash mismatch: " + name)
    changed = []
    for name, destination in destinations.items():
        content = (source / name).read_bytes()
        target = ROOT / destination
        if not target.exists() or target.read_bytes() != content:
            target.write_bytes(content)
            changed.append(destination)
    catalogue.cache_clear()
    result = audit()
    (ROOT / "catalogue_audit.json").write_text(json.dumps(result, indent=2) + "\n")
    return changed, result["counts"]


if __name__ == "__main__":
    print(import_snapshot(sys.argv[1]))
