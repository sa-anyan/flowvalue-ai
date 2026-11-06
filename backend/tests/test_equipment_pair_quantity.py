"""Paired purchasing quantities never double the equipment sizing coordinate."""

import pytest
from backend.blocks.equipment.quantity import equipment_quantity
from backend.blocks.equipment.calculation import calculate_equipment


@pytest.mark.parametrize(
    "tag", ["P-101AB", "FT-201AB", "BL-201A/B", "T-101 AB", "pd-201ab"]
)
def test_pair_count(tag):
    assert equipment_quantity({}, tag) == (2, "founder_AB_pair_convention")


@pytest.mark.parametrize("tag", ["P-101A", "P-101B", "LAB", "AB-101", "P-101ABC"])
def test_other_tags_not_pairs(tag):
    assert equipment_quantity({}, tag)[0] == 1


def test_explicit_quantity_preserved():
    assert equipment_quantity({"quantity": 3}, "P-101AB") == (
        3,
        "explicit_scenario_quantity",
    )


def test_canonical_pricing_extends_purchase_installation_but_not_size():
    report = {
        "entities": [
            {
                "key": "e",
                "kind": "equipment",
                "identifier": "T-9AB",
                "values": [],
                "stream_keys": [],
            }
        ]
    }
    item = {
        "equipment_key": "e",
        "source": "garrett",
        "curve_id": "G258-008",
        "size": 100,
        "size_unit": "US_gal",
        "costing_options": {"allow_unverified": True, "unit_context": {"target_gallon_basis": "US"}},
    }
    pair, rows = calculate_equipment(report, {"equipment": [item]})
    single, _ = calculate_equipment(report, {"equipment": [{**item, "quantity": 1}]})
    a, b = pair.equipment[0], single.equipment[0]
    assert a.equipment_cost is not None and a.installation_cost is not None
    assert a.quantity == 2
    assert a.equipment_cost == pytest.approx(2 * b.equipment_cost)
    assert a.installation_cost == pytest.approx(2 * b.installation_cost)
    assert a.equipment_and_installation_cost == pytest.approx(
        2 * b.equipment_and_installation_cost
    )
    assert a.calculation.estimate.size == b.calculation.estimate.size
    assert rows[0]["parsed_source"]["quantity_basis"] == "founder_AB_pair_convention"
