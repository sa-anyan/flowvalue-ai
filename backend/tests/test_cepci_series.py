"""CEPCI annual series (COST-DATA-V01, 12 Nov 2026).

Values were checked against the publisher. The series is used only when the
policy opts in and the target period has an observation; the default 2026-09
target still uses the CPI proxy until a 2025/2026 CEPCI value is added.
"""

from decimal import Decimal as D

import pytest

from backend.equipment_costing.cost_to_future.cost_translation import (
    DEFAULT_POLICY,
    catalogue,
    translate_cost,
)

CEPCI = catalogue()["series"]["CEPCI"]
OPT_IN_2024 = {
    "target_period": "2024",
    "allow_general_inflation_proxy": True,
    "equipment_index_series": "CEPCI",
}


@pytest.mark.parametrize(
    "year,value",
    [("1987", "323.8"), ("1996", "381.7"), ("1997", "386.5"), ("2001", "394.3"),
     ("2008", "575.4"), ("2016", "541.7"), ("2022", "816.0"), ("2024", "796.2")],
)
def test_verified_values(year, value):
    assert CEPCI["observations"][year]["value"] == value


def test_every_observation_is_cited_annual_usd():
    assert CEPCI["currency"] == "USD" and CEPCI["kind"] == "equipment_index"
    for year, point in CEPCI["observations"].items():
        assert point["frequency"] == "annual_average"
        assert point["source"].startswith(("Chemical Engineering", "Vatavuk"))
        assert point["location"] and point["retrieved"]
    expected = {"1987", "1996", "1997"} | {str(y) for y in range(2000, 2025)}
    assert set(CEPCI["observations"]) == expected


def test_no_unpublished_2025_or_2026_values():
    assert not any(k.startswith(("2025", "2026")) for k in CEPCI["observations"])


def test_default_policy_still_uses_cpi_proxy():
    result = translate_cost(1000, currency="USD", source_period="2016",
                            source_series="SOURCE_PRICE_BASIS", source_index=1.0,
                            policy=DEFAULT_POLICY)
    assert result.status == "general_inflation_proxy"
    assert result.applied_series == "US_CPI_U_NSA_1982_84"


def test_opt_in_escalates_source_year_with_cepci():
    result = translate_cost(1000, currency="USD", source_period="2016",
                            source_series="SOURCE_PRICE_BASIS", source_index=1.0,
                            policy=OPT_IN_2024)
    assert result.status == "equipment_index_ratio"
    assert result.applied_series == "CEPCI"
    assert result.multiplier == pytest.approx(D("796.2") / D("541.7"), rel=D("1e-25"))
    assert "CEPCI" in result.notice


def test_garrett_keeps_its_own_stated_index():
    result = translate_cost(1000, currency="USD", source_period="early 1987",
                            source_series="CEPCI", source_index=320,
                            policy=OPT_IN_2024)
    assert result.status == "same_series_index_ratio"
    assert result.multiplier == pytest.approx(D("796.2") / D("320"), rel=D("1e-25"))


def test_opt_in_without_target_observation_falls_back_to_proxy():
    policy = {**OPT_IN_2024, "target_period": "2026-09"}
    result = translate_cost(1000, currency="USD", source_period="2016",
                            source_series="SOURCE_PRICE_BASIS", source_index=1.0,
                            policy=policy)
    assert result.status == "general_inflation_proxy"


def test_opt_in_never_applies_usd_index_to_gbp():
    result = translate_cost(1000, currency="GBP", source_period="2016",
                            source_series="SOURCE_PRICE_BASIS", source_index=1.0,
                            policy={**OPT_IN_2024, "target_period": "2026-09"})
    assert result.applied_series == "UK_CPI_ALL_ITEMS_2015_100"
