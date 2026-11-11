"""Synthetic parser regression inputs; no customer data, formulas or macros.
Run using the existing verification environment (openpyxl/xlwt test dependencies).
"""

from pathlib import Path
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED
import openpyxl
import xlwt

ROOT = Path(__file__).parent
HEADERS = [
    "Stream ID",
    "Description",
    "Mass flow (kg/s)",
    "Volume flow (m3/h)",
    "Heat duty (W)",
    "Temperature (K)",
    "Pressure (bara)",
]
ROWS = [
    ["C-IN", "Gas entering Compressor C-101", 1, None, None, 300, 1],
    ["C-OUT", "Gas leaving Compressor C-101", 1, None, None, 300, 2],
    ["P-IN", "Liquid entering Pump P-101", None, 3.6, None, 300, 1],
    ["H-IN", "Fluid entering Heat Exchanger HE-101", None, None, -100000, 300, 1],
    ["V-IN", "Fluid entering Vaporizer V-101", None, None, 250000, 300, 1],
]


def grids(layout, boolean=None):
    rows = [list(r) for r in ROWS]
    if boolean is not None:
        rows[3][4] = boolean
    if layout == "rows":
        data = [HEADERS, *rows]
    else:
        data = [list(row) for row in zip(HEADERS, *rows)]
    return [
        ("Balance", data),
        (
            "Equipment",
            [
                ["Equipment tag", "Equipment name", "Equipment type"],
                ["C-101", "Compressor", "Compressor"],
                ["P-101", "Pump", "Pump"],
                ["HE-101", "Heat Exchanger", "Heat exchanger"],
                ["V-101", "Vaporizer", "Vaporizer"],
            ],
        ),
    ]


def save(ext, layout, boolean=None, suffix=""):
    name = (
        f"{layout}"
        + suffix
        + ("" if boolean is None else "_bool_" + str(boolean).lower())
        + "."
        + ext
    )
    sheets = grids(layout, boolean)
    if ext == "xls":
        book = xlwt.Workbook()
        for title, grid in sheets:
            ws = book.add_sheet(title)
            for i, row in enumerate(grid):
                for j, v in enumerate(row):
                    if v is not None:
                        ws.write(i + 2, j, v)
            ws.write_merge(0, 0, 0, 3, "Synthetic engineering source — SIZE-C03")
        book.save(str(ROOT / name))
    else:
        book = openpyxl.Workbook()
        book.remove(book.active)
        for title, grid in sheets:
            ws = book.create_sheet(title)
            ws.merge_cells("A1:D1")
            ws["A1"] = "Synthetic engineering source — SIZE-C03"
            for i, row in enumerate(grid, 3):
                for j, v in enumerate(row, 1):
                    if v is not None:
                        ws.cell(i, j, v)
        stream = BytesIO()
        book.save(stream)
        content = stream.getvalue()
        if ext == "xlsm":
            out = BytesIO()
            with ZipFile(BytesIO(content)) as zin, ZipFile(
                out, "w", ZIP_DEFLATED
            ) as zout:
                for item in zin.infolist():
                    value = zin.read(item.filename)
                    if item.filename == "[Content_Types].xml":
                        value = value.replace(
                            b"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml",
                            b"application/vnd.ms-excel.sheet.macroEnabled.main+xml",
                        )
                    zout.writestr(item, value)
            content = out.getvalue()
        (ROOT / name).write_bytes(content)


if __name__ == "__main__":
    for ext in ["xlsx", "xlsm", "xls"]:
        for layout in ["rows", "columns"]:
            save(ext, layout)
        for boolean in [True, False]:
            save(ext, "rows", boolean)

    # Equivalent alternative engineering units, with real values in cells.
    HEADERS[:] = [
        "Stream number",
        "Description",
        "Mass flow (kg/h)",
        "Volumetric flow (L/s)",
        "Heat duty (kW)",
        "Temperature (degC)",
        "Pressure (kPaa)",
    ]
    for row in ROWS:
        if row[2] is not None:
            row[2] *= 3600
        if row[3] is not None:
            row[3] /= 3.6
        if row[4] is not None:
            row[4] /= 1000
        row[5] -= 273.15
        row[6] *= 100
    for ext in ["xlsx", "xlsm", "xls"]:
        save(ext, "rows", suffix="_units")
    HEADERS[6] = "Pressure (barg)"
    for row in ROWS:
        row[6] = row[6] / 100 - 1
    for ext in ["xlsx", "xlsm", "xls"]:
        save(ext, "rows", suffix="_gauge")
    HEADERS[4] = "Heat duty"
    for ext in ["xlsx", "xlsm", "xls"]:
        save(ext, "rows", suffix="_missing_units")
