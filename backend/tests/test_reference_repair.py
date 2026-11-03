import pytest

from backend.orchestration.reference_repair import repair


def test_reference_repair_retains_values_and_records_inference():
    class Provider:
        def generate(self, **kwargs):
            assert kwargs["schema"]["properties"]["key"]["enum"] == [None, "stream-1"]
            return {"key": "stream-1", "rationale": "Source identity agrees"}

    original = {"sales": [{"id": "sale", "stream_key": "typo", "unit_price": 17.5}]}
    report = {
        "entities": [
            {
                "key": "stream-1",
                "kind": "material",
                "identifier": "Product",
                "values": [],
            }
        ]
    }
    result = repair(original, report, Provider())
    assert result["sales"][0]["stream_key"] == "stream-1"
    assert result["sales"][0]["unit_price"] == 17.5
    assert original["sales"][0]["stream_key"] == "typo"
    assert result["reference_repairs"][0]["status"] == "inferred_review_required"


def test_reference_repair_cannot_invent_key():
    class Provider:
        def generate(self, **kwargs):
            return {"key": "invented", "rationale": "Not supported"}

    with pytest.raises(ValueError, match="Unresolved"):
        repair(
            {"materials": [{"stream_key": "typo"}]},
            {"entities": [{"key": "s", "kind": "material"}]},
            Provider(),
        )


def test_missing_energy_is_not_fabricated():
    from backend.orchestration.reference_repair import repair_energy

    class Provider:
        def generate(self, **kwargs):
            return {
                "power_kw": None,
                "rationale": "Insufficient duty basis",
                "uncertainty": "Unresolved",
            }

    with pytest.raises(ValueError, match="Unresolved energy demand"):
        repair_energy(
            {"energy": [{"id": "heater", "method": "thermal_duty", "power_kw": None}]},
            {"entities": []},
            Provider(),
        )
