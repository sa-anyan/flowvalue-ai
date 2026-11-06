"""Conceptual matching contract, independent of actual model capability."""

import copy
from unittest.mock import patch

from backend.equipment_matching.service import (
    match_report,
    apply_matches,
    equipment_register,
)
from backend.orchestration.store import Store

MODEL = {
    "model_id": "test:pump",
    "source": "garrett",
    "equipment_name": "Pumps",
    "configuration": "Centrifugal",
    "source_page": 1,
}
REPORT = {
    "entities": [
        {
            "key": "e1",
            "identifier": "P-1",
            "kind": "equipment",
            "values": [
                {"property": "name", "normalized_value": "Transfer pump"},
                {"property": "pressure", "normalized_value": 123},
            ],
            "stream_keys": ["s1"],
            "id_evidence": {"id": "id1", "original_value": "P-1"},
        },
        {
            "key": "s1",
            "identifier": "Water",
            "kind": "material",
            "values": [
                {
                    "property": "description",
                    "normalized_value": "Water to pump",
                    "id": "d1",
                },
                {"property": "mass_flow", "normalized_value": 999},
            ],
        },
    ]
}


class Provider:
    model = "fake"
    calls = []

    def generate(self, *, instructions, context, schema):
        self.calls.append(context)
        return {
            "matches": [
                {
                    "equipment_key": "e1",
                    "equipment_function": "Liquid transfer",
                    "match_status": "matched",
                    "match_method": "semantic_equivalence",
                    "candidate_model_ids": ["test:pump"],
                    "selected_model_id": "test:pump",
                    "model_scope": "equipment",
                    "conceptual_validation": "suitable",
                    "reason": "Equivalent liquid-transfer function.",
                    "caveats": [],
                    "context_evidence_ids": ["d1"],
                }
            ]
        }


def run(tmp_path, provider=None):
    with patch("backend.equipment_matching.service.catalogue", return_value=[MODEL]):
        return match_report(
            REPORT,
            "Water transfer process",
            Store(tmp_path / "cache.sqlite"),
            provider or Provider(),
        )


def test_only_equipment_names_and_separate_non_numeric_context(tmp_path):
    Provider.calls = []
    result = run(tmp_path)
    assert result["summary"]["matched"] == 1
    context = Provider.calls[0]
    assert context["equipment_register"] == [
        {
            "equipment_key": "e1",
            "tag": "P-1",
            "names": ["Transfer pump"],
            "raw_names": [],
            "source_name_hints": [],
        }
    ]
    assert "999" not in str(context) and "123" not in str(context)
    assert context["lexical_candidates"]["e1"] == ["test:pump"]
    run(tmp_path)
    assert len(Provider.calls) == 1


def test_unavailable_does_not_clear_previous_model(tmp_path):
    class Failed(Provider):
        def generate(self, **kw):
            raise TimeoutError("test")

    result = run(tmp_path, Failed())
    assert result["summary"]["matched"] == 0
    old = [{"equipment_key": "e1", "curve_id": "old", "size": 9}]
    assert apply_matches(old, result)[0]["curve_id"] == "old"
    assert result["batches"][0]["status"] == "unavailable"


def test_missing_decision_not_silently_dropped(tmp_path):
    class Missing(Provider):
        def generate(self, **kw):
            return {"matches": []}

    result = run(tmp_path, Missing())
    assert len(result["matches"]) == 1
    assert result["summary"]["ambiguous"] == 1


def test_family_match_is_separate_from_selected_configuration(tmp_path):
    class Family(Provider):
        def generate(self, **kw):
            r = super().generate(**kw)
            r["matches"][0]["selected_model_id"] = None
            return r

    result = run(tmp_path, Family())
    assert result["summary"]["matched"] == 1
    assert result["summary"]["selected_configuration"] == 0


def test_component_only_is_not_complete_match(tmp_path):
    class Component(Provider):
        def generate(self, **kw):
            r = super().generate(**kw)
            r["matches"][0]["model_scope"] = "component_only"
            return r

    assert run(tmp_path, Component())["summary"]["matched"] == 0


def test_bad_reference_does_not_establish_match(tmp_path):
    class Bad(Provider):
        def generate(self, **kw):
            r = super().generate(**kw)
            r["matches"][0]["context_evidence_ids"] = ["invented"]
            return r

    assert run(tmp_path, Bad())["summary"]["matched"] == 0


