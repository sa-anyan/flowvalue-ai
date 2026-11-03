"""Independent equations and shared-ledger scope/price acceptance tests."""

import copy

import pytest

from backend.engineering_sizing.adapter import derive
from backend.engineering_sizing.compression import calculate as compression
from backend.engineering_sizing.thermal import evaporated_water, phase_change_duty
from backend.equipment_costing.total_cost.calculator import calculate_total_cost
from backend.equipment_resolution.scope import expand
from backend.orchestration.pipeline import run
from backend.scenarios_and_uncertainty.monte_carlo.discovery import discover
from backend.scenarios_and_uncertainty.monte_carlo.engine import evaluate
from backend.tests.test_monte_carlo import complete_state


def price(**updates):
    return dict(
        amount=10000,
        currency="USD",
        price_period="1987",
        source="Private test quote Q1",
        notes="Synthetic independent fixture; unit package boundary",
        cost_scope="purchased_equipment",
        approved=True,
        locked=True,
        **updates,
    )


def item(p=None):
    return {
        "equipment_tag": "Unit",
        "manual_price": p or price(),
        "quantity": 2,
        "size": None,
        "size_unit": None,
    }


def test_manual_purchase_and_installation_extend_once():
    p = price(
        installation_factor=1.5,
        installation_rationale="Synthetic explicit installation allowance",
    )
    line = calculate_total_cost([item(p)]).equipment[0]
    assert line.equipment_cost == 20000
    assert line.installation_cost == 10000
    assert line.equipment_and_installation_cost == 30000
    assert line.calculation.estimate.index_series == "PRICE_BASIS:USD:1987"


def test_installed_split_and_unsplit_boundaries():
    p = price()
    p.update(cost_scope="installed_equipment", purchased_component=6000)
    line = calculate_total_cost([item(p)]).equipment[0]
    assert (
        line.equipment_cost,
        line.installation_cost,
        line.equipment_and_installation_cost,
    ) == (12000, 8000, 20000)
    del p["purchased_component"]
    line = calculate_total_cost([item(p)]).equipment[0]
    assert line.equipment_cost is None and line.equipment_and_installation_cost == 20000
    p["installation_factor"] = 1.5
    assert calculate_total_cost([item(p)]).equipment[0].amount is None


@pytest.mark.parametrize(
    "field,value",
    [
        ("amount", 0),
        ("amount", True),
        ("amount", float("nan")),
        ("approved", False),
        ("source", ""),
        ("currency", "$"),
        ("price_period", "today"),
        ("installation_factor", 0.8),
    ],
)
def test_invalid_manual_price_retained_unresolved(field, value):
    p = price()
    p[field] = value
    assert calculate_total_cost([item(p)]).equipment[0].amount is None


def test_fx_uses_canonical_converter_and_preserves_source():
    from backend.currency_conversion import convert_currency

    p = price()
    p.update(currency="EUR", price_period="2026-09", calculation_currency="USD")
    line = calculate_total_cost([item(p)]).equipment[0]
    assert line.amount == pytest.approx(
        2 * float(convert_currency(10000, "EUR", "USD")["amount"])
    )
    assert line.calculation.evidence["reference"]["currency"] == "EUR"


def test_physical_split_and_alias_no_tag_suffix_guess():
    s = complete_state()
    r = s["parsed"]["report"]
    p = s["plan"]
    base = p["equipment"][0]
    base["scope_confirmation"] = {
        "status": "user_confirmed",
        "rationale": "Two isolated services in source documentation",
    }
    base["physical_assets"] = [
        {
            "asset_id": x,
            "equipment_tag": "P-" + x,
            "manual_price": price(),
            "quantity": 1,
        }
        for x in ("acid", "base")
    ]
    original = copy.deepcopy((r, p))
    rr, pp = expand(r, p)
    assert (r, p) == original
    assert len([e for e in rr["entities"] if e["kind"] == "equipment"]) == 2
    assert len(pp["equipment"]) == 2
    rr, pp = expand(rr, pp)
    assert len(pp["equipment"]) == 2
    result = run(r, s["description"], p)
    register = result["stages"]["equipment"]["result"]["resolution_register"]
    assert register["physical_asset_count"] == 2 and register["priced_records"] == 2
    assert result["stages"]["equipment"]["result"]["equipment_cost_total"] == 20000
    d = discover({**s, "plan": p, "results": result})
    assert any(
        x["targets"][0]
        == ["equipment", 0, "physical_assets", 0, "manual_price", "amount"]
        for x in d["settings"]["parameters"]
    )
    base["scope_confirmation"]["status"] = "unconfirmed"
    with pytest.raises(ValueError, match="confirmation"):
        expand(r, p)


