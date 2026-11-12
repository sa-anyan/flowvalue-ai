"""Charlie AI run (11 Nov): AI failures must show the sanitized provider message.

Matching recorded only "Equipment matching batch unavailable: RevenueAIError";
the real cause (an invalid key, a certificate error) was lost. RevenueAIError
messages are built by our provider from fixed text and status codes, so they
are safe to show. Any other exception may carry provider payloads, so only its
type is kept. Keys are redacted even if one ever reached a message.
"""

from unittest.mock import patch

import pytest

from backend.revenue.advisor import RevenueAIError, safe_ai_reason
from backend.tests.test_equipment_matching import run as run_matching
from backend.tests.test_isolated_stages import study  # noqa: F401 -- fixture
from backend.blocks.execution import run_stage

UNAUTHORISED = "OpenAI HTTP 401: invalid_api_key"


class Unauthorised:
    model = "fake"

    def generate(self, **kwargs):
        raise RevenueAIError(UNAUTHORISED)


class LeakyFailure:
    model = "fake"

    def generate(self, **kwargs):
        raise ValueError('response body {"secret": "do-not-show"}')


def test_safe_reason_keeps_provider_message_only_for_sanitized_errors():
    assert safe_ai_reason(RevenueAIError(UNAUTHORISED)) == (
        "RevenueAIError: " + UNAUTHORISED
    )
    assert safe_ai_reason(ValueError("raw body sk-abc")) == "ValueError"
    leaked = safe_ai_reason(RevenueAIError("bad key sk-proj-AbC123_xyz-987 used"))
    assert "sk-proj" not in leaked and "[redacted]" in leaked
    assert len(safe_ai_reason(RevenueAIError("x" * 1000))) <= 320


def test_matching_batch_carries_provider_message(tmp_path):
    result = run_matching(tmp_path, Unauthorised())
    batch = result["batches"][0]
    assert batch["status"] == "unavailable"
    assert batch["reason"] == "RevenueAIError: " + UNAUTHORISED


def test_matching_batch_never_shows_unsanitized_messages(tmp_path):
    batch = run_matching(tmp_path, LeakyFailure())["batches"][0]
    assert batch["reason"] == "ValueError"


def test_equipment_stage_issue_carries_provider_message(tmp_path):
    from types import SimpleNamespace
    from backend.blocks.equipment.runner import prepare

    result = run_matching(tmp_path, Unauthorised())
    ctx = SimpleNamespace(
        plan={"equipment": []},
        report={"entities": []},
        state={"process_description": "test"},
        store=None,
        provider=None,
        use_ai=True,
    )
    with patch(
        "backend.blocks.equipment.runner.match_report", return_value=result
    ), patch(
        "backend.equipment_costing.unit_conversion.bridges.automatic.resolve",
        side_effect=lambda report, plan, *a, **k: (plan, []),
    ):
        issues = prepare(ctx)[3]
    assert (
        "Equipment matching batch unavailable: RevenueAIError: " + UNAUTHORISED
        in issues
    )


def test_engineering_review_region_failure_carries_provider_message(study):
    store, key = study
    state = run_stage(
        store, key, "engineering_data", use_ai=True, provider=Unauthorised()
    )
    notes = state["engineering_review"]["scope_notes"]
    assert any(UNAUTHORISED in note for note in notes)
    failed = [b for b in state["ai"]["review"]["batches"] if b["status"] != "reviewed"]
    assert failed and all(
        b["reason"] == "RevenueAIError: " + UNAUTHORISED for b in failed
    )


def test_engineering_review_unavailable_carries_provider_message(study):
    store, key = study
    with patch(
        "backend.orchestration.provider.EngineeringProvider",
        side_effect=RevenueAIError(UNAUTHORISED),
    ):
        state = run_stage(store, key, "engineering_data", use_ai=True)
    assert state["ai"]["status"] == "review_unavailable"
    assert UNAUTHORISED in state["ai"]["notice"]


def test_equipment_input_resolution_audit_carries_provider_message(tmp_path):
    from backend.equipment_costing.unit_conversion.bridges.automatic import resolve
    from backend.orchestration.store import Store
    from backend.tests.test_automatic_equipment_inputs import REPORT, selected

    _, audit = resolve(
        REPORT, {"equipment": [selected()]}, "", Store(tmp_path / "r.db"),
        Unauthorised(), True,
    )
    unavailable = [a for a in audit if a["status"] == "ai_unavailable"]
    assert unavailable
    assert all(a["reason"] == "RevenueAIError: " + UNAUTHORISED for a in unavailable)
