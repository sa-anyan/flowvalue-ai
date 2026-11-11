"""Founder rule: prefer OpenPyTEA over Garrett when both cover the same equipment."""

from unittest.mock import patch

import pytest

from backend.equipment_matching.library_preference import (
    FAMILY_TO_OPENPYTEA,
    apply_preference,
    openpytea_category,
)
from backend.equipment_matching.service import PROMPT, catalogue, match_report
from backend.orchestration.store import Store

CATALOGUE = catalogue()
BY_ID = {m["model_id"]: m for m in CATALOGUE}
GARRETT_PUMP = "G296-122"
OPENPYTEA_PUMP = "openpytea:centrifugal_1-stage_3600_HSC_seider_2013"
GARRETT_CYCLONE = "G279-066"
DISABLED_CYCLONE = "openpytea:gas_multi_cyclone_ulrich_2003"


def decision(selected, candidates):
    return {"selected_model_id": selected, "candidate_model_ids": list(candidates),
            "match_status": "matched", "conceptual_validation": "suitable"}


def test_family_map_matches_the_live_catalogue():
    garrett = {m["equipment_name"] for m in CATALOGUE if m["source"] == "garrett"}
    openpytea = {openpytea_category(m) for m in CATALOGUE if m["source"] == "openpytea"}
    assert set(FAMILY_TO_OPENPYTEA) <= garrett
    assert set().union(*FAMILY_TO_OPENPYTEA.values()) <= openpytea


def test_garrett_selection_switches_to_same_family_openpytea():
    result, audit = apply_preference(decision(GARRETT_PUMP, [GARRETT_PUMP, OPENPYTEA_PUMP]), BY_ID)
    assert result["selected_model_id"] == OPENPYTEA_PUMP
    assert result["candidate_model_ids"] == [OPENPYTEA_PUMP, GARRETT_PUMP]  # Garrett kept as alternative
    assert audit["applied"] is True and audit["replaced"] == GARRETT_PUMP


def test_openpytea_of_another_family_does_not_replace_garrett():
    # A tank must not be swapped for a pump just because both were listed.
    result, audit = apply_preference(decision("G303-141", ["G303-141", OPENPYTEA_PUMP]), BY_ID)
    assert result["selected_model_id"] == "G303-141" and audit is None


def test_disabled_openpytea_model_keeps_garrett_with_reason():
    assert BY_ID[DISABLED_CYCLONE]["availability"] == "disabled"
    result, audit = apply_preference(decision(GARRETT_CYCLONE, [GARRETT_CYCLONE, DISABLED_CYCLONE]), BY_ID)
    assert result["selected_model_id"] == GARRETT_CYCLONE
    assert audit["applied"] is False and "none can be sized" in audit["reason"]


def test_garrett_only_family_is_left_alone():
    # Buildings have no OpenPyTEA equivalent.
    result, audit = apply_preference(decision("G264-022", ["G264-022"]), BY_ID)
    assert result["selected_model_id"] == "G264-022" and audit is None


def test_family_only_review_lists_openpytea_first():
    result, audit = apply_preference(decision(None, [GARRETT_PUMP, OPENPYTEA_PUMP]), BY_ID)
    assert result["candidate_model_ids"][0] == OPENPYTEA_PUMP and audit is None


def test_prompt_states_the_preference():
    assert "select the OpenPyTEA model" in PROMPT
    assert "without preferring" not in PROMPT


class GarrettChoosingProvider:
    model = "fake"

    def generate(self, *, instructions, context, schema):
        return {"matches": [{
            "equipment_key": "e1", "equipment_function": "Liquid transfer",
            "match_status": "matched", "match_method": "semantic_equivalence",
            "candidate_model_ids": [GARRETT_PUMP, OPENPYTEA_PUMP], "selected_model_id": GARRETT_PUMP,
            "model_scope": "equipment", "conceptual_validation": "suitable",
            "reason": "Centrifugal transfer pump.", "caveats": [], "context_evidence_ids": ["d1"],
        }]}


def test_matcher_enforces_preference_even_when_the_model_picks_garrett(tmp_path):
    report = {"entities": [
        {"key": "e1", "identifier": "P-1", "kind": "equipment",
         "values": [{"property": "name", "normalized_value": "Transfer pump"}],
         "stream_keys": ["s1"], "id_evidence": {"id": "id1", "original_value": "P-1"}},
        {"key": "s1", "identifier": "Water", "kind": "material",
         "values": [{"property": "description", "normalized_value": "Water to pump", "id": "d1"}]},
    ]}
    models = [BY_ID[GARRETT_PUMP], BY_ID[OPENPYTEA_PUMP]]
    with patch("backend.equipment_matching.service.catalogue", return_value=models):
        result = match_report(report, "Water transfer", Store(tmp_path / "c.sqlite"), GarrettChoosingProvider())
    match = result["matches"][0]
    assert match["selected_model_id"] == OPENPYTEA_PUMP
    assert match["source"] == "openpytea"
    assert match["library_preference"]["replaced"] == GARRETT_PUMP
