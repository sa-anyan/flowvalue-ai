"""G2 candidate through the existing explicit-stage execution boundary."""

from copy import deepcopy
from decimal import Decimal

from backend.blocks.execution import fresh, run_stage
from backend.orchestration.service import edit
from backend.orchestration.sizing import derive_size
from backend.revenue.authority import update
from backend.tests.test_isolated_stages import study  # noqa: F401


def test_approved_hold_up_edit_propagates_without_duplicate_assets(study):
    store, key = study
    source = store.workbook(key)
    state = run_stage(store, key, "engineering_data")
    update(store, key, state["revision"], approve=True)
    chain = ("equipment", "capex", "revenue", "opex", "financial")
    for stage in chain:
        state = run_stage(store, key, stage)
    assert all(fresh(state, stage) for stage in chain)
    baseline = deepcopy(state)
    version = store.version(key, "Before approved hold-up change")
    def historical_bytes():
        with store.db() as db:
            return db.execute("SELECT state FROM versions WHERE id=?", (version,)).fetchone()[0]

    historical = historical_bytes()

    plan = deepcopy(state["plan"]["equipment"])
    hold_up = plan[0]["sizing"]["parameters"]["residence_time_h"]
    hold_up["value"] = 48
    reason = "Approved: double hold-up at unchanged inlet flow and working fraction"
    state = edit(store, key, state["revision"], "equipment", plan, reason)
    assert all(not fresh(state, stage) for stage in ("equipment", "capex", "opex", "financial"))
    assert fresh(state, "revenue")
    assert state["stage_outputs"] == baseline["stage_outputs"]

    for stage in ("equipment", "capex", "opex", "financial"):
        state = run_stage(store, key, stage)
    assert all(fresh(state, stage) for stage in chain)
    assert state["stage_outputs"]["revenue"] == baseline["stage_outputs"]["revenue"]
    assert state["plan"]["equipment"] == plan
    assert store.workbook(key) == source
    assert historical_bytes() == historical
    assert state["assumptions"]["equipment"]["rationale"] == reason
    assert "equipment" in state["locked"]

    def result(snapshot, stage):
        return snapshot["results"]["stages"][stage]["result"]

    before, = result(baseline, "equipment")["equipment"]
    after, = result(state, "equipment")["equipment"]
    assert before["parsed_source"]["equipment_key"] == after["parsed_source"]["equipment_key"]
    assert before["quantity"] == after["quantity"] == 2
    # 1,000 kg/h / 1,000 kg/m3 * 48 h / 1.0 working fraction.
    for snapshot, line, expected in ((baseline, before, 24), (state, after, 48)):
        trace = line["parsed_source"]["sizing"]
        assert trace["source_evidence"]
        size, unit, _ = derive_size(
            {"sizing": trace["assumptions"]}, snapshot["parsed"]["report"]
        )
        assert (Decimal(str(size)), unit) == (Decimal(expected), "m3")
    before_estimate = before["calculation"]["estimate"]
    after_estimate = after["calculation"]["estimate"]
    assert after_estimate["size"] == before_estimate["size"] * 2
    assert Decimal(result(state, "capex")["total_capex"]) > Decimal(result(baseline, "capex")["total_capex"])
    assert Decimal(result(state, "opex")["first_year_cash_opex"]) > Decimal(result(baseline, "opex")["first_year_cash_opex"])
    def npv(snapshot):
        return Decimal(dict(result(snapshot, "financial")["metrics"])["project_npv"]["value"])

    assert npv(state) < npv(baseline)
