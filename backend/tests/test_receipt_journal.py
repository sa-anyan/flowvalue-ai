from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import sqlite3
import subprocess
import sys
from threading import Barrier

import pytest

from backend.orchestration.calculation_receipts import (
    CalculationReceipt, CalculationScope, evaluate_lifecycle, semantic_digest,
)
from backend.orchestration.store import Store
from backend.tests.receipt_journal_fixture import ReceiptConflict, ReceiptJournal, RevisionConflict
from backend.tests.test_calculation_receipts import NOW, SCOPE, inputs, receipt


def attempt(receipt_id, result, *, scope=SCOPE, outcome="ready", offset=0):
    return receipt("equipment", scope=scope, receipt_id=receipt_id, outcome=outcome,
                   executed_at=NOW + timedelta(seconds=offset),
                   output_digest=semantic_digest(result) if result is not None else None)


@pytest.fixture
def journal(tmp_path):
    return ReceiptJournal(tmp_path / "isolated-journal.sqlite")


def test_replay_is_exact_and_does_not_advance_revision(journal):
    output = {"cost": "10.00"}
    first = attempt("one", output)
    assert journal.append(first, output, expected_revision=0) == (1, False)
    second = attempt("two", {"cost": "20"})
    assert journal.append(second, {"cost": "20"}, expected_revision=1) == (2, False)
    before = journal.history(SCOPE)
    assert journal.append(first, output, expected_revision=0) == (1, True)
    with pytest.raises(ReceiptConflict, match="immutable"):
        journal.append(attempt("one", {"cost": "30"}), {"cost": "30"}, expected_revision=2)
    with pytest.raises(ValueError, match="does not match"):
        journal.append(first, {"cost": "30"}, expected_revision=2)
    assert journal.history(SCOPE) == before
    assert journal.append(attempt("three", output), output, expected_revision=2) == (3, False)


def test_concurrent_completions_use_revision_and_commit_order(journal):
    barrier = Barrier(2)
    payloads = [{"cost": "12"}, {"cost": "13"}]
    runs = [attempt(f"run-{i}", payloads[i], offset=i) for i in range(2)]

    def complete(i):
        barrier.wait(timeout=10)
        try:
            return journal.append(runs[i], payloads[i], expected_revision=0)
        except RevisionConflict:
            return None

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(complete, range(2)))
    assert sorted(result for result in results if result is not None) == [(1, False)]
    loser = results.index(None)
    winner = 1 - loser
    assert journal.history(SCOPE) == ((1, runs[winner].model_dump(mode="json"), payloads[winner]),)
    # Explicit fixture resubmission after seeing revision 1, not an automatic retry policy.
    assert journal.append(runs[loser], payloads[loser], expected_revision=1) == (2, False)
    assert [item[1]["receipt_id"] for item in journal.history(SCOPE)] == [runs[winner].receipt_id, runs[loser].receipt_id]
    earlier = attempt("earlier-clock", {"cost": "14"}, offset=-30)
    assert journal.append(earlier, {"cost": "14"}, expected_revision=2) == (3, False)
    assert journal.history(SCOPE)[-1][1]["receipt_id"] == "earlier-clock"


def test_sql_failure_after_insert_rolls_back_result_and_revision(journal):
    output = {"cost": "10"}
    journal.append(attempt("prior", output), output, expected_revision=0)
    before = journal.history(SCOPE)
    with journal.connect() as db:
        db.execute("""
            CREATE TRIGGER fail_revision BEFORE UPDATE ON scopes
            BEGIN SELECT RAISE(ABORT, 'injected write failure'); END
        """)
    with pytest.raises(sqlite3.IntegrityError, match="injected write failure"):
        journal.append(attempt("failed-write", {"cost": "20"}), {"cost": "20"}, expected_revision=1)
    assert journal.history(SCOPE) == before
    with journal.connect() as db:
        db.execute("DROP TRIGGER fail_revision")
    assert journal.append(attempt("next", output), output, expected_revision=1) == (2, False)


def test_process_exit_after_insert_does_not_publish_partial_transaction(journal):
    output = {"cost": "10"}
    journal.append(attempt("prior", output), output, expected_revision=0)
    before = journal.history(SCOPE)
    code = """
import os
import sys
from contextlib import contextmanager
from backend.tests.receipt_journal_fixture import ReceiptJournal
from backend.tests.test_receipt_journal import attempt

class InterruptedJournal(ReceiptJournal):
    @contextmanager
    def connect(self):
        with super().connect() as db:
            def interrupt(statement):
                if statement.startswith("UPDATE scopes"):
                    os._exit(17)
            db.set_trace_callback(interrupt)
            yield db

journal = InterruptedJournal.__new__(InterruptedJournal)
journal.path = sys.argv[1]
result = {"cost": "20"}
journal.append(attempt("interrupted", result), result, expected_revision=1)
"""
    process = subprocess.run([sys.executable, "-c", code, str(journal.path)], timeout=30)
    assert process.returncode == 17
    assert journal.history(SCOPE) == before
    assert journal.append(attempt("next", output), output, expected_revision=1) == (2, False)


@pytest.mark.parametrize("outcome", ["failed", "partial"])
def test_previous_complete_payload_remains_retrievable(journal, outcome):
    original = {"cost": "25"}
    complete = attempt("complete", original)
    journal.append(complete, original, expected_revision=0)
    result = {"cost": "8"} if outcome == "partial" else None
    latest = attempt("latest", result, outcome=outcome)
    journal.append(latest, result, expected_revision=1)
    history = journal.history(SCOPE)
    receipts = tuple(CalculationReceipt.model_validate(row[1]) for row in history)
    view = evaluate_lifecycle(SCOPE, {"equipment": ()}, receipts, inputs(complete))["equipment"]
    assert view.latest_attempt_id == "latest"
    assert view.active_receipt_id == ("latest" if outcome == "partial" else "complete")
    assert view.previous_complete_receipt_id == ("complete" if outcome == "partial" else None)
    assert history[0][2] == original


def test_scope_isolation_and_named_version_lineage(journal, tmp_path):
    store = Store(tmp_path / "isolated-snapshot.sqlite")
    saved = store.create({"results": {"cost": "11"}}, b"fixture")
    original = CalculationScope(assessment_id=saved["id"])
    other = CalculationScope(assessment_id="other")
    scenario = CalculationScope(assessment_id=saved["id"], scenario_id="trial")
    scopes = (original, other, scenario)
    for index, scope in enumerate(scopes, 1):
        output = {"cost": str(index)}
        assert journal.append(attempt("shared-id", output, scope=scope), output, expected_revision=0) == (index, False)
    assert [journal.history(scope)[0][2] for scope in scopes] == [{"cost": "1"}, {"cost": "2"}, {"cost": "3"}]
    before = journal.history(original)
    # Fixture metadata on a temporary Store only. No production writer or schema is changed.
    saved["calculation_receipts"] = [before[0][1]]
    saved = store.put(saved, saved["revision"])
    version = store.version(saved["id"], "Original scope")
    with store.db() as db:
        snapshot = db.execute("SELECT state FROM versions WHERE id=?", (version,)).fetchone()[0]
    reopened = store.load(version)
    assert reopened["calculation_receipts"] == saved["calculation_receipts"]
    assert reopened["results"] == saved["results"]
    assert journal.history(CalculationScope(assessment_id=reopened["id"])) == ()
    assert journal.history(original) == before
    with store.db() as db:
        assert db.execute("SELECT state FROM versions WHERE id=?", (version,)).fetchone()[0] == snapshot