def test_alias_confirmation_and_cycle():
    s = complete_state()
    r = s["parsed"]["report"]
    p = s["plan"]
    r["entities"].append(
        {
            **next(e for e in r["entities"] if e["key"] == "pump"),
            "key": "duplicate",
            "identifier": "P-AB",
        }
    )
    # Identify equipment by canonical key, never suffix.
    p["equipment"].append(
        {
            "equipment_key": "duplicate",
            "scope_decision": "alias",
            "alias_of": "pump",
            "alias_confirmation": {
                "status": "user_confirmed",
                "rationale": "Same supplied asset",
            },
        }
    )
    result = run(r, s["description"], p)
    assert evaluate(r, s["description"], p, [])["coverage"]["confirmed_aliases"] == 1
    rows = result["stages"]["equipment"]["result"]["resolution_register"]
    assert rows["confirmed_aliases"] == 1
    p["equipment"][0].update(
        scope_decision="alias",
        alias_of="duplicate",
        alias_confirmation={"status": "user_confirmed", "rationale": "cycle"},
    )
    with pytest.raises(ValueError, match="cyclic"):
        expand(r, p)


def test_phase_change_and_drying_independent_hand_checks():
    q, unit, _ = phase_change_duty(
        3600,
        {
            "latent_heat_kj_kg": 2000,
            "phase_change_fraction": 1,
            "sensible_enthalpy_change_kj_kg": 100,
        },
    )
    assert q == 2100 and unit == "kW"
    assert evaporated_water(
        1000, {"feed_water_mass_fraction": 0.8, "product_water_mass_fraction": 0.1}
    )[0] == pytest.approx(777.7777778)
    with pytest.raises(ValueError):
        evaporated_water(
            100, {"feed_water_mass_fraction": 0.1, "product_water_mass_fraction": 0.8}
        )
    with pytest.raises(ValueError):
        phase_change_duty(100, {"phase_change_fraction": 1})


def test_phase_change_enters_existing_area_path():
    r = {
        "entities": [
            {
                "key": "feed",
                "values": [
                    {
                        "id": "v",
                        "property": "mass_flow",
                        "normalized_value": 3600,
                        "normalized_unit": "kg/h",
                        "status": "verified",
                    }
                ],
            }
        ]
    }
    params = {
        k: {"value": v, "unit": u}
        for k, v, u in [
            ("latent_heat_kj_kg", 2000, "kJ/kg"),
            ("phase_change_fraction", 1, "fraction"),
            ("overall_u_w_m2_k", 1000, "W/m2/K"),
            ("lmtd_k", 20, "K"),
            ("lmtd_correction", 1, "fraction"),
        ]
    }
    size, unit, details = derive(
        {"method": "exchanger_area", "stream_key": "feed", "parameters": params}, r
    )
    assert size == 100 and unit == "m2" and details["source_evidence"] == ["v"]


def test_compressor_positive_and_limits():
    inputs = {
        "molecular_weight_kg_kmol": 28,
        "temperature_k": 300,
        "absolute_pressure_bar": 1,
        "discharge_pressure_bar": 2,
        "heat_capacity_ratio": 1.4,
        "efficiency": 0.8,
        "compressibility_z": 1,
    }
    assert compression(3600, inputs)[0] == pytest.approx(
        (8.31446261815324 / 28) * 300 * 3.5 * (2 ** (2 / 7) - 1) / 0.8
    )
    with pytest.raises(ValueError):
        compression(3600, {**inputs, "discharge_pressure_bar": 0.5})


def test_user_price_propagates_equipment_capex_and_finance():
    s = complete_state()
    p = s["plan"]
    r = s["parsed"]["report"]
    p["equipment"][0]["manual_price"] = price()
    p["operating_economics"]["price_basis"]["price_period"] = "1987"
    before = run(r, s["description"], p)
    p["equipment"][0]["manual_price"]["amount"] = 20000
    after = run(r, s["description"], p)
    assert before["stages"]["equipment"]["result"]["equipment_cost_total"] == 10000
    assert after["stages"]["equipment"]["result"]["equipment_cost_total"] == 20000
    assert float(after["stages"]["capex"]["result"]["total_capex"]) > float(
        before["stages"]["capex"]["result"]["total_capex"]
    )
    assert (
        before["stages"]["financial"]["result"]["metrics"]
        != after["stages"]["financial"]["result"]["metrics"]
    )


def test_capacity_based_resin_sizing():
    from backend.engineering_sizing.ion_exchange import capacity_sizing

    size, unit, details = capacity_sizing(
        10,
        {
            "ionic_load_mol_equiv_m3": 2,
            "service_cycle_h": 8,
            "working_resin_capacity_mol_equiv_m3": 1000,
            "resin_bed_fraction": 0.8,
        },
    )
    assert size == pytest.approx(0.2) and unit == "m3"
    assert details["regeneration_load_mol_equivalents"] == 160


