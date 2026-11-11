from decimal import Decimal

import pytest
from pydantic import ValidationError

from backend.orchestration.monetary_timeline_contracts import MonetaryLine, Timeline


def line(**overrides):
    return MonetaryLine(**{
        "record_key": "equipment:1",
        "amount": "0",
        "status": "present",
        "authority": "provisional",
        "representation": "extended_total",
        "scope": "purchased_equipment",
        "native_basis": {"currency": "USD", "price_year": 2024},
        "source_ref": "quote:1",
        **overrides,
    })


@pytest.mark.parametrize(("change", "issue"), [
    ({"native_basis": {"currency": "GBP", "price_year": 2024}}, "currency"),
    ({"native_basis": {"currency": "USD", "price_year": 2023}}, "price_period"),
    ({"scope": "installed_equipment"}, "scope"),
    ({"representation": "unit_price", "unit": "ft"}, "representation"),
])
def test_incompatible_monetary_metadata(change, issue):
    assert issue in line().comparison_issues(line(**change))


@pytest.mark.parametrize("status", ["missing", "unresolved", "excluded", "not_applicable"])
def test_zero_distinct_from_absent(status):
    absent = line(amount=None, status=status)
    assert absent.amount is None
    assert line().amount == Decimal("0")
    assert line().authority == "provisional"
    assert "amount_status" in line().comparison_issues(absent)
    with pytest.raises(ValidationError, match="Only present"):
        line(status=status)


def test_units_approval_and_translation_are_explicit():
    with pytest.raises(ValidationError, match="denominator"):
        line(representation="unit_price", unit="ft", quantity="2", quantity_unit="m")
    with pytest.raises(ValidationError, match="approval reference"):
        line(authority="approved")
    basis = {"currency": "GBP", "price_year": 2025}
    with pytest.raises(ValidationError, match="translation requires"):
        line(comparison_basis=basis)
    native = line(amount="100", comparison_amount="80", comparison_basis=basis, translation_ref="fx:approved")
    comparable = line(amount="80", native_basis=basis)
    assert native.comparison_issues(comparable) == ()
    assert native.amount == Decimal("100") and native.comparison_amount == Decimal("80")


def test_decimal_and_price_basis_round_trip():
    source = line(amount="0.123456789012345678901", native_basis={
        "currency": "USD", "price_year": 2024, "price_date": "2024-04-09",
        "index_series": "CEPCI", "index_value": "800.10",
    })
    assert source.model_dump(mode="json")["amount"] == "0.123456789012345678901"
    assert MonetaryLine.model_validate_json(source.model_dump_json()) == source
    with pytest.raises(ValidationError, match="decimal text"):
        line(amount=0.1)
    with pytest.raises(ValidationError, match="date and year disagree"):
        line(native_basis={"currency": "USD", "price_year": 2024, "price_date": "2025-01-01"})


@pytest.mark.parametrize("build", [0, 1, 2])
def test_explicit_timeline_coordinates_and_short_commercial_schedule(build):
    periods = [
        {"project_year": i, "calendar_year": 2030 + i, "phase": "construction"}
        for i in range(build)
    ]
    periods.append({"project_year": build, "calendar_year": 2030 + build, "phase": "startup"})
    periods.extend(
        {"project_year": build + year, "calendar_year": 2030 + build + year,
         "phase": "operation", "operating_year": year}
        for year in range(1, 4)
    )
    timeline = Timeline(periods=periods)
    assert timeline.periods[build + 1].project_year == build + 1
    assert timeline.periods[build + 1].calendar_year == 2031 + build
    assert timeline.periods[build + 1].operating_year == 1
    assert timeline.uncovered_operating_years({1, 2}) == (3,)
    assert Timeline.model_validate_json(timeline.model_dump_json()) == timeline
    periods[-1]["operating_year"] = 4
    with pytest.raises(ValidationError, match="advance consecutively"):
        Timeline(periods=periods)
