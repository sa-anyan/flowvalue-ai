"""M3.7: coverage tiers with stated confidence (R1) and unpriced significance (A4)."""

import copy
from decimal import Decimal

from backend.blocks.execution import view
from backend.capex.coverage_tiers import classify_line, coverage_tiers, unpriced_significance
from backend.dashboard_reporting.basis_of_estimate import build_basis_of_estimate, render_markdown
from backend.tests.test_basis_of_estimate import capex_study  # noqa: F401  (fixture)


def _line(tag, amount, *, classification="pump", currency="USD", floor=None, extrapolated=False,
          provenance=None, issues=(), evidence=None, label="CALCULATED — CORRELATION", curve="G1"):
    ev = {"cost_translation": {"status": "same_series_index_ratio"}, **(evidence or {})}
    if floor is not None:
        ev["below_range_floor"] = floor
    return {
        "equipment_tag": tag,
        "amount": None if amount is None else str(amount),
        "curve_id": curve,
        "pricing_status": label,
        "issues": list(issues),
        "parsed_source": {"classification": classification,
                          "sizing": {"input_provenance": provenance or {}}},
        "calculation": {"evidence": ev, "estimate": {"currency": currency, "extrapolated": extrapolated}},
    }


def test_in_range_with_study_inputs_is_source_supported():
    line = _line("P-1", 100, provenance={"flow_m3_h": {"status": "derived_from_meb"}})
    assert classify_line(line)["tier"] == "source_supported"


def test_floor_extrapolation_and_analogy_are_assumption_based():
    floored = classify_line(_line("P-1", 100, floor={"size_ratio": "8"}))
    assert floored["tier"] == "assumption_based"
    assert "minimum size" in floored["reasons"][0] and "8x" in floored["reasons"][0]
    assert classify_line(_line("P-2", 100, extrapolated=True))["tier"] == "assumption_based"
    analogy = classify_line(_line("P-3", 100, label="ESTIMATED — INDEPENDENT ANALOGY"))
    assert analogy["tier"] == "assumption_based" and "analogy" in analogy["reasons"][0]


def test_floor_key_present_with_none_is_not_a_floor():
    assert classify_line(_line("P-1", 100, floor=None, evidence={"below_range_floor": None}))["tier"] == "source_supported"


def test_ai_estimated_or_assumed_inputs_are_named():
    line = _line("P-1", 100, provenance={
        "density_kg_m3": {"status": "llm_estimate"},
        "efficiency": {"status": "assumed"},
        "flow_m3_h": {"status": "derived_from_meb"},
    })
    result = classify_line(line)
    assert result["tier"] == "assumption_based"
    assert "2 sizing input(s)" in result["reasons"][0]
    assert "density_kg_m3 (estimated by AI)" in result["reasons"][0]
    assert "flow_m3_h" not in result["reasons"][0]


def test_openpytea_assumed_coordinates_are_assumptions():
    primary = _line("T-1", 100, evidence={"input_classification": "ASSUMED"})
    second = _line("T-2", 100, evidence={"second_input_conversion": {"source": {"status": "ASSUMED"}}})
    extracted = _line("T-3", 100, evidence={"input_classification": "DERIVED",
                                            "second_input_conversion": {"source": {"status": "EXTRACTED"}}})
    assert classify_line(primary)["tier"] == "assumption_based"
    assert classify_line(second)["tier"] == "assumption_based"
    assert classify_line(extracted)["tier"] == "source_supported"


def test_user_evidence_wins_and_source_caveats_do_not_change_tier():
    user = _line("P-1", 100, floor={"size_ratio": "3"}, evidence={"method": "reviewed_comparable"})
    assert classify_line(user)["tier"] == "user_evidence"
    caveated = classify_line(_line("P-2", 100, issues=["UNVERIFIED correlation"], evidence={
        "applicability_status": "provisional", "cost_translation": {"status": "general_inflation_proxy"}}))
    assert caveated["tier"] == "source_supported"
    assert len(caveated["source_caveats"]) == 3


def test_summary_counts_values_and_never_values_unpriced():
    lines = [_line("A", 600), _line("B", 300, floor={"size_ratio": "2"}), _line("C", 100, extrapolated=True),
             _line("D", None)]
    result = coverage_tiers(lines, unpriced_tags=["E", "D"])
    t = result["tiers"]
    assert result["items"] == 5
    assert (t["source_supported"]["items"], t["assumption_based"]["items"], t["unpriced"]["items"]) == (1, 2, 2)
    assert t["unpriced"]["value"] is None and t["unpriced"]["fraction_of_priced_value"] is None
    assert t["source_supported"]["fraction_of_priced_value"] == "0.600"
    assert t["assumption_based"]["fraction_of_priced_value"] == "0.400"
    assert result["supported_fraction"] == "0.200"
    assert result["meets_coverage_target_without_assumptions"] is False
    assert result["assumption_kinds"]["minimum_size_floor"] == 1
    assert result["assumption_kinds"]["extrapolated"] == 1
    assert all(isinstance(v["confidence"]["statement"], str) for v in t.values())
    assert "no numeric confidence" in result["notice"]


