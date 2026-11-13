"""M2.3 register keeps reviewed zero and an unresolved assumption distinct."""

from backend.orchestration.register import register


def test_register_exposes_review_origin_and_does_not_fill_missing_assumptions():
    plan = {"equipment": [
        {"sizing": {"value": 0, "unit": "h", "source": "Measured hold-up"}},
        {"sizing": {"value": None, "unit": "h", "status": "unresolved"}},
    ]}
    metadata = {"equipment": {
        "origin": "user_assumption",
        "status": "user_override",
        "rationale": "Reviewed zero and left the other asset unresolved",
    }}
    rows = {row["path"]: row for row in register(plan, metadata)}
    zero = rows["equipment.0.sizing.value"]
    missing = rows["equipment.1.sizing.value"]
    assert zero["value"] == 0 and zero["status"] == "user_override"
    assert zero["source"] == "Measured hold-up"
    assert missing["value"] is None and missing["status"] == "unresolved"
    assert zero["rationale"] == missing["rationale"] == metadata["equipment"]["rationale"]
    assert zero["origin"] == missing["origin"] == "user_assumption"