def test_conflicting_plan_keys_and_split_streams_are_rejected():
    s = complete_state()
    r = s["parsed"]["report"]
    p = s["plan"]
    p["equipment"].append(copy.deepcopy(p["equipment"][0]))
    with pytest.raises(ValueError, match="duplicate"):
        expand(r, p)
    p["equipment"].pop()
    p["equipment"][0].update(
        scope_confirmation={
            "status": "user_confirmed",
            "rationale": "separate services",
        },
        physical_assets=[
            {"asset_id": "a", "equipment_tag": "A", "stream_keys": ["nonexistent"]},
            {"asset_id": "b", "equipment_tag": "B"},
        ],
    )
    with pytest.raises(ValueError, match="connections"):
        expand(r, p)


def test_vaporizer_does_not_substitute_sensible_heat():
    report = {
        "entities": [
            {
                "key": "feed",
                "values": [
                    {
                        "id": "m",
                        "property": "mass_flow",
                        "normalized_value": 3600,
                        "normalized_unit": "kg/h",
                    }
                ],
            }
        ]
    }
    parameters = {
        k: {"value": v, "unit": u}
        for k, v, u in [
            ("specific_heat_kj_kg_k", 4, "kJ/kg/K"),
            ("temperature_change_k", 10, "K"),
            ("overall_u_w_m2_k", 1000, "W/m2/K"),
            ("lmtd_k", 20, "K"),
            ("lmtd_correction", 1, "fraction"),
        ]
    }
    with pytest.raises(ValueError, match="sensible Cp alone"):
        derive(
            {
                "method": "vaporizer_area",
                "stream_key": "feed",
                "parameters": parameters,
            },
            report,
        )


def test_manual_price_monte_carlo_reconciles_same_canonical_run():
    from backend.scenarios_and_uncertainty.monte_carlo.models import Parameter, Settings
    from backend.scenarios_and_uncertainty.monte_carlo.sampling import sample
    from backend.scenarios_and_uncertainty.monte_carlo.scenarios import apply, prepare

    s = complete_state()
    s["plan"]["equipment"][0]["manual_price"] = price()
    s["plan"]["operating_economics"]["price_basis"]["price_period"] = "1987"
    s["plan"]["cost_translation"] = {"enabled": False}
    p = Parameter(
        id="manual",
        label="Manual scenario price",
        targets=[["equipment", 0, "manual_price", "amount"]],
        unit="USD/equipment",
        kind="economic",
        enabled=True,
        minimum=9000,
        mode=10000,
        maximum=11000,
        source="Independent synthetic test",
        rationale="Explicit uncertainty fixture",
    )
    settings = Settings(parameters=[p], seed=15)
    discovered = Settings.model_validate(discover(s)["settings"])
    draws = sample(settings, discovered)[1]
    assert (draws == sample(settings, discovered)[1]).all()
    plan = prepare(s, settings)
    apply(plan, [p], draws[0])
    output = evaluate(s["parsed"]["report"], s["description"], plan, [])
    assert list(output["equipment_costs"].values()) == pytest.approx(
        [float(draws[0, 0])]
    )
    assert output["status"] == "complete"


def test_comparison_retains_missing_vs_zero():
    from backend.equipment_resolution.comparison import compare_results

    rows = compare_results(
        {"stages": {}}, {"stages": {"capex": {"result": {"total_capex": 0}}}}
    )
    assert {"metric": "capex.total_capex", "previous": None, "updated": 0} in rows


def test_phase_change_choice_preserves_conflicting_enthalpy_as_alternative():
    report = {
        "entities": [
            {
                "key": "feed",
                "values": [
                    {
                        "id": "m",
                        "property": "mass_flow",
                        "normalized_value": 3600,
                        "normalized_unit": "kg/h",
                    },
                    {
                        "id": "h1",
                        "property": "enthalpy_flow",
                        "normalized_value": 0,
                        "normalized_unit": "kW",
                    },
                ],
            },
            {
                "key": "out",
                "values": [
                    {
                        "id": "h2",
                        "property": "enthalpy_flow",
                        "normalized_value": 1,
                        "normalized_unit": "kW",
                    }
                ],
            },
        ]
    }
    params = {
        k: {"value": v, "unit": u}
        for k, v, u in [
            ("latent_heat_kj_kg", 2000, "kJ/kg"),
            ("phase_change_fraction", 1, "fraction"),
            ("overall_u_w_m2_k", 1000, "W/m2/K"),
            ("lmtd_k", 20, "K"),
            ("lmtd_correction", 1, "fraction"),
        ]
    }
    size, unit, details = derive(
        {
            "method": "vaporizer_area",
            "stream_key": "feed",
            "outlet_stream_key": "out",
            "parameters": params,
        },
        report,
    )
    assert size == 100 and unit == "m2"
    assert (
        details["calculation"]["unreconciled_alternative_duties"][0]["heat_duty_kw"]
        == 1
    )
    assert (
        details["calculation"]["thermal_basis"]["status"]
        == "assumption_based_not_verified"
    )


