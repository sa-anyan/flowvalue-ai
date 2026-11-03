import json

from backend.orchestration.analyst_team import review_team


def test_large_specialist_contexts_are_bounded_and_retry_independently():
    entities = []
    for i in range(20):
        values = [
            {
                "id": f"c{i}-{j}",
                "property": "component_mass_flow",
                "component": f"X{j}",
                "normalized_value": 0,
                "normalized_unit": "kg/h",
                "original_value": 0,
                "original_unit": "kg/h",
                "sheet": "Process",
                "cell": f"A{j + 1}",
            }
            for j in range(200)
        ]
        values.append(
            {
                "id": f"flow{i}",
                "property": "mass_flow",
                "normalized_value": 100,
                "normalized_unit": "kg/h",
                "original_value": 100,
                "original_unit": "kg/h",
                "sheet": "Process",
                "cell": "B1",
            }
        )
        entities.append(
            {
                "key": f"s{i}",
                "kind": "material",
                "identifier": str(i),
                "id_evidence": {"id": f"id{i}", "sheet": "Process", "cell": "A1"},
                "values": values,
                "stream_keys": [],
            }
        )
        entities.append(
            {
                "key": f"e{i}",
                "kind": "equipment",
                "identifier": f"T-{i}",
                "id_evidence": {"id": f"eid{i}", "sheet": "Process", "cell": "C1"},
                "values": [],
                "stream_keys": [f"s{i}"],
            }
        )

    class Provider:
        model = "fake-no-network"
        calls = 0

        def generate(self, **kwargs):
            self.calls += 1
            assert len(json.dumps(kwargs["context"])) < 200000
            assert any(
                v[kwargs["context"]["value_columns"].index("property")] == "mass_flow"
                for e in kwargs["context"]["entities"]
                for v in e["values"]
            )
            if self.calls == 1:
                raise TimeoutError("Simulated first request timeout")
            return {
                "summary": "Test review",
                "findings": [],
                "sheet_decisions": [],
                "questions": [],
            }

    class Cache:
        def cached(self, key, call):
            return call(), False

    provider = Provider()
    reviews = review_team(
        {"entities": entities, "sheets": [{"name": "Process"}]},
        "Test process",
        "engineering",
        Cache(),
        provider,
    )
    assert len(reviews) == 3
    assert all(r["status"] == "proposed_not_approved" for r in reviews)
    assert reviews[0]["regions"][0]["attempts"] == 2
