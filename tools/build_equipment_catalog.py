"""Build the shipped read-only SQLite names catalog from its reviewable source seed."""

import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "backend/app/data"


def build():
    seed = json.loads((DATA / "equipment_catalog.json").read_text())
    target = DATA / "equipment_catalog.sqlite3"
    target.unlink(missing_ok=True)
    with sqlite3.connect(target) as db:
        db.executescript("""
            CREATE TABLE metadata (version TEXT NOT NULL, source_json TEXT NOT NULL);
            CREATE TABLE equipment (id TEXT PRIMARY KEY, name TEXT NOT NULL,
              family TEXT NOT NULL, pdf_page INTEGER NOT NULL, printed_page INTEGER NOT NULL,
              kind TEXT NOT NULL, cost_method_status TEXT NOT NULL);
            CREATE TABLE sources (id TEXT PRIMARY KEY, source_json TEXT NOT NULL);
            CREATE TABLE equipment_sources (equipment_id TEXT NOT NULL REFERENCES equipment(id),
              source_id TEXT NOT NULL REFERENCES sources(id), pdf_page INTEGER NOT NULL,
              printed_page INTEGER NOT NULL, PRIMARY KEY(equipment_id, source_id));
            CREATE TABLE aliases (equipment_id TEXT NOT NULL REFERENCES equipment(id),
              alias TEXT NOT NULL, PRIMARY KEY(equipment_id, alias));
        """)
        db.execute(
            "INSERT INTO metadata VALUES (?, ?)",
            (seed["version"], json.dumps(seed["source"])),
        )
        db.executemany(
            "INSERT INTO sources VALUES (?, ?)",
            [(src["id"], json.dumps(src)) for src in seed["sources"]],
        )
        for item in seed["equipment"]:
            db.execute(
                "INSERT INTO equipment VALUES (?, ?, ?, ?, ?, ?, ?)",
                tuple(
                    item[k]
                    for k in (
                        "id",
                        "name",
                        "family",
                        "pdf_page",
                        "printed_page",
                        "kind",
                        "cost_method_status",
                    )
                ),
            )
            db.executemany(
                "INSERT INTO equipment_sources VALUES (?, ?, ?, ?)",
                [
                    (item["id"], ref["source_id"], ref["pdf_page"], ref["printed_page"])
                    for ref in item["source_refs"]
                ],
            )
            db.executemany(
                "INSERT INTO aliases VALUES (?, ?)",
                [(item["id"], a) for a in item["aliases"]],
            )
    print(f"{len(seed['equipment'])} chart groups → {target}")


if __name__ == "__main__":
    build()
