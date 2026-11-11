"""M3.4 scope controls (B08 decision C) and M3.3 capital breakdown.

Synthetic numbers only. Each expected value is computed independently here
from the published factors, never read back from the engine.
"""

from dataclasses import replace
from decimal import Decimal as D

import pytest

from backend.capex import (
    CapexInputs,
    EquipmentCost,
    UnitCapitalCost,
    WorkingCapital,
    calculate_capex,
)
from backend.capex.scope import CATEGORIES, eligibility, inclusion_record

BASIS = dict(currency="USD", period="2026", index_series="CEPCI", index_value=800)
NO_WC = WorkingCapital(excluded=True, rationale="fixed capital comparison only")


def purchased(amount=100, tag="P-1"):
    return EquipmentCost(
        tag,
        amount,
        cost_scope="purchased_equipment",
        delivery_basis="delivered",
        provenance={"source": "garrett"},
        **BASIS,
    )


def installed(amount=300, tag="I-1", included=("installation",), excluded=None):
    return UnitCapitalCost(
        tag,
        amount,
        cost_scope="installed_equipment",
        included_categories=included,
        provenance={
            "source": "test_installed_source",
            "excluded_categories": list(
                excluded
                if excluded is not None
                else (
                    "engineering_supervision",
                    "construction_overheads",
                    "contractor_fee",
                    "contingency",
                )
            ),
        },
        **BASIS,
    )


def unit(amount=1000, tag="U-1", included=("installation", "engineering"), excluded=("contingency",)):
    return UnitCapitalCost(
        tag,
        amount,
        cost_scope="unit_capital",
        included_categories=included,
        provenance={"source": "test_package", "excluded_categories": list(excluded)},
        **BASIS,
    )


def three_scopes(**changes):
    return replace(
        CapexInputs(
            (purchased(),),
            "fluids",
            factor_selection="minimum",
            working_capital=NO_WC,
            pre_costed_capital=(installed(), unit()),
        ),
        **changes,
    )


def line(result, factor_id):
    return next(l for l in result.lines if l.id == factor_id)


def category(result, name):
    return next(b for b in result.breakdown if b.category == name)


# --- Decision C acceptance fixture -----------------------------------------


def test_lang_applies_only_to_purchased_and_installation_counted_once():
    r = calculate_capex("nottingham_lang", three_scopes())
    lang = line(r, "lang_factor")
    assert lang.base_amount == D(100)  # scopes never summed before factors
    assert lang.amount == D(470)
    assert r.scope_subtotals["purchased_equipment"] == D(100)
    assert r.scope_subtotals["installed_equipment"] == D(300)
    assert r.scope_subtotals["unit_capital"] == D(1000)
    # 100 x 4.7 + 300 x (1 + no indirects available in Lang) + 1000
    assert r.plant_cost == D(1770)
    assert r.fixed_capital == D(1770)
    checks = {c["id"]: c for c in r.double_count_checks}
    assert all(c["passed"] for c in checks.values()), checks
    # Lang has no indirect or contingency factor for the installed/unit lines:
    # they are reported as gaps, not silently treated as zero.
    gaps = {(g["tag"], g["category"]) for g in r.scope_gaps}
    assert ("I-1", "engineering_supervision") in gaps
    assert ("I-1", "contingency") in gaps
    assert ("U-1", "contingency") in gaps


