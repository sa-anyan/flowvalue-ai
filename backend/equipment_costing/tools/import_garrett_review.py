"""Explicit offline importer; never runs workbook formulas or imports at runtime.

Requires openpyxl only for offline extraction. Runtime engine uses stdlib JSON.
"""

import argparse
import hashlib
import json
from pathlib import Path


def build(workbook_path, pdf_path, output):
    from openpyxl import load_workbook

    workbook_path, pdf_path = Path(workbook_path), Path(pdf_path)
    workbook = load_workbook(
        workbook_path, read_only=True, data_only=True, keep_links=False
    )
    formula_book = load_workbook(
        workbook_path, read_only=True, data_only=False, keep_links=False
    )
    curves = []
    lookup = {}
    for rownum, row in enumerate(
        workbook["Curve Register"].iter_rows(min_row=2, values_only=True), 2
    ):
        if not row[0]:
            continue
        curve = dict(
            zip(
                (
                    "id",
                    "equipment_number",
                    "printed_page",
                    "pdf_page",
                    "equipment",
                    "configuration",
                    "size_unit",
                    "price_unit",
                    "formula_note",
                    "reading_count",
                    "holdout_count",
                    "suggested_total",
                    "visual_confidence",
                    "extraction_stage",
                    "review_status",
                    "caveats",
                ),
                row,
            )
        )
        curve["register_cell_range"] = f"A{rownum}:P{rownum}"
        curve["points"] = []
        curves.append(curve)
        key = (row[2], row[5])
        if key in lookup:
            raise ValueError("Duplicate curve identity")
        lookup[key] = curve
    formula_rows = list(
        formula_book["Point Readings"].iter_rows(min_row=2, values_only=True)
    )
    for rownum, row in enumerate(
        workbook["Point Readings"].iter_rows(min_row=2, values_only=True), 2
    ):
        if not row[0]:
            continue
        curve = lookup[(row[1], row[4])]
        curve["points"].append(
            {
                "row": rownum,
                "cell_range": f"H{rownum}:L{rownum}",
                "size": row[7],
                "size_unit": row[8],
                "source_price": row[9],
                "price_unit": row[10],
                "cached_usd": row[11],
                "purpose": row[6],
                "confidence": row[12],
                "method": row[13],
                "status": row[14],
                "note": row[15],
                "formula_cells": {
                    chr(65 + i) + str(rownum): v
                    for i, v in enumerate(formula_rows[rownum - 2])
                    if isinstance(v, str) and v.startswith("=")
                },
            }
        )
    data = {
        "schema_version": 1,
        "workbook_filename": workbook_path.name,
        "workbook_sha256": hashlib.sha256(workbook_path.read_bytes()).hexdigest(),
        "pdf_filename": pdf_path.name,
        "pdf_sha256": hashlib.sha256(pdf_path.read_bytes()).hexdigest(),
        "period": "early 1987",
        "currency": "USD",
        "cost_index": 320,
        "index_series": "CEPCI",
        "source_status": "unverified graph readings; PDF equations authoritative",
        "curves": curves,
    }
    Path(output).write_text(
        json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    )
    workbook.close()
    formula_book.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("workbook")
    parser.add_argument("pdf")
    parser.add_argument("output")
    args = parser.parse_args()
    build(args.workbook, args.pdf, args.output)
