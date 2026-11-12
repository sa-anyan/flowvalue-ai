"""GARRETT-C01: digitised corrections for Garrett curves that failed GARRETT-V01.

Expected chart values come from pixel-level digitisation of the source pages
(docs/verification/phase3/GARRETT-C01_corrections.md); where the page prints a
size exponent, the traced slope confirms it independently.
"""

import pytest

from backend.equipment_costing.indexes.garrett.integrated import (
    estimate_cost,
    list_models,
)

MODELS = {m["id"]: m for m in list_models()}


def price(curve_id, size):
    return estimate_cost(
        curve_id, size, size_unit=MODELS[curve_id]["size_unit"], allow_unverified=True
    )


# In-range chart values (USD, CE index 320) read from the digitised pages.
CHART = [
    ("G290-104", 1000, 205729),   # ion exchange, 1,000 gpm
    ("G290-104", 100, 22179),
    ("G303-141", 10, 26574),      # horizontal 150 psi tank, 10,000 gal
    ("G303-143", 10, 14083),      # small cone-roof tank, 10,000 gal
    ("G303-144", 10, 5600),       # small storage tank, 10,000 gal
]


@pytest.mark.parametrize("curve_id,size,chart_usd", CHART)
def test_printed_exponent_curves_reproduce_the_chart(curve_id, size, chart_usd):
    # These curves fit a fixed printed exponent to the digitised anchors, so
    # in-range prices sit within a few percent of the traced line.
    result = price(curve_id, size)
    assert not result.estimate.extrapolated
    assert result.amount == pytest.approx(chart_usd, rel=0.05)


def test_conventional_pump_no_longer_reads_from_the_wrong_line():
    # Old readings: 5,000 / 21,000 / 70,000 at 1 / 10 / 100 matched no line.
    # The conventional (AVS) line reads about 2,800 at 10 and 10,600 at 100.
    at_10, at_100 = price("G296-122", 10).amount, price("G296-122", 100).amount
    assert 2400 < at_10 < 3600
    assert 9000 < at_100 < 13000


def test_corrected_curves_keep_their_own_size_units():
    # The correction mechanism previously forced the dryer's size unit on every
    # corrected curve.
    assert MODELS["G296-122"]["size_unit"].startswith("flow × pressure")
    assert MODELS["G303-141"]["size_unit"] == "tank capacity, 1,000 gal"
    assert MODELS["G290-104"]["size_unit"] == "water treated, gpm"
    assert MODELS["G277-060"]["size_unit"] == "actual chamber volume, ft3"
    assert MODELS["G277-062"]["size_unit"] == "actual chamber volume, ft3"


@pytest.mark.parametrize("curve_id,lower,upper", [
    ("G296-122", 1.5, 300), ("G296-123", 8, 50), ("G290-104", 15, 4000),
    ("G303-141", 1.5, 70), ("G303-143", 1.5, 30), ("G303-144", 1.5, 20),
    ("G279-066", 1.5, 150),
])
def test_anchor_range_stays_on_the_printed_line(curve_id, lower, upper):
    assert MODELS[curve_id]["observed_size_range"] == [lower, upper]
    # Beyond the printed line end, a price is an explicit extrapolation.
    assert price(curve_id, upper * 2).estimate.extrapolated


def test_correction_evidence_names_its_page_and_method():
    correction = price("G303-141", 10).evidence["source_correction"]
    assert correction["source"]["printed_page"] == 303
    assert correction["source"]["sha256"].startswith("720cca1e")
    assert "digitisation" in correction["method"]


def test_merged_mixed_axial_pump_curve_is_blocked():
    result = price("G296-124", 100)
    assert result.amount is None
    assert any("two separate lines" in issue for issue in result.issues)
