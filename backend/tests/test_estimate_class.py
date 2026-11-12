"""M3.5: AACE estimate class proposal (18R-97 Table 1), for review only."""

import pytest

from backend.capex.estimate_class import (
    CLASS_MATRIX,
    DELIVERABLES,
    REFERENCE,
    propose_estimate_class,
)

FEASIBILITY = {
    "capacity_and_products": "complete",
    "plant_location": "preliminary",
    "process_flow_diagram": "preliminary",
}
BUDGET = {d.id: "complete" for d in DELIVERABLES}


def line(tag, amount=100.0, **evidence):
    estimate = {"extrapolated": evidence.pop("extrapolated", False)}
    return {"equipment_tag": tag, "curve_id": evidence.pop("curve_id", "G1"),
            "amount": amount, "calculation": {"estimate": estimate, "evidence": evidence}}


def test_table_1_values_as_published():
    """18R-97 Rev. 7 Aug 2020, Table 1, p. 3 of 21 (public sample)."""
    assert CLASS_MATRIX[5]["accuracy_low_percent"] == (-20, -50)
    assert CLASS_MATRIX[5]["accuracy_high_percent"] == (30, 100)
    assert CLASS_MATRIX[4]["accuracy_low_percent"] == (-15, -30)
    assert CLASS_MATRIX[4]["accuracy_high_percent"] == (20, 50)
    assert CLASS_MATRIX[4]["maturity_percent"] == (1, 15)
    assert CLASS_MATRIX[3]["accuracy_high_percent"] == (10, 30)
    assert CLASS_MATRIX[2]["accuracy_low_percent"] == (-5, -15)
    assert CLASS_MATRIX[1]["maturity_percent"] == (65, 100)
    assert "Table 1" in REFERENCE and "Rev. 7 August 2020" in REFERENCE


def test_nothing_declared_is_class_5_and_says_what_is_missing():
    result = propose_estimate_class(balance_approved=True, equipment_lines=[line("P-1")])
    assert result["proposed_class"] == 5
    assert result["status"] == "proposed" and result["requires_review"]
    missing = {g["id"] for g in result["gaps_to_next_class"]}
    assert missing == {"capacity_and_products", "plant_location", "process_flow_diagram"}
    rows = {r["id"]: r for r in result["deliverables"]}
    assert rows["heat_and_material_balance"]["basis"].startswith("derived")
    assert rows["plot_plan"]["basis"] == "not_stated_treated_as_absent"


def test_feasibility_deliverables_give_class_4_with_class_3_gaps():
    result = propose_estimate_class(design_maturity=FEASIBILITY, balance_approved=True,
                                    equipment_lines=[line("P-1")], capex_method="garrett")
    assert result["proposed_class"] == 4
    assert result["class_characteristics"]["end_usage"] == "Study or feasibility"
    assert {g["id"] for g in result["gaps_to_next_class"]} >= {
        "piping_and_instrument_diagrams", "plot_plan", "heat_and_material_balance"}
    assert not result["issues"]


def test_unapproved_balance_holds_class_5():
    result = propose_estimate_class(design_maturity=FEASIBILITY, balance_approved=False,
                                    equipment_lines=[line("P-1")])
    assert result["proposed_class"] == 5


def test_class_3_maturity_with_factored_method_is_flagged_not_downgraded():
    result = propose_estimate_class(design_maturity=BUDGET, capex_method="garrett")
    assert result["proposed_class"] == 3
    assert result["next_class"] is None
    assert any("equipment factored" in i for i in result["issues"])


def test_classes_1_and_2_are_never_proposed():
    result = propose_estimate_class(design_maturity=BUDGET)
    assert result["proposed_class"] == 3
    assert any("Classes 2 and 1" in r for r in result["reasons"])


