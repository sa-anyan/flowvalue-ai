from backend.equipment_costing.unit_conversion.bridges.thermal_screening import (
    temperature_arrangements,
)


def test_equal_outlets_have_positive_countercurrent_approach_not_parallel():
    obs = [
        {
            "id": key,
            "entity_key": key,
            "property": "temperature",
            "value": temp,
            "unit": "degC",
        }
        for key, temp in [("hi", 150), ("ho", 80), ("ci", 20), ("co", 80)]
    ]
    contexts = [
        {
            "entity_key": key,
            "connections": [
                {"role": "destination" if key in ["hi", "ci"] else "source"}
            ],
        }
        for key in ["hi", "ho", "ci", "co"]
    ]
    result = temperature_arrangements(obs, contexts)
    selected = next(
        r
        for r in result["arrangements"]
        if r["roles"]
        == {
            "hot_inlet": "hi",
            "hot_outlet": "ho",
            "cold_inlet": "ci",
            "cold_outlet": "co",
        }
    )
    assert selected["feasibility"]["countercurrent"]["valid"]
    assert selected["feasibility"]["countercurrent"]["lmtd_k"] > 0
    assert not selected["feasibility"]["parallel"]["valid"]
    assert not result["truncated"]


def test_missing_or_conflicting_temperatures_do_not_become_invented_facts():
    obs = [
        {
            "id": "one",
            "entity_key": "stream",
            "property": "temperature",
            "value": 10,
            "unit": "degC",
        },
        {
            "id": "two",
            "entity_key": "stream",
            "property": "temperature",
            "value": 20,
            "unit": "degC",
        },
    ]
    result = temperature_arrangements(obs, [])
    assert result["arrangements"] == []
    assert result["ambiguous_temperature_streams"] == ["stream"]


def test_negative_enthalpies_have_signed_heat_release_not_negative_flow_claim():
    import copy
    import pytest
    from backend.equipment_costing.unit_conversion.bridges.thermal_screening import (
        enthalpy_pairings,
    )

    observations = [
        {
            "id": "hin",
            "entity_key": "steam",
            "property": "enthalpy_flow",
            "value": -100,
            "unit": "kW",
        },
        {
            "id": "hout",
            "entity_key": "condensate",
            "property": "enthalpy_flow",
            "value": -140000,
            "unit": "W",
        },
    ]
    before = copy.deepcopy(observations)
    result = enthalpy_pairings(
        observations,
        [
            {"entity_key": "steam", "connections": [{"role": "destination"}]},
            {"entity_key": "condensate", "connections": [{"role": "source"}]},
        ],
    )
    assert len(result["pairings"]) == 1
    pair = result["pairings"][0]
    assert pair["hot_release_kw"] == pytest.approx(40)
    assert pair["cold_absorption_kw"] == pytest.approx(-40)
    assert pair["source_measurement_ids"] == ["hin", "hout"]
    assert observations == before
    assert "NOT confirmed" in result["notice"]