def test_coverage_target_boundary():
    lines = [_line(f"P{i}", 10) for i in range(19)] + [_line("X", 10, extrapolated=True)]
    assert coverage_tiers(lines)["meets_coverage_target_without_assumptions"] is True
    lines[0]["calculation"]["estimate"]["extrapolated"] = True
    assert coverage_tiers(lines)["meets_coverage_target_without_assumptions"] is False


def test_mixed_currencies_are_not_summed():
    result = coverage_tiers([_line("A", 1), _line("B", 1, currency="GBP")])
    assert result["tiers"]["source_supported"]["value"] is None
    assert "not summed" in result["value_basis"]


def test_significance_uses_same_classification_then_all_priced():
    lines = [_line("P-1", 100), _line("P-2", 300), _line("R-1", 5000, classification="reactor"),
             _line("P-9", None), _line("X-1", None, classification="mystery")]
    before = copy.deepcopy(lines)
    result = unpriced_significance(lines)
    assert lines == before  # never fills a price in
    p9, x1 = result["items"]
    assert p9["band"] == {"low": "100", "high": "300"} and "same classification" in p9["basis"]
    assert x1["band"] == {"low": "100", "high": "5000"} and "all 3 priced items" in x1["basis"]
    assert result["total_band"] == {"low": "200", "high": "5300"}
    assert result["significance"] == "not_compared"
    assert "never added to any total" in result["notice"]


def test_significance_against_class_range():
    lines = [_line("P-1", 100), _line("P-2", 900), _line("P-3", None)]
    cls4 = {"class": 4, "accuracy_high_percent": (20, 50)}
    small = [_line("P-1", 100), _line("P-2", 100), _line("P-4", 800, classification="other"), _line("P-3", None)]
    assert unpriced_significance(small, class_characteristics=cls4)["significance"] == "within_class_range"
    big = unpriced_significance(lines, class_characteristics=cls4)
    assert big["significance"] == "significant"
    assert big["against_estimate_class"]["could_exceed"] is True
    assert "+20% narrowest typical high range of Class 4" in big["against_estimate_class"]["statement"]


def test_significance_edge_cases():
    assert unpriced_significance([_line("A", 1)])["status"] == "none_unpriced"
    assert unpriced_significance([_line("A", None)])["status"] == "not_assessable"
    mixed = unpriced_significance([_line("A", 1), _line("B", 1, currency="GBP")], ["C"])
    assert mixed["status"] == "not_assessable"


def test_equipment_stage_records_tiers(capex_study):  # noqa: F811
    store, key = capex_study
    equipment = view(store.get(key))["results"]["stages"]["equipment"]["result"]
    coverage = equipment["pricing_coverage"]
    assert coverage["tiers"]["items"] == len(equipment["equipment"])
    assert "lines" not in coverage["tiers"]
    assert coverage["unpriced_significance"]["status"] in {"none_unpriced", "assessed", "not_assessable"}
    assert all(l["coverage_tier"]["tier"] in {"source_supported", "user_evidence", "assumption_based", "unpriced"}
               for l in equipment["equipment"])


def test_basis_of_estimate_reports_tiers_and_significance(capex_study):  # noqa: F811
    store, key = capex_study
    state = view(store.get(key))
    equipment = state["results"]["stages"]["equipment"]["result"]["equipment"]
    priced = [l for l in equipment if l["amount"] is not None]
    unpriced_line = copy.deepcopy(priced[0])
    unpriced_line.update(equipment_tag="HX-9", amount=None)
    state["results"]["stages"]["equipment"]["result"]["equipment"].append(unpriced_line)
    state["results"]["stages"]["capex"]["result"]["unpriced_equipment"] = ["HX-9"]
    total_before = state["results"]["stages"]["capex"]["result"]["total_capex"]
    boe = build_basis_of_estimate(state)
    tiers = boe["coverage"]["tiers"]
    assert tiers["tiers"]["unpriced"]["tags"] == ["HX-9"]
    sig = boe["coverage"]["unpriced_significance"]
    assert sig["status"] == "assessed" and sig["items"][0]["tag"] == "HX-9"
    assert sig["significance"] in {"significant", "within_class_range"}
    assert boe["totals"]["total_capex"] == total_before
    assert all(r["coverage_tier"] for r in boe["scope"]["priced_equipment"])
    text = render_markdown(boe)
    assert "### Coverage tiers" in text and "### Significance of unpriced items" in text
    assert Decimal(sig["total_band"]["high"]) > 0


def test_confirmed_alias_is_not_counted_as_unpriced(capex_study):  # noqa: F811
    store, key = capex_study
    state = view(store.get(key))
    equipment = state["results"]["stages"]["equipment"]["result"]["equipment"]
    alias = copy.deepcopy(equipment[0])
    alias["equipment_tag"] = "P-ALIAS"
    alias["amount"] = None
    alias["parsed_source"]["confirmed_alias"] = True
    equipment.append(alias)
    boe = build_basis_of_estimate(state)
    assert "P-ALIAS" not in boe["coverage"]["tiers"]["tiers"]["unpriced"]["tags"]
    assert boe["coverage"]["unpriced_significance"]["status"] == "none_unpriced"