def test_specialist_refresh_cannot_replace_approved_cost_or_scope():
    from backend.orchestration.approved_equipment import retain_approved

    old = [
        {"equipment_key": "a", "manual_price": price()},
        {
            "equipment_key": "b",
            "scope_decision": "alias",
            "alias_of": "a",
            "alias_confirmation": {
                "status": "user_confirmed",
                "rationale": "User reviewed identity",
            },
        },
    ]
    snapshot = copy.deepcopy(old)
    result = retain_approved(old, [{"equipment_key": "a", "curve_id": "wrong"}])
    assert result == old and old == snapshot
    old[0]["manual_price"]["locked"] = False
    assert (
        retain_approved(old, [{"equipment_key": "a", "curve_id": "alternative"}])[0][
            "curve_id"
        ]
        == "alternative"
    )


def test_resolution_api_reuses_store_and_unknown_parent_404(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient

    import backend.api.app as api
    from backend.orchestration.store import Store

    store = Store(tmp_path / "test.sqlite3")
    state = complete_state()
    state["results"] = run(
        state["parsed"]["report"], state["description"], state["plan"]
    )
    saved = store.create(state, b"")
    monkeypatch.setattr(api, "store", store)
    with TestClient(api.app) as client:
        response = client.get(
            "/api/assessments/" + saved["id"] + "/equipment-resolution"
        )
        assert response.status_code == 200 and response.json()["priced_records"] == 1
        assert (
            client.get("/api/assessments/missing/equipment-resolution").status_code
            == 404
        )
        assert (
            client.get("/api/catalogue/equipment-knowledge").json()[
                "default_assumption_ranges"
            ]
            == []
        )


def test_real_charlie_thirteen_cases_against_saved_engineering_register():
    import json
    from pathlib import Path

    from backend.orchestration.store import Store

    metadata = Path("outputs/equipment-resolution/draft.json")
    if not metadata.exists():
        pytest.skip("Private real workbook fixture is not redistributed")
    store = Store("outputs/assessments/local.sqlite3")
    state = store.get(json.loads(metadata.read_text())["assessment"])
    source = (
        state.get("scoped_report")
        or state.get("effective_report")
        or state["parsed"]["report"]
    )
    original = copy.deepcopy(state)
    results = run(source, state["description"], state["plan"])
    from backend.equipment_resolution.review import review

    rows = {r["tag"]: r for r in review(source, state["plan"], results)["items"]}
    references = [
        "T-104",
        "T-101",
        "R-101",
        "T-105",
        "HE-101",
        "HE-102",
        "S-201",
        "FT-201",
        "PD-201AB",
        "PD-201",
        "C-201",
        "T-301",
        "R-201",
    ]
    for tag in references:
        assert tag in rows and rows[tag]["source"] and rows[tag]["rationale"]
        assert rows[tag]["status"] == (
            "PRICED — MODEL" if tag in {"HE-101", "HE-102", "T-301"} else "UNRESOLVED"
        )
        if rows[tag]["status"] == "UNRESOLVED":
            assert rows[tag]["purchased_cost"] is None
    assert state == original == store.get(state["id"])


def test_split_cannot_assign_all_parent_measurements_or_connections_by_default():
    s = complete_state()
    r = s["parsed"]["report"]
    p = s["plan"]
    parent = next(e for e in r["entities"] if e["key"] == "pump")
    parent["values"] = [
        {
            "id": "dimension",
            "property": "volume",
            "normalized_value": 5,
            "normalized_unit": "m3",
        }
    ]
    parent["stream_keys"] = ["water"]
    r["connections"] = [
        {"equipment_key": "pump", "stream_key": "water", "role": "outlet"}
    ]
    p["equipment"][0].update(
        scope_confirmation={
            "status": "user_confirmed",
            "rationale": "Two separately quoted assets",
        },
        physical_assets=[
            {"asset_id": "a", "equipment_tag": "A"},
            {"asset_id": "b", "equipment_tag": "B"},
        ],
    )
    rr, _ = expand(r, p)
    children = [e for e in rr["entities"] if e.get("parent_equipment_key") == "pump"]
    assert all(not e["values"] and not e["stream_keys"] for e in children)
    assert (
        not rr["connections"]
        and rr["scope_unresolved_connections"][0]["stream_key"] == "water"
    )
