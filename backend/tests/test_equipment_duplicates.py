import copy
from backend.equipment_resolution.duplicates import reconcile


def source(tags):
    return {
        "entities": [
            {
                "key": str(i),
                "kind": "equipment",
                "identifier": t,
                "values": [],
                "stream_keys": ["s" + str(i)],
            }
            for i, t in enumerate(tags)
        ],
        "connections": [
            {"equipment_key": str(i), "stream_key": "s" + str(i)}
            for i in range(len(tags))
        ],
    }


def test_plain_tag_removed_when_ab_present_with_source_references_retained():
    r = source(["PD-201", "PD-201AB", "FT-201AB", "FT-201"])
    original = copy.deepcopy(r)
    out, _, audit = reconcile(r, {})
    assert [e["identifier"] for e in out["entities"]] == ["PD-201AB", "FT-201AB"]
    assert out["entities"][0]["stream_keys"] == ["s1", "s0"]
    assert len(audit) == 2 and all(a["status"] == "dropped" for a in audit)
    assert r == original
    assert out["connections"][0]["original_equipment_key"] == "0"


def test_normalized_duplicates_but_not_similar_names_or_separate_a_b():
    out, _, a = reconcile(source(["T-104", " T - 104 ", "P-1A", "P-1B", "T-105"]), {})
    assert len(out["entities"]) == 4 and len(a) == 1


def test_restore_persists_and_exclude_again():
    r = source(["FT-201", "FT-201AB"])
    plan = {"equipment": [{"equipment_key": "0", "duplicate_action": "restore"}]}
    for _ in range(2):
        out, plan, a = reconcile(r, plan)
        assert len(out["entities"]) == 2 and a[0]["status"] == "restored"
        assert out["entities"][1]["stream_keys"] == ["s1"]
    plan["equipment"][0]["duplicate_action"] = "auto"
    assert len(reconcile(r, plan)[0]["entities"]) == 1


def test_duplicate_ab_records_resolve_to_single_pair():
    out, _, a = reconcile(source(["P-1", "P-1AB", "P - 1 AB"]), {})
    assert len(out["entities"]) == 1 and out["entities"][0]["identifier"] == "P-1AB"
    assert all(x["retained_equipment_key"] == "1" for x in a)


def test_restored_duplicate_does_not_lose_existing_prices_or_overrides():
    r = source(["P-1", "P-1AB"])
    plan = {
        "equipment": [
            {
                "equipment_key": "0",
                "duplicate_action": "restore",
                "manual_price": {"amount": 123},
            },
            {"equipment_key": "1", "quantity": 2},
        ]
    }
    original = copy.deepcopy(plan)
    _, returned, _ = reconcile(r, plan)
    assert returned == original and plan == original


def test_matching_receives_reconciled_ab_inlet_and_outlet_before_sizing():
    from types import SimpleNamespace
    from unittest.mock import patch
    import pytest
    from backend.blocks.equipment.runner import calculate

    report = source(["PD-201", "PD-201AB"])

    class Seen(Exception):
        pass

    def inspect(report, *args):
        equipment = [e for e in report["entities"] if e["kind"] == "equipment"]
        assert len(equipment) == 1
        assert equipment[0]["identifier"] == "PD-201AB"
        assert set(equipment[0]["stream_keys"]) == {"s0", "s1"}
        raise Seen()

    ctx = SimpleNamespace(
        plan={"equipment": []},
        report=report,
        use_ai=True,
        state={},
        store=None,
        provider=None,
    )
    with patch("backend.blocks.equipment.runner.match_report", side_effect=inspect):
        with pytest.raises(Seen):
            calculate(ctx)
