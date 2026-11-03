"""Independent founder workflow cases; no live provider or legacy formulas."""

import copy
import json
from unittest.mock import patch

import pytest

from backend.engineering_sizing import calculate
from backend.orchestration.design_handoff import complete
from backend.orchestration.sizing import derive_size


def test_ion_exchange_example_is_python_calculated():
    size, unit, audit = calculate(
        "ion_exchange_ebct",
        10,
        {"empty_bed_contact_time_min": 15, "resin_bed_fraction": 0.7},
    )
    assert size == pytest.approx(25 / 7)
    assert unit == "m3"
    assert audit["resin_bed_volume_m3"] == 2.5
    with pytest.raises(ValueError, match="exceed"):
        calculate(
            "ion_exchange_ebct",
            10,
            {"empty_bed_contact_time_min": 15, "resin_bed_fraction": 1.1},
        )


def test_edited_parameters_supersede_legacy_scalar():
    report = {
        "entities": [
            {
                "key": "s",
                "values": [
                    {
                        "property": "mass_flow",
                        "normalized_value": 1000,
                        "normalized_unit": "kg/h",
                        "id": "v",
                    }
                ],
            }
        ]
    }
    p = {
        "sizing": {
            "method": "mass_residence",
            "stream_key": "s",
            "density_kg_m3": 1000,
            "residence_time_h": 1,
            "working_fraction": 1,
            "parameters": {"residence_time_h": {"value": 2, "unit": "h"}},
        }
    }
    assert derive_size(p, report)[0] == 2


class Cache:
    def __init__(self):
        self.values = {}

    def cached(self, key, call):
        key = json.dumps(key, sort_keys=True)
        if key in self.values:
            return self.values[key], True
        value = call()
        self.values[key] = value
        return value, False


def test_design_handoff_retries_missing_record_and_preserves_priced_units():
    report = {
        "entities": [
            {
                "key": "e",
                "identifier": "P-1AB",
                "kind": "equipment",
                "stream_keys": [],
                "values": [],
            },
            {"key": "ok", "identifier": "T-1", "kind": "equipment", "values": []},
        ],
        "connections": [],
    }
    plan = {
        "equipment": [
            {"equipment_key": "e", "curve_id": None},
            {"equipment_key": "ok", "size": 123},
        ],
        "engineering_policy": {
            "duty_standby_suffixes": {
                "AB": {"duty": 1, "standby": 1, "source": "User design basis"}
            }
        },
    }
    original = copy.deepcopy(plan)

    def result(report, description, plan):
        return {
            "stages": {
                "equipment": {
                    "result": {
                        "equipment": [
                            {
                                "equipment_cost": None,
                                "equipment_tag": "P-1AB",
                                "curve_id": None,
                                "parsed_source": {"equipment_key": "e"},
                                "decision": {},
                            },
                            {
                                "equipment_cost": 123,
                                "equipment_tag": "T-1",
                                "parsed_source": {"equipment_key": "ok"},
                            },
                        ]
                    }
                }
            }
        }

    responses = [
        {"sections": [{"section": "equipment", "value_json": "[]"}]},
        {
            "sections": [
                {
                    "section": "equipment",
                    "value_json": json.dumps(
                        [{"equipment_key": "e", "curve_id": None}]
                    ),
                }
            ]
        },
    ]
    with (
        patch("backend.orchestration.design_handoff.run", side_effect=result),
        patch(
            "backend.orchestration.design_handoff.generate", side_effect=responses
        ) as generate,
    ):
        actual, audits = complete(report, "User process", plan, [], Cache(), object())
    assert generate.call_count == 2
    assert audits[0]["attempts"] == 2
    assert actual["equipment"][1] == original["equipment"][1]
    assert actual["equipment"][0]["quantity"] == 2
    assert plan == original


def test_locked_equipment_cannot_be_rewritten():
    plan = {"equipment": [{"equipment_key": "e", "size": 123}]}
    with patch("backend.orchestration.design_handoff.generate") as provider:
        actual, audits = complete({}, "", plan, ["equipment"], None, object())
    assert actual == plan
    assert not provider.called
    assert audits[0]["status"] == "skipped_locked_or_unavailable"
