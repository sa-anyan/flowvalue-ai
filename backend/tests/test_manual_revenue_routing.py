"""All six user-selected routes calculate without an LLM call."""
from pathlib import Path
import tempfile
from unittest.mock import patch
import pytest

from backend.orchestration.service import new_assessment, edit, execute
from backend.orchestration.store import Store
from backend.revenue.authority import update
from backend.revenue.validation import CATEGORIES
from backend.tests.test_operating_economics import fixture
from backend.tests.test_revenue_mece import config_line


@pytest.mark.parametrize("category", CATEGORIES)
def test_manual_type_routes_to_python_without_ai(category):
    report, config, _ = fixture()
    config["sales"] = []
    line = config_line(config["financial"]["operating_years"], category)
    line.update(stream_key=None, property="contract_quantity", eligibility_basis="User-supplied eligibility assumption")
    for year in line["years"]:
        year["quantity"] = 100
    config["commercial_lines"] = [line]
    with tempfile.TemporaryDirectory() as folder:
        store = Store(Path(folder) / "test.db")
        state = new_assessment(store, b"fixture", "fixture.xlsx", "Process", "", workflow="revenue")
        state.update(running=False, parsed={"report": report})
        state = store.put(state, state["revision"])
        with patch("backend.orchestration.provider.EngineeringProvider.generate", side_effect=AssertionError("No LLM")):
            state = edit(store, state["id"], state["revision"], "operating_economics", config, "Explicit drawer selection", manual_revenue=True)
            state = update(store, state["id"], state["revision"], approve=True)
            result = execute(store, state["id"], use_ai=False)
        assert not result.get("error")
        revenue = result["results"]["stages"]["revenue"]["result"]
        assert revenue["commercial"][0]["category"] == category
        assert float(revenue["annual"][0]["sales_revenue"]) == 200
