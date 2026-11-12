import pytest

from backend.equipment_costing.total_cost.calculator import calculate_total_cost


def record(key, *, tag="T-104", distinct=False, restore=False, amount=10_000):
    return {
        "equipment_tag": tag,
        "manual_price": {
            "amount": amount,
            "currency": "USD",
            "price_period": "1987",
            "source": "Synthetic approved purchase price",
            "notes": "Explicit per-unit purchase cost for testing",
            "cost_scope": "purchased_equipment",
            "approved": True,
        },
        "parsed_source": {
            "equipment_key": key,
            "confirmed_distinct": distinct,
            "duplicate_action": "restore" if restore else "auto",
        },
    }


def test_confirmed_distinct_records_can_share_display_tag():
    result = calculate_total_cost(
        [record("one"), record("two", distinct=True, amount=5_000)]
    )
    assert [line.amount for line in result.equipment] == [10_000, 5_000]
    assert result.total == 15_000
    assert [line.parsed_source["equipment_key"] for line in result.equipment] == [
        "one", "two"
    ]


def test_effective_record_key_must_be_unique_even_across_tags():
    with pytest.raises(ValueError, match="Duplicate equipment record key"):
        calculate_total_cost([record("one"), record("one", tag="T-105", distinct=True)])


@pytest.mark.parametrize("restore", [False, True])
def test_unconfirmed_same_tag_is_rejected_at_costing_boundary(restore):
    with pytest.raises(ValueError, match="Duplicate equipment tag"):
        calculate_total_cost([record("one"), record("two", restore=restore)])
