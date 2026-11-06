"""Independent equation checks and canonical additional-model handoff regressions.

Synthetic source observations, NOT claimed Team 8(6) workbook validation.
"""

import copy
from dataclasses import replace
from decimal import Decimal as D, localcontext
import pytest
from backend.equipment_costing.registry import (
    estimate_cost,
    list_equipment_models,
    estimate_from_parsed_inputs,
)
from backend.equipment_costing.indexes.additional_models.registry import (
    EPA,
    TURTON,
    CIRCULAR,
    RECTANGULAR,
)
from backend.equipment_costing.unit_conversion import (
    convert,
    ConversionContext,
    Measurement,
)
from backend.equipment_costing.unit_conversion.bridges.service import evaluate
from backend.equipment_costing.total_cost.calculator import calculate_total_cost
from backend.equipment_costing.cost_to_future.cost_translation import (
    DEFAULT_POLICY,
    translate_calculation,
    translate_cost,
)
from backend.capex.connectors import prepare_capex_inputs
from backend.capex import calculate_capex
from backend.capex.models import CapexInputs, EquipmentCost
from backend.equipment_matching.service import catalogue, lexical_candidates


def test_registry_and_independent_equations():
    ids = {m["id"] for m in list_equipment_models("all")}
    assert {EPA, TURTON, CIRCULAR, RECTANGULAR} <= ids
    assert list_equipment_models()  # unchanged Garrett default
    with localcontext() as ctx:
        ctx.prec = 40
        x = D("0.2").ln()
        expected = (D("11.721") + D(".543") * x + D(".000139") * x * x).exp()
        assert estimate_cost(
            EPA, 0.2, size_unit="US_MGD"
        ).estimate.amount == pytest.approx(float(expected))
        x = D("10").log10()
        expected = D(10) ** (D("4.1052") + D(".532") * x - D(".0005") * x * x)
        assert estimate_cost(
            TURTON, 10, size_unit="m3"
        ).estimate.amount == pytest.approx(float(expected))
    for model, expected in [(CIRCULAR, 290158.0), (RECTANGULAR, 260655.0)]:
        assert estimate_cost(
            model, 1000, size_unit="ft2", allow_unverified=True
        ).estimate.amount == pytest.approx(expected)


@pytest.mark.parametrize(
    "model,unit", [(EPA, "US_MGD"), (TURTON, "m3"), (CIRCULAR, "ft2")]
)
@pytest.mark.parametrize("value", [0, -1, None, float("nan"), float("inf"), True])
def test_invalid_input(model, unit, value):
    with pytest.raises((ValueError, TypeError)):
        estimate_cost(model, value, size_unit=unit, allow_unverified=True)


@pytest.mark.parametrize("v", [0.09, 35.01, 10000])
def test_fermenter_strict_range(v):
    with pytest.raises(ValueError, match="MODEL_OUT_OF_RANGE"):
        estimate_cost(TURTON, v, size_unit="m3")


@pytest.mark.parametrize("model,area", [(CIRCULAR, 90000), (RECTANGULAR, 30000)])
def test_clarifier_guard_and_explicit_provisional_acceptance(model, area):
    with pytest.raises(ValueError, match="MODEL_APPLICABILITY_UNVERIFIED"):
        estimate_cost(model, 100, size_unit="ft2")
    with pytest.raises(ValueError, match="MODEL_OUT_OF_RANGE"):
        estimate_cost(model, area, size_unit="ft2", allow_unverified=True)


def report(flow=125127.5):
    return {
        "entities": [
            {
                "key": "e",
                "identifier": "P-001",
                "kind": "equipment",
                "stream_keys": ["s"],
                "values": [],
            },
            {
                "key": "s",
                "identifier": "Feed",
                "kind": "material",
                "values": [
                    {
                        "id": "m",
                        "property": "mass_flow",
                        "normalized_value": flow,
                        "normalized_unit": "kg/h",
                        "status": "verified",
                        "sheet": "MEB",
                        "cell": "C7",
                    }
                ],
            },
        ]
    }


def spec(model, method, **inputs):
    return dict(
        model_id=model,
        method=method,
        measurement_id="m",
        inputs=inputs,
        rationale="Explicit synthetic QA assumptions",
    )


