"""Independent HYSYS-style export fixtures; no third-party workbook is redistributed."""

from io import BytesIO

from openpyxl import Workbook

from app.parsers.balance import parse_excel
from app.parsers.inputs.aspen_hysys_excel import parse_hysys_excel


def sample(rows, prefix=()):
    book = Workbook()
    sheet = book.active
    sheet.title = "HYSYS stream results"
    for row in prefix:
        sheet.append(row)
    for row in rows:
        sheet.append(row)
    buffer = BytesIO()
    book.save(buffer)
    return buffer.getvalue()


def streams():
    return [
        ["", "Units", "S-101", "S-102"],
        ["Phase", "", "Vapour", "Liquid"],
        ["Temperature", "C", 32, 90],
        ["Pressure", "bar(a)", 1.5, 3.0],
        ["Molar Enthalpy", "kJ/kmol", 200, 450],
        ["Mass Enthalpy", "kJ/kg", 12.5, 15.8],
        ["Mass Density", "kg/m3", 1.2, 920],
        ["Mole Flows", "kmol/h", 18, 12],
        ["Methane", "kmol/h", 14, 0],
        ["Water", "kmol/h", 4, 12],
        ["Mass Flows", "kg/h", 240, 380],
        ["Methane", "kg/h", 224, 0],
        ["Water", "kg/h", 16, 380],
        ["Vapor Phase", None, None, None],
    ]


def prop(entity, name, component=None):
    return next(
        value for value in entity.values
        if value.property == name and value.component == component
    )


def test_hysys_properties_and_components_to_canonical_evidence():
    report = parse_hysys_excel(sample(streams()), "hysys-export.xlsx")
    assert report.schema_version == "flowvalue-balance-v1"
    assert len(report.tables) == 1
    assert report.tables[0].orientation == "records_in_columns"
    assert [entity.identifier for entity in report.entities] == ["S-101", "S-102"]
    a, b = report.entities
    assert a.id_evidence.cell == "C1"
    assert prop(a, "phase").normalized_value == "vapor"
    assert prop(a, "temperature").normalized_value == 32
    assert prop(a, "pressure").normalized_unit == "bar_abs"
    assert prop(a, "mass_flow").normalized_value == 240
    assert prop(a, "molar_flow").normalized_value == 18
    assert prop(a, "specific_enthalpy").normalized_unit in ("kJ/kg", "kJ/kmol")
    assert prop(a, "density").normalized_value == 1.2
    assert prop(a, "mass_flow", "Methane").normalized_value == 224
    assert prop(a, "molar_flow", "Water").normalized_value == 4
    assert prop(b, "mass_flow", "Methane").normalized_value == 0
    assert prop(b, "mass_flow", "Water").cell == "D13"
    assert prop(b, "mass_flow", "Water").original_unit == "kg/h"
    assert report.sha256 and not any(i.code == "no_tables" for i in report.issues)


def test_hysys_no_fixed_row_numbers_and_safe_unit_conversion():
    rows = streams()
    rows[2][1] = "K"
    rows[2][2] = 300
    rows[3][1] = "psia"
    rows[3][2] = 14.6959
    report = parse_hysys_excel(
        sample(rows, prefix=[["Run data"], ["HYSYS Results"], [""]]),
        "shifted.xlsx",
    )
    a = report.entities[0]
    assert a.id_evidence.cell == "C4"
    assert abs(prop(a, "temperature").normalized_value - 26.85) < 1e-7
    assert abs(prop(a, "pressure").normalized_value - 1.01325) < 0.001
    assert prop(a, "temperature").cell == "C6"


def test_unresolved_units_and_unsupported_hysys_format_remain_explicit():
    rows = streams()
    rows[3][1] = "bar"  # no absolute/gauge basis
    report = parse_hysys_excel(sample(rows), "ambiguous.xlsx")
    pressure = prop(report.entities[0], "pressure")
    assert pressure.status == "unresolved"
    assert pressure.normalized_value is None
    assert any(i.code == "unresolved_value" for i in report.issues)

    ordinary = sample([
        ["Stream ID", "Mass flow [kg/h]", "Temperature [C]", "Pressure [bara]", "Phase"],
        ["S1", 100, 25, 1.2, "liquid"],
    ])
    generic = parse_excel(ordinary, "ordinary.xlsx")
    requested_hysys = parse_hysys_excel(ordinary, "ordinary.xlsx")
    assert len(requested_hysys.entities) == len(generic.entities)
    assert any(i.code == "hysys_layout_unrecognised" for i in requested_hysys.issues)


def test_selected_hysys_returns_standard_balance_schema():
    report = parse_hysys_excel(sample(streams()), "selected-hysys.xlsx")
    assert report.schema_version == "flowvalue-balance-v1"
    assert report.sheets[0]["tables"] == 1
