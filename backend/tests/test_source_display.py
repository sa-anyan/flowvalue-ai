"""Display rounding must never become engineering input or erase trace values."""

import pytest

from backend.ingestion.balance.display import source_display
from backend.ingestion.balance.parser import Parser
from backend.ingestion.balance.workbook import Cell, Sheet


@pytest.mark.parametrize(
    "value,mask,expected",
    [
        (0.16486581513528364, "0.0", "0.2"),
        (1.4514764455431945e-05, "0.0", "0.0"),
        (0, "0.0", "0.0"),
        (0.16486581513528364, "0.00", "0.16"),
        (0.125, "0.00%", "12.50%"),
        (1234.5, "#,##0.00", "1,234.50"),
        (-0.01, "0.0", "0.0"),
        (1.25, "0.0", "1.3"),
        (1.45e-5, "0.00E+00", None),
        (1234, "mm-dd-yy", None),
        (0.16, "[Red]0.0", None),
        (True, "0.0", None),
        (None, "0.0", None),
    ],
)
def test_bounded_regex_display_masks(value, mask, expected):
    assert source_display(value, mask) == expected


@pytest.mark.parametrize(
    "component,value,expected",
    [
        ("Chloride", 0.16486581513528364, "0.2"),
        ("Manganese", 1.4514764455431945e-05, "0.0"),
        ("Manganese", 0, "0.0"),
    ],
)
def test_component_cell_retains_exact_value_and_source(component, value, expected):
    sheet = Sheet(
        "Balance",
        {(8, 12): Cell(value, "=G8", cached=True, number_format="0.0")},
        8,
        12,
    )
    parser = Parser(b"fixture", "rounding.xlsx", loaded=([sheet], []))
    evidence = parser.evidence(
        sheet, 8, 12, component, "component_mass_flow", "mass_flow", "kg/hr", component
    )
    assert evidence.original_value == evidence.normalized_value == value
    assert evidence.normalized_unit == "kg/h"
    assert evidence.display_value == expected
    assert evidence.number_format == "0.0"
    assert evidence.sheet == "Balance" and evidence.cell == "L8"
    assert evidence.formula == "=G8" and evidence.cached
