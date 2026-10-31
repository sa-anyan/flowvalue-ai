"""Local private SQLite assessment snapshots; named versions never overwrite baselines."""

import hashlib
import json
import os
import sqlite3
import uuid
from pathlib import Path


def dump(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.db() as db:
            db.executescript("""CREATE TABLE IF NOT EXISTS assessments
                (id TEXT PRIMARY KEY, revision INTEGER, state TEXT, workbook BLOB);
                CREATE TABLE IF NOT EXISTS versions
                (id TEXT PRIMARY KEY, assessment_id TEXT, name TEXT, state TEXT);
                CREATE TABLE IF NOT EXISTS ai_cache (key TEXT PRIMARY KEY, value TEXT);""")
        os.chmod(self.path, 0o600)

    def db(self):
        return sqlite3.connect(self.path, timeout=10)

    def create(self, state, workbook):
        key = uuid.uuid4().hex
        state = dict(state, id=key, revision=0)
        with self.db() as db:
            db.execute(
                "INSERT INTO assessments VALUES (?,?,?,?)",
                (key, 0, dump(state), workbook),
            )
        return state

    def get(self, key):
        with self.db() as db:
            row = db.execute(
                "SELECT state FROM assessments WHERE id=?", (key,)
            ).fetchone()
        if not row:
            raise KeyError("Assessment not found")
        return json.loads(row[0])

    def put(self, state, expected):
        state = dict(state, revision=expected + 1)
        with self.db() as db:
            cursor = db.execute(
                "UPDATE assessments SET revision=?, state=? WHERE id=? AND revision=?",
                (expected + 1, dump(state), state["id"], expected),
            )
            if cursor.rowcount != 1:
                raise ValueError("Assessment changed; reload before editing")
        return state

    def version(self, key, name):
        if not name.strip() or len(name) > 120:
            raise ValueError("Name the version (up to 120 characters)")
        state = self.get(key)
        if state.get("running"):
            raise ValueError("Wait for the calculation to finish")
        version_id = uuid.uuid4().hex
        with self.db() as db:
            db.execute(
                "INSERT INTO versions VALUES (?,?,?,?)",
                (version_id, key, name, dump(state)),
            )
        return version_id

    def versions(self, key):
        with self.db() as db:
            return [
                {"id": r[0], "name": r[1]}
                for r in db.execute(
                    "SELECT id,name FROM versions WHERE assessment_id=? ORDER BY rowid",
                    (key,),
                )
            ]

    def load(self, version):
        with self.db() as db:
            row = db.execute(
                "SELECT assessment_id,state FROM versions WHERE id=?", (version,)
            ).fetchone()
            if not row:
                raise KeyError("Version not found")
            content = db.execute(
                "SELECT workbook FROM assessments WHERE id=?", (row[0],)
            ).fetchone()[0]
        state = json.loads(row[1])
        state["parent_version"] = version
        state["running"] = False
        return self.create(state, content)

    def cached(self, context, compute):
        key = hashlib.sha256(dump(context).encode()).hexdigest()
        with self.db() as db:
            row = db.execute(
                "SELECT value FROM ai_cache WHERE key=?", (key,)
            ).fetchone()
        if row:
            return json.loads(row[0]), True
        value = compute()
        with self.db() as db:
            db.execute(
                "INSERT OR REPLACE INTO ai_cache VALUES (?,?)", (key, dump(value))
            )
        return value, False

    def all_versions(self):
        with self.db() as db:
            return [
                {"id": r[0], "name": r[1], "assessment_id": r[2]}
                for r in db.execute(
                    "SELECT id,name,assessment_id FROM versions ORDER BY rowid DESC"
                )
            ]
