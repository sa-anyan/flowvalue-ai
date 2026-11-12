"""Revenue Box is authoritative; draft assumptions cannot enter financial metrics."""

import copy
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from backend.orchestration.codec import plain
from backend.orchestration.pipeline import run
from backend.orchestration.service import new_assessment
from backend.orchestration.store import Store
from backend.revenue.authority import bind, fingerprint, questions, runtime, update
from backend.orchestration.operating_economics import calculate_operating_study
from backend.tests.test_commercial_intent import intent
from backend.tests.test_operating_economics import fixture
from backend.tests.test_revenue_mece import config_line

BOX = "We sell lignin and charge wastewater treatment fees."


def ready():
    report, config, capex = fixture()
    config["sales"][0].update(
        name="Lignin", context_quote="sell lignin", intent_id="sale"
    )
    config["commercial_lines"] = [config_line(config["financial"]["operating_years"])]
    config["commercial_lines"][0].update(
        context_quote="charge wastewater treatment fees", intent_id="fee"
    )
    config["commercial_intent"] = intent(
        [
            ("sale", "product_sales", "sell lignin"),
            ("fee", "processing_services", "charge wastewater treatment fees"),
        ]
    )
    # Both bill the same synthetic stream: the Phase 4 shared-stream review.
    review = {"basis": "Synthetic: product sale and treatment fee are separate payments"}
    config["sales"][0]["shared_stream_review"] = review
    config["commercial_lines"][0]["shared_stream_review"] = dict(review)
    return report, config, capex


def approve(config, report, text=BOX):
    return {
        "text": text,
        "approval": {"fingerprint": fingerprint(config, text, report)},
    }


def test_box_cannot_be_replaced_by_process_description_or_manual_rationale():
    report, config, _ = ready()
    assert "How will" in questions(config, "", report)[0]
    config["intent_source"] = "user_override"
    config["intent_override_reason"] = "sell lignin"
    assert questions(config, "We charge wastewater treatment fees only.", report)
    config["sales"][0]["_approved"] = True
    assert questions(config, "We charge wastewater treatment fees only.", report)


def test_missing_prices_and_source_mappings_ask_instead_of_inventing():
    report, config, _ = ready()
    config["sales"][0]["unit_price"] = None
    config["sales"][0]["stream_key"] = "missing"
    config["commercial_lines"][0]["years"][0]["rate"] = None
    q = questions(config, BOX, report, require_approval=False)
    assert any("selling price" in x for x in q)
    assert any("measured M&E stream" in x for x in q)
    assert any("fee, billing unit" in x for x in q)
    assert config["sales"][0]["unit_price"] is None


@pytest.mark.parametrize("group", ["sales", "commercial_lines", "both"])
def test_one_or_multiple_user_approved_sources_feed_real_finance(group):
    report, config, capex = ready()
    if group != "both":
        config["commercial_lines" if group == "sales" else "sales"] = []
        config["commercial_intent"]["mechanisms"] = [
            m
            for m in config["commercial_intent"]["mechanisms"]
            if m["category"]
            == ("product_sales" if group == "sales" else "processing_services")
        ]
    policy = approve(config, report)
    assert questions(config, BOX, report, approval=policy["approval"]) == []
    config["_revenue_authority"] = runtime(config, policy, report)
    result = calculate_operating_study(report, BOX, config, capex)
    assert not result["financial"].issues
    assert bool(result["revenue"].products) == (group != "commercial_lines")
    assert bool(result["revenue"].commercial) == (group != "sales")


def test_price_schedule_and_workbook_changes_invalidate_approval_but_opex_does_not():
    report, config, _ = ready()
    approval = approve(config, report)["approval"]
    for change in ("price", "schedule", "source"):
        c, r = copy.deepcopy(config), copy.deepcopy(report)
        if change == "price":
            c["sales"][0]["unit_price"] = 20
        if change == "schedule":
            c["operating"]["days_per_year"] = 300
        if change == "source":
            r["entities"][0]["values"][0]["normalized_value"] = 200
        assert questions(c, BOX, r, approval=approval)
    config["labour"][0]["annual_base_salary"] = 40000
    assert not questions(config, BOX, report, approval=approval)