def test_garrett_indirects_and_contingency_on_eligible_bases_only():
    inputs = three_scopes(
        indirect_basis="direct_costs",
        selected_factors={"contingency": "0.10"},
    )
    r = calculate_capex("garrett", inputs)
    assert r.status == "provisional", r.issues
    garrett_direct_minima = sum(
        D(x)
        for x in (".15", ".10", ".10", ".30", ".07", ".02", ".02", ".05", ".10", ".05", "0")
    )
    purchased_direct = D(100) * (1 + garrett_direct_minima)  # 196
    assert purchased_direct == D(196)
    # Every plant/direct factor is charged on purchased equipment only.
    for f in (
        "piping",
        "electrical",
        "instrumentation_controls",
        "utilities_services",
        "foundations",
        "buildings",
    ):
        assert line(r, f).base_amount == D(100)
    # Installed line receives the engineering/fee factors its source excludes.
    eng = line(r, "construction_engineering")
    assert eng.base_amount == purchased_direct + 300
    assert eng.amount == (purchased_direct + 300) * D(".10")
    fee = line(r, "contractor_fee")
    assert fee.amount == (purchased_direct + 300) * D(".03")
    # Contingency: purchased path, installed (excluded by its source) and the
    # unit-capital package (excludes contingency). Unit capital never gets
    # engineering, its source already includes it.
    cont = line(r, "contingency")
    assert cont.base_amount == purchased_direct + 300 + 1000
    assert cont.amount == (purchased_direct + 300 + 1000) * D(".10")
    assert eng.scope_contributions["unit_capital"]["base"] == D(0)
    expected_plant = (
        purchased_direct + 300 + 1000 + eng.amount + fee.amount + cont.amount
    )
    assert r.plant_cost == expected_plant
    assert all(c["passed"] for c in r.double_count_checks), r.double_count_checks


def test_purchase_basis_indirects_are_not_stretched_over_installed_scope():
    r = calculate_capex("garrett", three_scopes())  # indirect_basis purchased
    eng = line(r, "construction_engineering")
    assert eng.base_amount == D(100)
    gaps = {(g["tag"], g["factor"]) for g in r.scope_gaps}
    assert ("I-1", "construction_engineering") in gaps
    assert ("U-1", "contingency") in gaps


def test_source_included_category_is_never_charged_again():
    already = installed(
        included=("installation", "engineering", "contingency"),
        excluded=("construction_overheads", "contractor_fee"),
    )
    r = calculate_capex(
        "garrett",
        three_scopes(
            indirect_basis="direct_costs",
            pre_costed_capital=(already,),
        ),
    )
    # Garrett's combined construction/engineering factor cannot be split, and
    # the source already includes engineering: not applied, reported.
    assert line(r, "construction_engineering").scope_contributions[
        "installed_equipment"
    ]["base"] == D(0)
    assert line(r, "contingency").scope_contributions["installed_equipment"][
        "base"
    ] == D(0)
    assert line(r, "contractor_fee").scope_contributions["installed_equipment"][
        "base"
    ] == D(300)


def test_unknown_inclusions_are_gaps_not_applied():
    record = inclusion_record("X", "unit_capital", {"source": "nowhere"})
    applies, status, _ = eligibility(record, "contingency")
    assert not applies and status == "unknown"
    applies, status, _ = eligibility(record, "piping")
    assert not applies and status == "not_eligible"


def test_module_estimate_belongs_to_installed_family():
    record = inclusion_record(
        "M", "module_estimate", {"costing_evidence": {"source": "openpytea"}}
    )
    assert record["scope"] == "installed_equipment"
    assert eligibility(record, "contingency")[0] is True
    assert eligibility(record, "engineering_supervision")[1] == "already_included"
    assert eligibility(record, "piping")[1] == "not_eligible"


# --- Missing scope ----------------------------------------------------------


def test_purchased_line_without_scope_is_rejected():
    no_scope = replace(purchased(), cost_scope=None)
    r = calculate_capex("garrett", three_scopes(equipment=(no_scope,)))
    assert r.total_capex is None
    assert r.status == "needs_review"
    assert any("no recorded cost scope" in i for i in r.issues)


def test_equipment_cost_has_no_default_scope():
    record = EquipmentCost("P-9", 100, **BASIS)
    assert record.cost_scope is None
    r = calculate_capex(
        "garrett",
        CapexInputs((record,), "fluids", factor_selection="minimum"),
    )
    assert r.total_capex is None
    assert any("no recorded cost scope" in i for i in r.issues)


