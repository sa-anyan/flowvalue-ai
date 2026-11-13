"""Test-only SQLite receipt append contract. No application store imports this."""

from contextlib import closing, contextmanager
import json
import sqlite3

from backend.orchestration.calculation_receipts import semantic_digest
from backend.orchestration.store import dump


class RevisionConflict(ValueError):
    pass


class ReceiptConflict(ValueError):
    pass


class ReceiptJournal:
    def __init__(self, path):
        self.path = path
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE scopes (scope TEXT PRIMARY KEY, revision INTEGER NOT NULL);
                CREATE TABLE attempts (
                    sequence INTEGER PRIMARY KEY,
                    scope TEXT NOT NULL REFERENCES scopes(scope),
                    receipt_id TEXT NOT NULL,
                    receipt TEXT NOT NULL,
                    result TEXT,
                    UNIQUE(scope, receipt_id)
                );
            """)

    @contextmanager
    def connect(self):
        with closing(sqlite3.connect(self.path, timeout=10)) as db, db:
            db.execute("PRAGMA foreign_keys=ON")
            yield db

    def append(self, receipt, result, *, expected_revision):
        """Return commit sequence and whether the delivery replayed an existing row."""
        scope = dump(receipt.scope.model_dump(mode="json"))
        encoded = dump(receipt.model_dump(mode="json"))
        payload = dump(result) if result is not None else None
        output_digest = semantic_digest(result) if result is not None else None
        if output_digest != receipt.output_digest:
            raise ValueError("Fixture result does not match receipt digest")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute(
                "SELECT sequence, receipt, result FROM attempts WHERE scope=? AND receipt_id=?",
                (scope, receipt.receipt_id),
            ).fetchone()
            if existing is not None:
                if existing[1:] != (encoded, payload):
                    raise ReceiptConflict("Conflicting immutable receipt delivery")
                return existing[0], True
            db.execute("INSERT INTO scopes VALUES (?, 0) ON CONFLICT(scope) DO NOTHING", (scope,))
            appended = db.execute(
                "INSERT INTO attempts(scope, receipt_id, receipt, result) VALUES (?, ?, ?, ?)",
                (scope, receipt.receipt_id, encoded, payload),
            )
            updated = db.execute(
                "UPDATE scopes SET revision=revision+1 WHERE scope=? AND revision=?",
                (scope, expected_revision),
            )
            if updated.rowcount != 1:
                raise RevisionConflict("Scope revision changed")
            return appended.lastrowid, False

    def history(self, scope):
        scope_key = dump(scope.model_dump(mode="json"))
        with self.connect() as db:
            rows = db.execute(
                "SELECT sequence, receipt, result FROM attempts WHERE scope=? ORDER BY sequence",
                (scope_key,),
            ).fetchall()
        return tuple((sequence, json.loads(receipt), json.loads(result) if result is not None else None)
                     for sequence, receipt, result in rows)
