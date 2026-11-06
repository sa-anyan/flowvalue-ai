import copy
import pytest
from backend.equipment_costing.unit_conversion.bridges.observation_selection import (
    select_observation,
)
from backend.equipment_costing.unit_conversion import convert


def cv(value, unit, target):
    return convert(value, unit, target).value


def source(id, value, status="verified", unit="degC"):
    return dict(id=id, value=value, unit=unit, sheet="Balance", cell=id, status=status)


def test_direct_measurement_precedes_inferred_conflict_and_retains_all_evidence():
    observations = [
        source("ai-evidence:interpretation", 19, "inferred"),
        source("C10", 207),
    ]
    before = copy.deepcopy(observations)
    selected, audit = select_observation(observations, "K", cv)
    assert selected["id"] == "C10"
    assert audit["policy"] == "direct_cell_over_inferred_interpretation"
    assert audit["alternatives_retained"] == [observations[0]]
    assert observations == before


def test_equivalent_direct_readings_converted_without_duplicate_charge():
    selected, audit = select_observation(
        [source("C10", 0), source("D10", 273.15, unit="K")], "K", cv
    )
    assert selected["id"] == "C10"
    assert audit["policy"] == "equivalent_duplicate_readings"


def test_conflicting_direct_measurements_remain_unresolved():
    with pytest.raises(ValueError, match="equally supported"):
        select_observation([source("C10", 20), source("D10", 200)], "K", cv)