def test_capital_line_without_scope_is_rejected():
    no_scope = replace(unit(), cost_scope=None)
    r = calculate_capex("garrett", three_scopes(pre_costed_capital=(no_scope,)))
    assert r.total_capex is None
    assert any("no recorded cost scope" in i for i in r.issues)


def test_connector_rejects_line_without_scope():
    from types import SimpleNamespace

    from backend.capex.connectors import prepare_capex_inputs

    line_ = SimpleNamespace(
        equipment_tag="Z-1",
        cost_scope=None,
        amount=10.0,
        equipment_cost=10.0,
        calculation=SimpleNamespace(estimate=object(), evidence={}),
        parsed_source=None,
        status="provisional",
    )
    total = SimpleNamespace(equipment=(line_,))
    with pytest.raises(ValueError, match="no recorded cost scope"):
        prepare_capex_inputs(total, process_type="fluids", delivery_basis="delivered")


# --- M3.3 breakdown ----------------------------------------------------------


def test_breakdown_lists_every_category_and_reconciles():
    r = calculate_capex(
        "garrett",
        three_scopes(
            indirect_basis="direct_costs",
            working_capital=WorkingCapital(),
            offsite_scope_confirmation="no shared facilities in this synthetic case",
        ),
    )
    assert r.total_capex is not None, r.issues
    assert [b.category for b in r.breakdown[: len(CATEGORIES)]] == list(CATEGORIES)
    owners = category(r, "owners_costs")
    assert owners.status == "gap" and owners.amount is None  # never zero
    assert category(r, "construction_overheads").status == "combined"
    assert category(r, "construction_overheads").combined_into == (
        "engineering_supervision"
    )
    # Garrett: equipment installation is embedded in the direct factors; the
    # category carries only insulation and painting, and says so.
    installation = category(r, "installation")
    assert installation.status == "calculated"
    assert {f["id"] for f in installation.factors} == {
        "equipment_installation",
        "insulation",
        "painting_fire_safety",
    }
    assert installation.amount == D(100) * (D(".02") + D(".02"))
    assert "embedded" in installation.note
    for b in r.breakdown:
        assert b.source and b.basis
        assert b.provisional is True
        assert b.ai_suggested is False
    total = sum(b.amount for b in r.breakdown if b.counted)
    assert total == r.total_capex
    assert "owners_costs" in r.breakdown_gaps


def test_nottingham_breakdown_separates_engineering_and_flags_gaps():
    r = calculate_capex(
        "nottingham",
        CapexInputs((purchased(1000),), "fluids", working_capital=NO_WC),
    )
    assert category(r, "engineering_supervision").amount == D(330)
    assert category(r, "construction_overheads").amount == D(410)
    assert category(r, "installation").amount == D(470)
    assert category(r, "civil_structural").status == "gap"
    assert category(r, "startup_commissioning").status == "gap"
    assert category(r, "working_capital").status == "excluded"
    # Decision D: excluded is reported as excluded, not as a zero amount.
    assert category(r, "working_capital").amount is None


def test_lang_breakdown_marks_categories_combined_in_lang_factor():
    r = calculate_capex("nottingham_lang", three_scopes())
    assert category(r, "piping").status == "combined"
    assert category(r, "piping").combined_into == "lang_overall"
    lang = next(b for b in r.breakdown if b.category == "lang_overall")
    assert lang.amount == D(370)  # 470 less the purchased equipment itself
    assert category(r, "purchased_equipment").amount == D(100)


def test_ai_suggested_override_is_labelled():
    from backend.capex import Override

    r = calculate_capex(
        "garrett",
        three_scopes(
            overrides={
                "piping": Override(
                    fraction="0.2", rationale="draft", source="AI suggestion"
                )
            }
        ),
    )
    assert category(r, "piping").ai_suggested is True
