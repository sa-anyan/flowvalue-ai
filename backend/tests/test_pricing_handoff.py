"""Planning handoff uses bounded data and canonical Python sizing."""

import json
from unittest.mock import patch

import pytest

from backend.orchestration.planning_context import compact_context, equipment_batches
from backend.orchestration.sizing import derive_size


def test_planning_keeps_design_totals_and_full_original_evidence():
    value = {
        "requested_sections": ["equipment", "capex"],
        "report": {
            "entities": [
                {
                    "key": "u",
                    "identifier": "T-1",
                    "kind": "equipment",
                    "stream_keys": ["s"],
                    "values": [{"property": "type", "value": "Tank"}],
                },
                {
                    "key": "s",
                    "kind": "material",
                    "values": [
                        {"property": "mass_flow", "value": 1000},
                        {"property": "component_mass_flow", "value": 1000},
                    ],
                },
            ],
            "connections": [
                {
                    "stream_key": "s",
                    "equipment_key": "u",
                    "role": "destination",
                    "evidence_ids": ["v1"],
                }
            ],
        },
        "parsed_revenue_streams": [{"duplicate": True}],
    }
    compact = compact_context(value)
    assert len(value["report"]["entities"][1]["values"]) == 2
    assert compact["report"]["entities"][1]["values"] == [
        {"property": "mass_flow", "value": 1000}
    ]
    assert compact["parsed_revenue_streams"] == []
    assert next(iter(equipment_batches(compact)))["report"]["entities"][1]["key"] == "s"


def test_mass_residence_and_volume_throughput_use_explicit_density():
    report = {
        "entities": [
            {
                "key": "feed",
                "values": [
                    {
                        "id": "v1",
                        "property": "mass_flow",
                        "normalized_value": 1000,
                        "normalized_unit": "kg/h",
                        "status": "inferred",
                    }
                ],
            }
        ]
    }
    sizing = {
        "method": "mass_residence",
        "stream_key": "feed",
        "density_kg_m3": 1000,
        "residence_time_h": 2,
        "working_fraction": 0.8,
    }
    size, unit, evidence = derive_size({"sizing": sizing}, report)
    assert size == 2.5 and unit == "m3"
    assert evidence["assumptions"]["density_kg_m3"] == 1000
    sizing["method"] = "mass_to_volume_flow"
    assert derive_size({"sizing": sizing}, report)[:2] == (1, "m3/h")
    for density in (None, 0, -1, "NaN"):
        sizing["density_kg_m3"] = density
        with pytest.raises(ValueError):
            derive_size({"sizing": sizing}, report)


def test_partial_equipment_batch_failure_preserves_other_selections(tmp_path):
    from backend.equipment_matching.service import match_report
    from backend.orchestration.store import Store
    from backend.tests.test_equipment_matching import Provider, MODEL, REPORT
    import copy

    report = copy.deepcopy(REPORT)
    for i in range(1, 3):
        entity = copy.deepcopy(REPORT["entities"][0])
        entity["key"] = f"e{i+1}"
        report["entities"].append(entity)

    class Partial(Provider):
        def generate(self, **kw):
            key = kw["context"]["equipment_register"][0]["equipment_key"]
            if key == "e2":
                raise TimeoutError("Independent failed batch")
            result = super().generate(**kw)
            result["matches"][0]["equipment_key"] = key
            return result

    with patch("backend.equipment_matching.service.BATCH_SIZE", 1), patch(
        "backend.equipment_matching.service.catalogue", return_value=[MODEL]
    ):
        result = match_report(
            report, "Water transfer", Store(tmp_path / "partial.sqlite"), Partial()
        )
    assert result["summary"]["matched"] == 2
    assert len(result["matches"]) == 3
    assert [b["status"] for b in result["batches"]] == [
        "matched",
        "unavailable",
        "matched",
    ]


def test_correction_batches_only_target_failed_equipment():
    context = {
        "report": {
            "entities": [
                {
                    "key": "a",
                    "identifier": "T-1",
                    "kind": "equipment",
                    "stream_keys": [],
                    "values": [],
                },
                {
                    "key": "b",
                    "identifier": "T-2",
                    "kind": "equipment",
                    "stream_keys": [],
                    "values": [],
                },
            ],
            "connections": [],
        },
        "plan": {
            "equipment": [
                {"equipment_key": "a", "size": 1},
                {"equipment_key": "b", "size": 2},
            ]
        },
        "calculated_stage_summary": {"engineering_errors": [{"equipment_tag": "T-2"}]},
    }
    batches = list(equipment_batches(context))
    assert len(batches) == 1 and batches[0]["equipment_batch"]["keys"] == ["b"]
    assert batches[0]["plan"]["equipment"] == [{"equipment_key": "b", "size": 2}]
    assert context["plan"]["equipment"][0]["size"] == 1
