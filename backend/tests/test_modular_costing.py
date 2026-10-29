from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.engine.equipment_costing import garrett, turton_et_al
from app.engine.equipment_costing.models import EquipmentPrice
from app.engine.price_escalation.escalator import escalate_price
from app.engine.price_escalation.models import CostIndex


def index(value, **changes):
    return CostIndex.model_validate(
        dict(
            series="CEPCI",
            basis="1957-1959=100",
            value=value,
            period="1987",
            source="Synthetic test basis",
            status="assumption",
            **changes,
        )
    )


def price(**changes):
    return EquipmentPrice.model_validate(
        {
            "equipment_id": "ANY-001",
            "amount": "100000",
            "currency": "USD",
            "scope": "purchased",
            "method": "parsed_vendor_quote",
            "source_reference": "User-supplied quote, source cell Prices!B2",
            "reference_index": index(320),
            **changes,
        }
    )


def test_any_equipment_price_escalates_without_source_mutation_or_scope_change():
    original = price()
    before = original.model_dump_json()
    result = escalate_price(original, index(800))
    assert result.adjusted_amount == Decimal(250000)
    assert result.index_ratio == Decimal("2.5")
    assert result.original_price.scope == "purchased"
    assert result.currency == "USD"
    assert "assumed" in result.qualification
    assert original.model_dump_json() == before
    assert result.original_price.source_reference.endswith("Prices!B2")


def test_zero_and_deflation_are_explicit_not_missing_prices():
    assert escalate_price(price(amount=0), index(800)).adjusted_amount == 0
    assert escalate_price(price(), index(160)).adjusted_amount == 50000
    with pytest.raises(ValidationError):
        price(amount=None)


def test_missing_basis_and_incompatible_series_or_rebases_fail():
    with pytest.raises(ValueError, match="missing"):
        escalate_price(price(reference_index=None), index(800))
    for target in [
        index(800).model_copy(update={"series": "Marshall Swift"}),
        index(800).model_copy(update={"basis": "2000=100"}),
    ]:
        with pytest.raises(ValueError, match="differ"):
            escalate_price(price(), target)


@pytest.mark.parametrize("value", [0, -1, "NaN", "Infinity"])
def test_invalid_index_rejected(value):
    with pytest.raises(ValidationError):
        index(value)


def test_turton_reference_price_separate_from_escalation():
    # Independent arithmetic at S=100: log10(S)=2.
    expected = 10 ** (4.3247 - 0.3030 * 2 + 0.1634 * 4)
    original = turton_et_al.estimate_base_price("E-101", "heat_exchanger", 100)
    assert float(original.amount) == pytest.approx(expected)
    assert original.reference_index.value == 397
    adjusted = escalate_price(original, index(794))
    assert adjusted.adjusted_amount == original.amount * 2
    assert original.scope == "base_purchase"


def test_unsupported_methods_and_out_of_range_inputs_do_not_fall_back():
    with pytest.raises(NotImplementedError, match="not implemented"):
        garrett.estimate_base_price(equipment_id="P-001", catalog_id="garrett-a1-258")
    with pytest.raises(ValueError, match="Unsupported"):
        turton_et_al.estimate_base_price("X", "bioreactor", 100)
    with pytest.raises(ValueError, match="range"):
        turton_et_al.estimate_base_price("P", "pump", 1000)


def test_author_packages_have_separate_complete_equipment_modules():
    from importlib import import_module

    from app.engine.equipment_catalog import catalog

    entries = {item["id"]: item for item in catalog()["equipment"]}
    assert set(garrett.METHOD_MODULES) == set(entries)
    assert len(set(garrett.METHOD_MODULES.values())) == len(entries)
    for equipment_id, module_name in garrett.METHOD_MODULES.items():
        module = import_module(f"app.engine.equipment_costing.garrett.{module_name}")
        assert module.CATALOG_ID == equipment_id
        assert module.EQUIPMENT_NAME == entries[equipment_id]["name"]
        assert module.SOURCE_REFERENCES == entries[equipment_id]["source_refs"]
        assert module.IMPLEMENTATION_STATUS == "not_implemented"
        with pytest.raises(NotImplementedError):
            module.estimate_base_price(equipment_id="TEST")
    assert len({module.__file__ for module in turton_et_al.METHODS.values()}) == 4
    for kind, module in turton_et_al.METHODS.items():
        assert module.KIND == kind
        assert module.IMPLEMENTATION_STATUS == "screening_method"