def test_flow_and_clarifier_conversion_traceability():
    r = report()
    before = copy.deepcopy(r)
    a = evaluate(r, "e", spec(EPA, "liquid_flow", density_kg_m3=1000))
    assert a["size"] == pytest.approx(125.1275 * 24 / 3785.411784)
    assert a["source_measurements"][0]["cell"] == "C7"
    b = evaluate(
        r,
        "e",
        spec(CIRCULAR, "clarifier_area", density_kg_m3=1000, hydraulic_loading_m_h=2),
    )
    assert b["size"] == pytest.approx(125.1275 / 2 / 0.09290304)
    assert r == before
    with pytest.raises(ValueError, match="density"):
        evaluate(r, "e", spec(EPA, "liquid_flow"))


def test_fermenter_mode_and_residence():
    s = spec(
        TURTON,
        "vessel_volume",
        density_kg_m3=1000,
        residence_time_h=0.1,
        working_fraction=0.8,
    )
    with pytest.raises(ValueError, match="operating_mode"):
        evaluate(report(), "e", s)
    s["operating_mode"] = "continuous"
    r = evaluate(report(), "e", s)
    assert r["size"] == pytest.approx(125.1275 * 0.1 / 0.8)
    assert estimate_cost(TURTON, r["size"], size_unit=r["size_unit"]).estimate
    s["inputs"]["residence_time_h"] = 10
    r = evaluate(report(), "e", s)
    with pytest.raises(ValueError, match="MODEL_OUT_OF_RANGE"):
        estimate_cost(TURTON, r["size"], size_unit=r["size_unit"])


def test_dimensions_pressure_and_parser_adapter():
    assert convert(1, "m3", "ft3").value == pytest.approx(35.3146667215)
    assert convert(1, "m2", "ft2").value == pytest.approx(10.7639104167)
    c = convert(
        1,
        "barg",
        "bar",
        context=ConversionContext(
            target_pressure_basis="absolute", atmospheric_pressure_pa=101325
        ),
    )
    assert c.value == pytest.approx(2.01325)
    assert convert(1, "kg", "ft2").value is None
    c = estimate_from_parsed_inputs(
        EPA, {"size": Measurement(125.1275, "m3/h", {"cell": "C7"})}
    )
    assert c.evidence["input_provenance"]["cell"] == "C7"


@pytest.mark.parametrize(
    "model,unit,size,year",
    [
        (EPA, "US_MGD", 0.5, "1989"),
        (TURTON, "m3", 10, "2001"),
        (CIRCULAR, "ft2", 1000, "2011"),
    ],
)
def test_escalation_and_no_double_escalation(model, unit, size, year):
    c = estimate_cost(model, size, size_unit=unit, allow_unverified=True)
    x = translate_calculation(c, method_id="additional_models", policy=DEFAULT_POLICY)
    assert c.estimate.period == year
    assert x.estimate.period == "2026-09"
    assert x.estimate.amount > c.estimate.amount
    assert x.evidence["cost_translation"]["status"] == "general_inflation_proxy"
    y = translate_calculation(x, method_id="additional_models", policy=DEFAULT_POLICY)
    assert y == x
    with pytest.raises(ValueError):
        translate_calculation(
            c,
            method_id="additional_models",
            policy={"target_period": "2099", "allow_general_inflation_proxy": False},
        )


def test_explicit_native_indices_override():
    indices = {
        "series": {
            "CEPCI": {
                "currency": "USD",
                "observations": {
                    "2026": {
                        "value": "900",
                        "source": "Synthetic QA target, NOT a real published index",
                    }
                },
            }
        }
    }
    policy = {
        "target_period": "2026",
        "source_index_overrides": {
            "additional_models": {
                "2001": {
                    "series": "CEPCI",
                    "value": 397,
                    "source": "Synthetic QA source, NOT a source claim",
                }
            }
        },
    }
    r = translate_cost(
        100,
        currency="USD",
        source_period="2001",
        source_series="SOURCE_PRICE_BASIS",
        source_index=1,
        method_id="additional_models",
        policy=policy,
        indices=indices,
    )
    assert float(r.amount) == pytest.approx(100 * 900 / 397)
    assert r.status == "same_series_index_ratio"


