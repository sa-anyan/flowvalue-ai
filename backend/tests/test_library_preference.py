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


def test_openpytea_of_another_family_is_never_chosen():
    # A tank must not be swapped for a pump just because both were listed; the
    # rule looks up OpenPyTEA *tanks* instead.
    result, audit = apply_preference(decision("G303-141", ["G303-141", OPENPYTEA_PUMP]), BY_ID)
    assert result["selected_model_id"] != OPENPYTEA_PUMP
    assert OPENPYTEA_PUMP not in audit["added_from_catalogue"]
    added = [BY_ID[i]["equipment_name"].split(" / ")[0] for i in audit["added_from_catalogue"]]
    assert set(added) <= {"Tanks", "Pressure vessels"}


def test_disabled_listed_model_falls_through_to_usable_catalogue_models():
    # "OpenPyTEA first" means always: a disabled listed model must not stop the
    # search when the catalogue holds usable cyclone/dust-collector models.
    assert BY_ID[DISABLED_CYCLONE]["availability"] == "disabled"
    result, audit = apply_preference(decision(GARRETT_CYCLONE, [GARRETT_CYCLONE, DISABLED_CYCLONE]), BY_ID)
    assert result["selected_model_id"] is None
    assert result["candidate_model_ids"][0] == "openpytea:cyclone_scrubber_turton_2001"
    assert DISABLED_CYCLONE not in audit["added_from_catalogue"]
    assert result["candidate_model_ids"][-2:] == [GARRETT_CYCLONE, DISABLED_CYCLONE] or GARRETT_CYCLONE in result["candidate_model_ids"]


def test_catalogue_lookup_when_the_ai_lists_no_openpytea_model():
    result, audit = apply_preference(decision(GARRETT_PUMP, [GARRETT_PUMP]), BY_ID)
    assert result["selected_model_id"] is None  # configuration chosen at sizing
    assert all(BY_ID[i]["source"] == "openpytea" for i in result["candidate_model_ids"][:-1])
    assert result["candidate_model_ids"][-1] == GARRETT_PUMP  # Garrett kept as fallback
    assert "centrifugal" in result["candidate_model_ids"][0]
    assert audit["replaced"] == GARRETT_PUMP and len(audit["added_from_catalogue"]) <= 8


def test_family_without_openpytea_equivalent_keeps_garrett():
    # Ion exchange has no OpenPyTEA category in the map.
    result, audit = apply_preference(decision("G290-104", ["G290-104"]), BY_ID)
    assert result["selected_model_id"] == "G290-104" and audit is None


def test_user_selected_model_survives_ai_rerun_and_preference():
    from backend.equipment_matching.service import apply_matches

    previous = [{"equipment_key": "e1", "curve_id": GARRETT_PUMP, "source": "garrett",
                 "model_selection": {"origin": "user", "curve_id": GARRETT_PUMP}}]
    rerun = {"matches": [{"equipment_key": "e1", "match_status": "matched", "review_available": True,
                          "selected_model_id": OPENPYTEA_PUMP, "candidate_model_ids": [OPENPYTEA_PUMP, GARRETT_PUMP],
                          "conceptual_validation": "suitable", "source": "openpytea", "reason": "AI rerun"}]}
    row = apply_matches(previous, rerun)[0]
    assert row["curve_id"] == GARRETT_PUMP
    assert row["matching_attempt"]["selected_model_id"] == OPENPYTEA_PUMP  # shown for review only


def test_changed_or_cleared_user_selection_is_not_protected():
    from backend.equipment_matching.library_preference import user_selected_model

    assert user_selected_model({"curve_id": "A", "model_selection": {"origin": "user", "curve_id": "A"}}) == "A"
    assert user_selected_model({"curve_id": "B", "model_selection": {"origin": "user", "curve_id": "A"}}) is None
    assert user_selected_model({"curve_id": "A", "model_selection": None}) is None
    assert user_selected_model({"curve_id": "A", "model_selection": {"origin": "ai", "curve_id": "A"}}) is None


def test_sizing_step_also_states_the_preference():
    from backend.equipment_costing.unit_conversion.bridges.automatic import PROMPT as SIZING

    assert "choose an OpenPyTEA model before any Garrett model" in SIZING


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
