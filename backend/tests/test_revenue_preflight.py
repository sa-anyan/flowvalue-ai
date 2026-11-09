"""All currently detectable revenue blockers are returned before the review opens."""

import copy
from unittest.mock import patch
from backend.revenue.review import inspect_revenue
from backend.blocks.execution import run_stage
from backend.tests.test_isolated_stages import study


def inputs(study):
    store, key = study
    run_stage(store, key, "engineering_data")
    state = store.get(key)
    return (
        state["plan"]["operating_economics"],
        state["revenue_description"],
        state["stage_outputs"]["engineering_data"]["report"],
    )


def test_ready_revenue_has_no_optional_override_question(study):
    config, text, report = inputs(study)
    original = copy.deepcopy(config)
    with patch(
        "backend.orchestration.provider.EngineeringProvider",
        side_effect=AssertionError("No AI"),
    ):
        review = inspect_revenue(config, text, report)
    assert review["ready"], review
    assert review["questions"] == []
    assert config == original


def test_collects_price_source_fraction_and_schedule_in_one_pass(study):
    config, text, report = inputs(study)
    config["sales"][0].update(unit_price=None, stream_key="absent", sold_fraction=None)
    config["operating"]["hours_per_day"] = 0
    result = inspect_revenue(config, text, report)
    questions = " ".join(result["questions"]).lower()
    assert not result["ready"]
    for fragment in ["selling price", "measured", "sold output", "hours"]:
        assert fragment in questions


def test_cross_source_duplicates_are_caught_before_approval(study):
    config, text, report = inputs(study)
    config["sales"].append(copy.deepcopy(config["sales"][0]))
    result = inspect_revenue(config, text, report)
    assert not result["ready"]
    assert "duplicate" in " ".join(result["questions"]).lower()


def test_missing_price_and_sold_fraction_are_one_complete_review(study):
    config, text, report = inputs(study)
    config["sales"][0].update(unit_price=None, sold_fraction=None)
    result = inspect_revenue(config, text, report)
    assert len(result["questions"]) == 2, result
    # Apply the user's entire answer batch, then inspect once with no new question.
    config["sales"][0].update(unit_price=2, sold_fraction=0.8)
    after = inspect_revenue(config, text, report)
    assert after["ready"], after