def test_quantity_and_capital_factor_boundary():
    total = calculate_total_cost(
        [
            dict(
                equipment_tag="P-001AB",
                curve_id=EPA,
                size=0.5,
                size_unit="US_MGD",
                quantity=2,
            ),
            dict(equipment_tag="R-001", curve_id=TURTON, size=10, size_unit="m3"),
        ],
        translation_policy=DEFAULT_POLICY,
    )
    assert all(e.amount for e in total.equipment)
    assert total.equipment[0].equipment_cost is None  # never a purchased subtotal
    assert total.equipment[0].installation_cost is None
    assert total.equipment[0].amount == pytest.approx(
        total.equipment[0].calculation.estimate.amount * 2
    )
    inputs = prepare_capex_inputs(
        total,
        process_type="fluids",
        delivery_basis="delivered",
        factor_selection="minimum",
    )
    assert len(inputs.pre_costed_capital) == 1 and len(inputs.equipment) == 1
    mixed = calculate_capex(inputs=inputs)
    base = calculate_capex(inputs=replace(inputs, pre_costed_capital=()))
    capital = D(str(total.equipment[0].amount))
    assert mixed.plant_cost == base.plant_cost + capital
    assert mixed.direct_costs == base.direct_costs + capital
    assert mixed.indirect_costs == base.indirect_costs
    assert mixed.total_capex is not None
    assert mixed.plant_cost == mixed.direct_costs + mixed.indirect_costs
    duplicate = replace(
        inputs, pre_costed_capital=(replace(inputs.pre_costed_capital[0], tag="R-001"),)
    )
    assert calculate_capex(inputs=duplicate).total_capex is None


def test_capital_only_and_no_generic_installation():
    total = calculate_total_cost(
        [dict(equipment_tag="P", curve_id=EPA, size=0.5, size_unit="US_MGD")]
    )
    i = prepare_capex_inputs(
        total,
        process_type="fluids",
        delivery_basis="delivered",
        factor_selection="minimum",
    )
    r = calculate_capex(inputs=i)
    assert r.purchased_equipment == 0
    assert r.plant_cost == D(str(total.equipment[0].amount))
    assert r.total_capex is not None
    with pytest.raises(ValueError, match="corrections"):
        estimate_cost(EPA, 0.5, size_unit="US_MGD", factors=["installation"])


def test_matching_aliases_not_tag_prefix():
    models = catalogue()
    assert EPA in lexical_candidates(
        {"names": ["pH adjustment"], "tag": "P-001"}, models
    )
    assert TURTON in lexical_candidates(
        {"names": ["fungal bioreactor"], "tag": "R-001"}, models
    )
    assert CIRCULAR in lexical_candidates(
        {"names": ["biomass settler"], "tag": "S-001"}, models
    )
    assert EPA not in lexical_candidates({"names": ["Pump"], "tag": "P-001"}, models)


def test_connected_parser_to_twenty_year_financial_ledger(tmp_path):
    """Real canonical stages, no provider calls or alternative financial engine."""
    from backend.tests.test_stage_connections import (
        workbook,
        plan_for,
        StageConnectionTests,
    )
    from backend.orchestration.service import (
        new_assessment,
        _execute_connected_reference as execute,
    )
    from backend.orchestration.ingest import parse
    from backend.orchestration.store import Store
    from backend.revenue.authority import update

    data = workbook()
    store = Store(tmp_path / "additional-integration.sqlite")
    state = new_assessment(
        store,
        data,
        "synthetic-additional.xlsx",
        "Continuous water treatment",
        "sells treated water",
    )
    parsed = parse(data, state["filename"])
    plan = plan_for(parsed["report"])
    row = plan["equipment"][0]
    key = row["equipment_key"]
    plan["equipment"] = [
        dict(
            equipment_key=key,
            curve_id=EPA,
            source="additional_models",
            quantity=2,
            size=125.1275,
            size_unit="m3/h",
            rationale="Synthetic package scope integration test",
        )
    ]
    plan["cost_translation"] = {**DEFAULT_POLICY, "enabled": True}
    state.update(parsed=parsed, plan=plan, running=False)
    state = store.put(state, state["revision"])
    state = update(store, state["id"], state["revision"], approve=True)
    a = execute(store, state["id"], use_ai=False)
    for stage in (
        "equipment",
        "capex",
        "operating_economics",
        "opex",
        "revenue",
        "financial",
    ):
        current = a["results"]["stages"][stage]
        assert current["status"] not in (
            "pending",
            "partial",
            "unresolved",
            "pending_dependencies",
        ), current
        assert current["result"] is not None
    assert (
        dict(a["results"]["stages"]["financial"]["result"]["metrics"])["project_npv"][
            "value"
        ]
        is not None
    )
    item = a["results"]["stages"]["equipment"]["result"]["equipment"][0]
    assert item["cost_scope"] == "unit_capital" and item["amount"] > 0
    assert item["equipment_cost"] is None
    capex = a["results"]["stages"]["capex"]["result"]
    assert D(capex["plant_cost"]) == D(str(item["amount"]))
    assert (
        len(
            [
                r
                for r in a["results"]["stages"]["financial"]["result"]["ledger"]
                if r["products"]
            ]
        )
        == 20
    )
