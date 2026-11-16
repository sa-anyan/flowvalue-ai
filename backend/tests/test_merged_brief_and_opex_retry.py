"""One user brief, explicit OPEX retries and no replacement of saved inputs."""

from backend.blocks.opex import brainstorm
from backend.revenue.authority import bind, commercial_text


def test_background_adapter_retains_opex_only_section(tmp_path, monkeypatch):
    import json
    from backend.orchestration import operating_advisor
    from backend.tests.test_opex_brainstorm import _extracted
    store, key = _extracted(tmp_path)
    response = {"sections": [{"section": "operating_economics", "value_json": json.dumps({
        "labour": [{"id": "ops", "headcount_fte": 5}]
    }), "evidence_ids": [], "uncertainty": "Synthetic", "rationale": "Synthetic", "units": "FTE"}],
                "source_review": [], "questions": []}
    monkeypatch.setattr(operating_advisor, "generate", lambda *args, **kwargs: response)
    class Provider:
        model = "test"
    values, meta = brainstorm._propose(store.get(key), store, Provider())
    assert values["labour"][0]["headcount_fte"] == 5


def test_opex_only_proposal_never_runs_revenue_validation(monkeypatch):
    import json
    from backend.orchestration import operating_advisor, reference_repair

    monkeypatch.setattr(operating_advisor, "validate", lambda *args: None)
    def forbidden(*args, **kwargs):
        raise AssertionError("OPEX cannot be blocked by revenue validation")
    monkeypatch.setattr("backend.revenue.commercial_intent.validate_intent", forbidden)
    monkeypatch.setattr(reference_repair, "repair", lambda value, *args: value)
    monkeypatch.setattr(reference_repair, "repair_energy", lambda value, *args: value)
    class Provider:
        def generate(self, *, instructions, context, schema):
            assert "commercial_intent" not in schema["properties"]
            assert "sales" not in schema["properties"]
            return {"financial": {}, "questions": [], "materials": [], "energy": [],
                    "labour": [{"id": "operators", "headcount_fte": 5, "annual_base_salary": 50000}]}
    result = operating_advisor.generate(Provider(), "", {
        "plan": {"cost_translation": {"target_period": "2026-09"}},
        "report": {"entities": [], "connections": []}, "revenue_box": "Lignin is sold."
    }, opex_only=True)
    value = json.loads(result["sections"][0]["value_json"])
    assert len(value["labour"]) == 1


def test_income_intent_comes_from_process_brief_without_a_second_box():
    state = {"id": "test", "process_description": "Treat wastewater. Lignin is sold.", "revenue_description": ""}
    assert commercial_text(state) == state["process_description"]
    bind(state)
    assert state["plan"]["revenue_authority"]["text"] == state["process_description"]
    assert not state.get("revenue_approval")


def test_legacy_income_statement_is_preserved_without_duplicate_text():
    state = {"process_description": "Treat wastewater.", "revenue_description": "We charge a treatment fee."}
    assert commercial_text(state) == "We charge a treatment fee."
    # Entry combines the legacy inputs visibly; saving that edit adopts the brief.
    state["process_description"] += "\n\n" + state["revenue_description"]
    state["revenue_description"] = state["process_description"]
    assert commercial_text(state).count("We charge a treatment fee.") == 1


def test_explicit_retry_fills_missing_prices_but_preserves_existing_prices():
    def feed(id, price):
        return {"id": id, "stream_key": id, "property": "mass_flow", "component": None,
                "quantity_unit": "kg", "unit_price": price, "origin": "user"}
    config = {"materials": [feed("acid", None), feed("sugar", 2)]}
    proposed = {"materials": [feed("acid", 0.4), feed("sugar", 999)],
                "price_basis": {"currency": "USD", "price_period": "2026-09"},
                "labour": [{"id": "ops", "headcount_fte": 5, "annual_base_salary": 50000}]}
    updated, added = brainstorm.merge(config, proposed, fill_missing=True)
    assert updated["materials"][0]["unit_price"] == 0.4
    assert updated["materials"][0]["ai_price_proposal"]["status"] == brainstorm.STATUS
    assert updated["materials"][1]["unit_price"] == 2
    assert updated["labour"][0]["headcount_fte"] == 5
    assert config["materials"][0]["unit_price"] is None


def test_retry_status_is_running_even_when_the_inputs_have_not_changed(monkeypatch):
    monkeypatch.setitem(brainstorm._live, "retry-test", {"status": "running", "fingerprint": "same"})
    state = {"opex_brainstorm": {"status": "ready", "fingerprint": "same"}}
    assert brainstorm.status("retry-test", state)["status"] == "running"
