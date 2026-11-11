"""M1.4: sizing failures carry a distinct, machine-readable state.

Missing inputs, invalid inputs and unsupported methods were previously all bare
ValueError told apart only by message text. They remain ValueError subclasses so
every existing caller keeps working.
"""

import math

import pytest

from backend.engineering_sizing import calculate
from backend.engineering_sizing.common import (
    InvalidInputError,
    MissingInputError,
    SizingError,
    UnsupportedMethodError,
    failure_kind,
)

HOLD_UP = {"residence_time_h": 2, "working_fraction": 0.8}


def kind_of(method, value, inputs):
    with pytest.raises(ValueError) as caught:
        calculate(method, value, inputs)
    assert isinstance(caught.value, SizingError)
    return failure_kind(caught.value)


def test_missing_input_is_distinct():
    assert kind_of("vessel_hold_up", 10, {"working_fraction": 0.8}) == "missing_input"
    assert kind_of("pump_duty", 10, {}) == "missing_input"


@pytest.mark.parametrize("value", [-10, 0, math.nan, math.inf, True, "ten"])
def test_invalid_input_is_distinct(value):
    assert kind_of("vessel_hold_up", value, HOLD_UP) == "invalid_input"


def test_invalid_assumption_is_distinct_from_missing():
    assert kind_of("vessel_hold_up", 10, {**HOLD_UP, "working_fraction": -1}) == "invalid_input"


def test_unsupported_method_is_distinct():
    with pytest.raises(UnsupportedMethodError) as caught:
        calculate("reactor_from_vibes", 10, {})
    assert failure_kind(caught.value) == "unsupported_method"


def test_completed_calculation_carries_no_failure_state():
    size, unit, details = calculate("vessel_hold_up", 10, HOLD_UP)
    assert (size, unit) == (pytest.approx(25.0), "m3")
    assert details["engineering_method"]["method_id"] == "vessel_hold_up"


def test_states_remain_value_errors_for_existing_callers():
    for cls in (MissingInputError, InvalidInputError, UnsupportedMethodError):
        assert issubclass(cls, ValueError)
    # Errors raised elsewhere (not typed) default to invalid_input, never "missing".
    assert failure_kind(ValueError("other")) == "invalid_input"
