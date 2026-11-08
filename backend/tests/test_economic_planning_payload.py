"""Economic planning must not resend equipment audit trees or drop CAPEX ranges."""

import copy
import json
from backend.orchestration.planning_context import compact_context


def test_economic_context_keeps_costs_and_bases_without_equipment_audit():
    context = {
        "requested_sections": ["capex"],
        "report": {"entities": [], "connections": []},
        "plan": {
            "equipment": [{"audit": "x" * 10000}],
            "capex": {"delivery_basis": "delivered"},
        },
        "capex_factors": [{"id": "piping", "minimum": ".15", "maximum": ".70"}],
        "calculated_stage_summary": {
            "equipment": {
                "result": {
                    "total_equipment_cost": "123",
                    "input_resolution": [{"audit": "x" * 300000}],
                    "matching_register": {"audit": "x" * 300000},
                    "equipment": [
                        {
                            "equipment_tag": "P-1",
                            "equipment_cost": "123",
                            "quantity": 2,
                            "calculation": {
                                "estimate": {"currency": "USD", "period": "2026"}
                            },
                            "parsed_source": {"audit": "x" * 300000},
                        }
                    ],
                }
            },
            "engineering_data": {
                "result": {"equipment_count": 1, "issues": ["x" * 10000] * 50}
            },
        },
    }
    before = copy.deepcopy(context)
    compact = compact_context(context)
    assert len(json.dumps(compact)) < 10000
    assert compact["capex_factors"] == context["capex_factors"]
    assert compact["plan"]["capex"] == {"delivery_basis": "delivered"}
    line = compact["calculated_stage_summary"]["equipment"]["result"]["equipment"][0]
    assert line["equipment_cost"] == "123" and line["quantity"] == 2
    assert line["price_basis"] == {
        "currency": "USD",
        "period": "2026",
        "index_series": None,
        "index_value": None,
    }
    assert context == before


def test_operating_context_does_not_include_capital_factor_catalogue():
    c = compact_context(
        {
            "requested_sections": ["opex"],
            "report": {"entities": [], "connections": []},
            "plan": {"capex": {"delivery_basis": "delivered"}},
            "capex_factors": [{"id": "piping"}],
        }
    )
    assert c["capex_factors"] == [] and "capex" not in c["plan"]


def test_typed_capital_adapter_requires_bridge_fields_and_published_factors():
    from backend.orchestration.capital_advisor import generate
    from backend.capex import get_factor_ranges

    class Provider:
        def generate(self, *, instructions, context, schema):
            return {
                "process_type": "fluids",
                "delivery_basis": "delivered",
                "selected_factors": {
                    f["id"]: float(f["minimum"])
                    for f in get_factor_ranges("garrett", "mixed")
                    if f["minimum"] is not None and f["additive"]
                },
                "rationale": "Synthetic documented lower-bound test",
                "uncertainty": "Test input",
            }

    response = generate(
        Provider(), "Test", {"report": {"entities": [], "connections": []}}
    )
    config = json.loads(response["sections"][0]["value_json"])
    assert config["delivery_basis"] == "delivered" and config["model_id"] == "garrett"
    assert config["factor_selection"] == "selected" and config["selected_factors"]
