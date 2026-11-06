"""A missing coordinate is one explicit exception, never a plant-wide crash."""

from backend.equipment_costing.total_cost.calculator import calculate_total_cost


def test_missing_size_does_not_discard_valid_equipment():
    base = {
        "source": "garrett",
        "curve_id": "G258-004",
        "size_unit": "gal",
        "costing_options": {"allow_unverified": True},
    }
    result = calculate_total_cost(
        [
            {**base, "equipment_tag": "TK-MISSING", "size": None},
            {**base, "equipment_tag": "TK-VALID", "size": 100},
        ]
    )
    assert result.equipment[0].equipment_cost is None
    assert any("Sizing input missing" in issue for issue in result.equipment[0].issues)
    assert result.equipment[1].equipment_cost is not None


def test_nottingham_native_handoff_keeps_conversion_context_out_of_correlation():
    from backend.blocks.equipment.calculation import calculate_equipment

    report = {
        "entities": [
            {
                "key": "pump",
                "identifier": "P-9",
                "kind": "equipment",
                "values": [],
                "stream_keys": [],
            }
        ]
    }
    plan = {
        "equipment": [
            {
                "equipment_key": "pump",
                "curve_id": "N501-PUMP-STAINLESS_316",
                "size": 1,
                "size_unit": "kW",
                "quantity": 2,
                "costing_options": {
                    "unit_context": {"atmospheric_pressure_pa": 101325}
                },
            }
        ]
    }
    total, rows = calculate_equipment(report, plan)
    assert total.equipment[0].equipment_cost is not None
    assert "unit_context" not in rows[0]["costing_options"]
    assert (
        rows[0]["parsed_source"]["sizing"]["native_costing_handoff"][
            "conversion_context"
        ]["atmospheric_pressure_pa"]
        == 101325
    )
    plan["equipment"][0].update(size=1000, size_unit="W")
    converted, _ = calculate_equipment(report, plan)
    assert converted.equipment[0].equipment_cost == total.equipment[0].equipment_cost
