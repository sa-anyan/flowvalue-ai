"""The user's mixed statement retains conditional mechanisms without pricing them."""
import copy
import pytest

from backend.revenue.commercial_intent import validate_intent
from backend.revenue.authority import questions
from backend.tests.test_revenue_authority import ready

PRODUCT = "The plant earns $20 per kg of powder sold."
WATER = "Recycling water could save $0.002 per kg of powder produced."
OXYGEN = "Selling surplus oxygen could bring in $0.034 per kg of powder if a buyer is secured at the assumed price."
CAPACITY = "A separate capacity fee could add $0.05 per kg of powder if agreed with a customer."
TEXT = "\n".join([PRODUCT, WATER, OXYGEN, CAPACITY])


def mixed():
    report, config, _ = ready()
    config["commercial_lines"] = []
    config["sales"][0].update(intent_id="sale", context_quote=PRODUCT, unit_price=20)
    config["commercial_intent"] = {"status": "explicit", "questions": [], "mechanisms": [
        {"id": ident, "category": category, "context_quote": quote, "interpretation": "Stated by user"}
        for ident, category, quote in [("sale", "product_sales", PRODUCT), ("oxygen", "product_sales", OXYGEN), ("capacity", "capacity_availability", CAPACITY)]
    ]}
    config["pending_inputs"] = [
        {"id": ident, "name": ident, "category": category, "context_quote": quote,
         "rate": rate, "rate_unit": "USD/kg powder", "quantity_basis": basis, "missing_inputs": [missing]}
        for ident, category, quote, rate, basis, missing in [
            ("water", "avoided_cost", WATER, 0.002, "kg powder produced", "Identify the existing water expense and production denominator"),
            ("oxygen", "product_sales", OXYGEN, 0.034, "kg powder; not kg oxygen", "Confirm buyer and oxygen quantity/price basis"),
            ("capacity", "capacity_availability", CAPACITY, 0.05, "kg powder", "Confirm customer agreement and billing quantity"),
        ]
    ]
    return report, config


def test_all_four_statements_are_preserved_and_pending_entries_are_not_income():
    report, config = mixed()
    validate_intent(config, TEXT, require=True)
    assert len(config["sales"]) == 1 and config["commercial_lines"] == []
    assert config.get("avoided_costs", []) == []
    assert [x["rate"] for x in config["pending_inputs"]] == [0.002, 0.034, 0.05]
    missing = questions(config, TEXT, report, require_approval=False)
    assert sum(q.startswith("Pending ") for q in missing) == 3
    assert not any("omitted" in q or "exact user-context" in q for q in missing)


def test_pending_opportunity_cannot_also_be_calculated_payment():
    _, config = mixed()
    config["commercial_lines"] = [{"id": "capacity", "intent_id": "capacity", "category": "capacity_availability"}]
    with pytest.raises(ValueError, match="cannot also be calculated"):
        validate_intent(config, TEXT)


def test_pending_opportunities_require_real_quotes_and_matching_categories():
    _, config = mixed()
    wrong = copy.deepcopy(config)
    wrong["pending_inputs"][1]["context_quote"] = "There is a signed oxygen offtake agreement"
    with pytest.raises(ValueError, match="exact user-context"):
        validate_intent(wrong, TEXT)
    config["pending_inputs"][1]["category"] = "capacity_availability"
    with pytest.raises(ValueError, match="match one stated mechanism"):
        validate_intent(config, TEXT)