def test_partial_fallback_cannot_send_unapproved_income_to_finance():
    report, config, _ = ready()
    result = run(
        report,
        BOX,
        {
            "equipment": [],
            "capex": {},
            "operating_economics": config,
            "revenue_authority": {"text": BOX, "approval": None},
            "cost_translation": {"enabled": False},
        },
    )
    assert not result["stages"]["revenue"]["result"]["annual"]
    assert not result["stages"]["financial"]["result"]["metrics"]
    assert result["stages"]["opex"]["result"]["known_cash_opex_subtotal"] is not None


def test_only_explicit_server_approval_and_current_revision_are_accepted():
    report, config, _ = ready()
    with tempfile.TemporaryDirectory() as folder:
        store = Store(Path(folder) / "test.sqlite")
        state = new_assessment(
            store,
            b"",
            "synthetic.xlsx",
            "The process also makes oxygen, which is not authorised income.",
            BOX,
        )
        state.update(
            running=False,
            parsed={"report": report},
            plan={"operating_economics": config},
        )
        state = store.put(state, state["revision"])
        saved = update(store, state["id"], state["revision"], approve=True)
        assert saved["revenue_approval"]["origin"] == "explicit_user_approval"
        assert saved["revenue_questions"] == []
        with pytest.raises(ValueError, match="reload"):
            update(store, state["id"], state["revision"], approve=True)
        changed = update(
            store, state["id"], saved["revision"], text="Treatment fees only"
        )
        assert not changed.get("revenue_approval")
        assert changed["results"] is None
        assert changed["revenue_questions"]
        # Editable config cannot forge the server-owned policy.
        changed["plan"]["revenue_authority"] = {
            "text": BOX,
            "approval": saved["revenue_approval"],
        }
        bind(changed)
        assert changed["plan"]["revenue_authority"]["text"] == "Treatment fees only"
        assert changed["plan"]["revenue_authority"]["approval"] is None


def test_saved_historical_outputs_do_not_bypass_live_approval_view():
    from backend.orchestration.current_prices import current_price_view

    report, config, _ = ready()
    saved = {
        "revenue_description": BOX,
        "plan": {"operating_economics": config, "cost_translation": {"enabled": False}},
        "parsed": {"report": report},
        "results": {
            "stages": {"financial": {"result": {"metrics": {"project_npv": 999}}}}
        },
    }
    view = current_price_view(saved)
    assert view["results"]["stages"]["financial"]["result"] is None
    assert (
        saved["results"]["stages"]["financial"]["result"]["metrics"]["project_npv"]
        == 999
    )


def test_uncertainty_plan_cannot_drop_revenue_authority():
    from types import SimpleNamespace
    from backend.scenarios_and_uncertainty.monte_carlo.scenarios import prepare

    report, config, _ = ready()
    state = {
        "revenue_description": BOX,
        "plan": {"equipment": [], "operating_economics": config},
        "parsed": {"report": report},
    }
    settings = SimpleNamespace(operating_years=3, aliases=[], distinct=[])
    result = prepare(state, settings)
    assert result["revenue_authority"] == {"text": BOX, "approval": None}
    assert "revenue_authority" not in state["plan"]


def test_clarification_draft_cannot_be_approved_as_zero_income():
    report, config, _ = ready()
    config.update(
        sales=[],
        commercial_lines=[],
        commercial_intent={
            "status": "needs_clarification",
            "mechanisms": [],
            "questions": ["What treatment fee should we use?"],
        },
    )
    assert "What treatment fee should we use?" in questions(
        config, BOX, report, require_approval=False
    )
