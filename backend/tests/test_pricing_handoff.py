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


def test_partial_equipment_batch_failure_preserves_other_selections():
    from backend.orchestration.advisor import propose

    entities = [
        {
            "key": f"u{i}",
            "kind": "equipment",
            "identifier": f"T-{i}",
            "id_evidence": {"id": f"id{i}", "sheet": "Process", "cell": f"A{i + 1}"},
            "stream_keys": [],
            "values": [],
        }
        for i in range(7)
    ]
    parsed = {
        "report": {"entities": entities, "connections": [], "coverage": "Test"},
        "source_cells": [],
        "source_cells_truncated": False,
    }

    class Provider:
        model = "fake-no-network"

    class Cache:
        def cached(self, key, call):
            return call(), False

    def generate(provider, instructions, context):
        if context["equipment_batch"]["index"] == 2:
            raise ValueError("Fake failure")
        rows = [
            {"equipment_key": e["key"], "curve_id": None, "size": 2, "size_unit": "m3"}
            for e in context["report"]["entities"]
            if e["kind"] == "equipment"
        ]
        return {
            "sections": [
                {
                    "section": "equipment",
                    "value_json": json.dumps(rows),
                    "evidence_ids": [],
                    "uncertainty": "Test",
                },
                {
                    "section": "capex",
                    "value_json": "{}",
                    "evidence_ids": [],
                    "uncertainty": "Test",
                },
            ],
            "questions": [],
        }

    with patch(
        "backend.orchestration.equipment_advisor.generate", side_effect=generate
    ):
        result, _ = propose(
            parsed,
            "Synthetic process",
            {},
            [],
            Cache(),
            Provider(),
            requested_sections=("equipment", "capex"),
        )
    rows = json.loads(
        next(s["value_json"] for s in result["sections"] if s["section"] == "equipment")
    )
    assert len(rows) == 7 and len({r["equipment_key"] for r in rows}) == 7
    assert sum(r["size"] == 2 for r in rows) == 6
    assert next(r for r in rows if r["equipment_key"] == "u6")["size"] is None
    assert len([s for s in result["sections"] if s["section"] == "capex"]) == 1


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