def test_changed_model_cannot_reuse_old_coordinate_or_invent_size(tmp_path):
    result = run(tmp_path)
    old = [
        {
            "equipment_key": "e1",
            "curve_id": "old",
            "size": 9,
            "size_unit": "gal",
            "previous_costing_inputs": {"old": True},
        }
    ]
    new = apply_matches(old, result)[0]
    assert new["curve_id"] == "test:pump"
    assert "size" not in new
    assert new["previous_costing_inputs"]["size"] == 9
    assert "previous_costing_inputs" not in new["previous_costing_inputs"]


def test_family_only_review_preserves_existing_compatible_configuration(tmp_path):
    import copy

    result = run(tmp_path)
    match = result["matches"][0]
    match.update(
        selected_model_id=None,
        match_status="ambiguous",
        conceptual_validation="uncertain",
        candidate_model_ids=["test:pump"],
    )
    old = [
        {
            "equipment_key": "e1",
            "curve_id": "test:pump",
            "unit_conversion": {"enabled": True, "inputs": {"head": 12}},
            "quantity": 2,
            "rationale": "Saved preliminary scenario",
        }
    ]
    original = copy.deepcopy(old)
    out = apply_matches(old, result)[0]
    assert old == original
    assert out["curve_id"] == "test:pump"
    assert out["unit_conversion"] == old[0]["unit_conversion"]
    assert out["quantity"] == 2
    assert out["matching_attempt"] == match
    assert "matching_preservation_reason" in out
    match.update(conceptual_validation="unsuitable", match_status="no_suitable_model")
    assert apply_matches(old, result)[0]["curve_id"] is None
    match.update(
        conceptual_validation="uncertain",
        match_status="ambiguous",
        candidate_model_ids=["different:model"],
    )
    assert apply_matches(old, result)[0]["curve_id"] is None


def test_source_words_add_tank_hint_without_tag_guessing():
    from backend.equipment_matching.service import lexical_candidates

    models = [
        {"model_id": "tank:model", "equipment_name": "Tanks"},
        {"model_id": "blower:model", "equipment_name": "Blowers"},
    ]
    source = {
        "tag": "T-301",
        "names": ["Packaging station"],
        "raw_names": ["Dry product entering Packaging Tank T-301"],
    }
    assert lexical_candidates(source, models) == ["tank:model"]
    assert lexical_candidates({"names": ["PD-201AB"], "raw_names": []}, models) == []


def test_upstream_name_is_not_an_exact_match_for_target_tag():
    from backend.equipment_matching.service import lexical_candidates, source_name_hints

    models = [
        {"model_id": "centrifuge", "equipment_name": "Centrifuges"},
        {"model_id": "tank", "equipment_name": "Tanks"},
    ]
    row = {
        "tag": "PD-201AB",
        "names": ["Centrifuge"],
        "raw_names": ["Food leaving Centrifuge S-201 entering PD-201AB"],
    }
    assert source_name_hints(row) == []
    assert lexical_candidates(row, models) == []
    row = {
        "tag": "T-301",
        "names": ["Packaging station"],
        "raw_names": [
            "Dry food leaving Centrifuge S-201 entering Packaging Tank T - 301"
        ],
    }
    assert lexical_candidates(row, models) == ["tank"]


def test_separate_name_cell_still_supplies_exact_word_hint():
    from backend.equipment_matching.service import lexical_candidates

    row = {"tag": "TK-900", "names": ["Storage"], "raw_names": ["Storage tank"]}
    models = [{"model_id": "tank", "equipment_name": "Tanks"}]
    assert lexical_candidates(row, models) == ["tank"]


def test_catalogue_exposes_unusable_coordinates_without_source_prices():
    from backend.equipment_matching.service import catalogue
    rows={r['model_id']:r for r in catalogue()}
    assert rows['G297-126']['coordinate_issues']
    assert rows['N501-PUMP-STAINLESS_316']['size_inputs']==[{'quantity':'power','unit':'kW'}]
    assert 'PD slurry service' in rows['N501-PUMP-STAINLESS_316']['limitation']
    assert all('points'not in row and 'amount'not in row for row in rows.values())
