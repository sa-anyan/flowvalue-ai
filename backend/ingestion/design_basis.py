"""Design-basis parameters from "Parameter / Value / Unit" style tables.

Held-out finding 2: workbooks often state their design basis (specific
electricity, recoveries, heat capacities, temperatures) in parameter tables
outside the stream tables. Those values were parsed as cells but never given
to the AI, which then proposed its own numbers.

This reads the already-parsed source cells, finds a header row that has a
label column ("Parameter", "Energy term", "Item", ...) and a "Value" column,
and returns each labelled row below it, allowing short blank gaps, until
three empty rows or the next table header. Values keep their sheet
and cell. Nothing is converted or calculated, and a row without a numeric
value is skipped. The rows are workbook statements for the AI and the user
to cite, not verified data.
"""

import re

LABEL_HEADERS = {"parameter", "parameters", "energy term", "item", "variable", "quantity", "design parameter",
                 "description", "property", "input"}
VALUE_HEADERS = {"value", "values", "design value"}
UNIT_HEADERS = {"unit", "units", "uom"}
EXTRA_HEADERS = {"type", "basis", "reference", "source", "notes", "note", "classification"}
MAX_ITEMS = 200
_CELL = re.compile(r"^([A-Z]{1,3})(\d+)$")


def _column_number(letters):
    number = 0
    for ch in letters:
        number = number * 26 + ord(ch) - 64
    return number


def _key(text):
    return re.sub(r"\s+", " ", str(text or "")).strip().casefold().rstrip(":")


def _numeric(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def extract(source_cells):
    """Return [{id, sheet, cell, parameter, value, unit, notes}] from parsed cells."""
    grid = {}
    for c in source_cells or []:
        match = _CELL.match(str(c.get("cell", "")))
        if not match:
            continue
        grid.setdefault(c.get("sheet"), {})[(int(match.group(2)), _column_number(match.group(1)))] = c
    items = []
    for sheet, cells in grid.items():
        rows = sorted({r for r, _ in cells})
        for header_row in rows:
            header = {col: _key(cells[(header_row, col)].get("value")) for (r, col) in cells if r == header_row}
            label_cols = [col for col, text in header.items() if text in LABEL_HEADERS]
            value_cols = [col for col, text in header.items() if text in VALUE_HEADERS]
            if not label_cols or not value_cols:
                continue
            label_col, value_col = min(label_cols), min(value_cols, key=lambda c: abs(c - min(label_cols)))
            unit_col = next((col for col, text in sorted(header.items()) if text in UNIT_HEADERS), None)
            extra_cols = {col: text for col, text in header.items() if text in EXTRA_HEADERS}
            row, gap, last = header_row + 1, 0, max(rows)
            while row <= last and gap < 3:
                label = str((cells.get((row, label_col)) or {}).get("value") or "").strip()
                if not label:
                    gap += 1
                    row += 1
                    continue
                gap = 0
                if _key(label) in LABEL_HEADERS:
                    break  # the next table starts here
                value_cell = cells.get((row, value_col))
                if value_cell and _numeric(value_cell.get("value")):
                    unit = cells.get((row, unit_col), {}).get("value") if unit_col else None
                    items.append({
                        "id": f"{sheet}!{value_cell['cell']}",
                        "sheet": sheet,
                        "cell": value_cell["cell"],
                        "parameter": label,
                        "value": value_cell["value"],
                        "unit": str(unit).strip() if unit not in (None, "") else None,
                        "formula": value_cell.get("formula"),
                        "notes": {text: str(cells[(row, col)]["value"]).strip()
                                  for col, text in extra_cols.items()
                                  if (row, col) in cells and str(cells[(row, col)].get("value") or "").strip()},
                    })
                    if len(items) >= MAX_ITEMS:
                        return items
                row += 1
    return items
