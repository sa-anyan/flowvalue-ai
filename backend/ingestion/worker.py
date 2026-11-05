"""Resource-bounded workbook worker; never evaluates formulas, VBA or external links."""

import json
import sys
from pathlib import Path


def apply_resource_limits():
    # Windows has no resource module. The parent still isolates the process
    # and enforces its wall-clock timeout and workbook/output bounds.
    if sys.platform == "win32":
        return
    import resource

    resource.setrlimit(resource.RLIMIT_CPU, (20, 20))
    if sys.platform.startswith("linux"):
        resource.setrlimit(resource.RLIMIT_AS, (768 * 1024**2, 768 * 1024**2))


if __name__ == "__main__":
    try:
        apply_resource_limits()
        from backend.ingestion.balance.workbook import read_book, address
        from backend.ingestion.workbook_pipeline import parse_workbook

        content = Path(sys.argv[1]).read_bytes()
        loaded = read_book(content, sys.argv[2])
        report = parse_workbook(content, sys.argv[2], loaded=loaded)
        # Bounded source cells permit source-backed review, including missed tables.
        cells = []
        for sheet in loaded[0]:
            for (row, col), cell in sorted(sheet.cells.items()):
                if cell.value is not None:
                    cells.append(
                        {
                            "sheet": sheet.name,
                            "cell": address(row, col),
                            "value": cell.value,
                            "formula": cell.formula,
                        }
                    )
        print(
            json.dumps(
                {
                    "report": report.model_dump(mode="json"),
                    "source_cells": cells[:12000],
                    "source_cells_truncated": len(cells) > 12000,
                },
                default=str,
                allow_nan=False,
            )
        )
    except Exception as exc:
        print(json.dumps({"error": str(exc)[:400]}))
        sys.exit(1)