def test_costing_caveats_widen_range_but_never_change_class():
    lines = [
        line("A", below_range_floor={"size_ratio": 100}),
        line("B", extrapolated=True),
        line("C", cost_translation={"status": "general_inflation_proxy"}),
        line("D", method="reviewed_comparable"),
    ]
    result = propose_estimate_class(design_maturity=FEASIBILITY, balance_approved=True,
                                    equipment_lines=lines, unpriced=["E"], new_technology=True)
    assert result["proposed_class"] == 4
    c = result["costing_evidence"]
    assert (c["items"], c["priced"], c["unpriced"]) == (5, 4, 1)
    assert (c["minimum_size_floor"], c["extrapolated"], c["cpi_proxy_escalated"]) == (1, 1, 1)
    assert c["user_or_quote_priced"] == 1
    text = " ".join(result["wide_end_reasons"])
    for phrase in ("unpriced", "minimum size", "extrapolated", "CPI proxy", "two to three times"):
        assert phrase in text
    rows = {r["id"]: r for r in result["deliverables"]}
    assert rows["major_equipment_quotes"]["status"] == "preliminary"


def test_unpriced_line_amount_none_counts_as_unpriced_only_once():
    result = propose_estimate_class(equipment_lines=[line("A"), line("B", amount=None)], unpriced=["B"])
    assert result["costing_evidence"]["priced"] == 1


def test_reviewer_confirms_or_overrides_with_rationale():
    base = dict(design_maturity=FEASIBILITY, balance_approved=True, equipment_lines=[line("A")])
    ok = propose_estimate_class(**base, review={"class": 4, "reviewer": "Engineer 2"})
    assert ok["status"] == "confirmed" and not ok["requires_review"]
    with pytest.raises(ValueError, match="rationale"):
        propose_estimate_class(**base, review={"class": 5, "reviewer": "Engineer 2"})
    over = propose_estimate_class(**base, review={"class": 5, "reviewer": "E2", "rationale": "Electrolyser scope immature"})
    assert over["status"] == "reviewer_override"
    assert over["proposed_class"] == 4 and over["effective_class"] == 5
    assert over["class_characteristics"]["accuracy_high_percent"] == (30, 100)
    with pytest.raises(ValueError, match="reviewer"):
        propose_estimate_class(**base, review={"class": 4})
    with pytest.raises(ValueError, match="1-5"):
        propose_estimate_class(**base, review={"class": 0, "reviewer": "E2"})


def test_bad_declarations_are_rejected():
    with pytest.raises(ValueError, match="Unknown"):
        propose_estimate_class(design_maturity={"pids": "complete"})
    with pytest.raises(ValueError, match="one of"):
        propose_estimate_class(design_maturity={"plot_plan": "done"})


def test_capex_stage_reports_class_and_edit_marks_it_stale(tmp_path):
    from backend.blocks.execution import run_stage
    from backend.orchestration.service import edit
    store, key = _study(tmp_path)
    for stage in ("engineering_data", "equipment", "capex"):
        state = run_stage(store, key, stage)
    proposal = state["results"]["stages"]["capex"]["result"]["estimate_class"]
    assert proposal["status"] == "proposed" and proposal["proposed_class"] in {4, 5}
    changed = edit(store, key, state["revision"], "estimate_class",
                   {"design_maturity": {"plot_plan": "done"}}, "Declare deliverables")
    assert changed["stage_runs"]["capex"]["status"] == "stale"
    state = run_stage(store, key, "capex")
    bad = state["results"]["stages"]["capex"]["result"]["estimate_class"]
    assert bad["status"] == "invalid_input" and "one of" in bad["error"]
    assert state["stage_runs"]["capex"]["status"] == "ready"


def _study(tmp_path):
    from backend.blocks.execution import initialize
    from backend.orchestration.ingest import parse
    from backend.orchestration.service import new_assessment
    from backend.orchestration.store import Store
    from backend.tests.test_stage_connections import DESCRIPTION, plan_for, workbook

    content = workbook()
    report = parse(content, "independent.xlsx")["report"]
    store = Store(tmp_path / "stages.sqlite")
    state = initialize(new_assessment(store, content, "independent.xlsx", DESCRIPTION, "sells treated water"))
    state.update(running=False, plan=plan_for(report))
    state = store.put(state, state["revision"])
    return store, state["id"]


def test_floor_key_with_none_value_is_not_counted():
    """Saved lines can carry below_range_floor=None when no floor applied."""
    result = propose_estimate_class(equipment_lines=[
        line("A", below_range_floor=None), line("B", below_range_floor={"size_ratio": 3})])
    assert result["costing_evidence"]["minimum_size_floor"] == 1
