"""Research pending terms only when the user explicitly stated the income source."""

import copy
import pytest
from backend.tests.test_analyst_workflow import ResearchTests
from backend.orchestration.deep_research import research_draft


def test_research_explicit_pending_source_keeps_plan_unchanged():
    state = ResearchTests().state()
    state["revenue_description"] = "We charge for wastewater treatment."
    state["plan"]["operating_economics"] = {
        "sales": [],
        "commercial_lines": [],
        "pending_inputs": [
            {
                "id": "fee",
                "name": "Treatment fee",
                "category": "processing_services",
                "context_quote": "charge for wastewater treatment",
            }
        ],
    }
    before = copy.deepcopy(state)
    result = research_draft(state, "market", "fee", ResearchTests().provider())
    assert result["target_id"] == "fee"
    assert result["plan_changed"] is False
    assert state == before


def test_pending_opportunity_without_user_intent_cannot_trigger_research():
    state = ResearchTests().state()
    state["revenue_description"] = "We sell protein."
    state["plan"]["operating_economics"] = {
        "pending_inputs": [
            {"id": "fee", "context_quote": "We charge for wastewater treatment"}
        ]
    }
    with pytest.raises(ValueError):
        research_draft(state, "market", "fee", ResearchTests().provider())
