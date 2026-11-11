"""Nearest real graph boundary -> canonical C2=C1*(S2/S1)**n."""

import pytest
from backend.equipment_costing.registry import estimate_cost, list_equipment_models


def cost(identifier, size, **options):
    model = next(m for m in list_equipment_models() if m["id"] == identifier)
    return estimate_cost(identifier, size, size_unit=model["size_unit"], **options)


# GARRETT-C01: boundaries are the digitised ends of the printed cyclone line
# (1,500 to 150,000 cfm). The earlier readings (20 -> $5,000, 700 -> $65,000)
# misread the size axis by about 3x.
@pytest.mark.parametrize(
    "size,boundary,reference", [(0.28753362139945604, 1.5, 1467.0), (1400, 150, 58502.0)]
)
def test_cyclone_lower_and_upper_boundary(size, boundary, reference):
    result = cost("G279-066", size, allow_unverified=True)
    assert result.amount is not None
    assert result.estimate.anchor_size == boundary
    assert result.estimate.anchor_cost == reference
    assert result.amount == pytest.approx(
        reference * (size / boundary) ** result.estimate.exponent
    )
    assert "not a printed Garrett exponent" in result.estimate.exponent_basis
    assert any("PROVISIONAL BOUNDARY" in issue for issue in result.issues)


def test_strict_policy_and_graph_permission_remain_available():
    assert cost("G279-066", 0.3).amount is None
    assert (
        cost(
            "G279-066", 0.3, allow_unverified=True, allow_fitted_extrapolation=False
        ).amount
        is None
    )


def test_explicit_exponent_preserves_precedence_and_requires_rationale():
    assert (
        cost("G279-066", 0.3, allow_unverified=True, extrapolation_exponent=0.6).amount
        is None
    )
    result = cost(
        "G279-066",
        0.3,
        allow_unverified=True,
        extrapolation_exponent=0.6,
        extrapolation_justification="Explicit test scenario",
    )
    assert result.estimate.exponent == 0.6
    assert "Caller-supplied" in result.estimate.exponent_basis


def test_in_range_results_unchanged_and_missing_models_not_invented():
    # 50,000 cfm lies inside the printed cyclone line (GARRETT-C01).
    a = cost("G279-066", 50, allow_unverified=True)
    b = cost("G279-066", 50, allow_unverified=True, allow_fitted_extrapolation=False)
    assert a.amount == b.amount and not a.estimate.extrapolated
    with pytest.raises(ValueError):
        estimate_cost(
            "not-an-equipment-model", 10, size_unit="kg/h", allow_unverified=True
        )
    assert cost("G306-154", 1, allow_unverified=True).amount is None


@pytest.mark.parametrize("identifier", ["G265-023", "G296-122", "G298-132"])
def test_shared_policy_applies_beyond_cyclone(identifier):
    model = next(m for m in list_equipment_models() if m["id"] == identifier)
    lower = model["observed_size_range"][0]
    result = cost(identifier, lower / 10, allow_unverified=True)
    assert result.amount is not None
    assert result.estimate.extrapolated
