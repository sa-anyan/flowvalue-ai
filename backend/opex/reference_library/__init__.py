"""Source-cited OPEX reference library: ranges for deterministic default proposals.

Each source has its own module holding rows of numbers and citations only:
category id (matching ``opex.indexes.garrett.model.CATEGORIES``), base, low,
typical (or None when the source gives no typical value), high, units, source
reference, printed page/table, a short applicability note in our own words, and
a verification status.

Only rows marked ``page_checked`` are ever used in a calculation. Rows marked
``pending_source_check`` are slots awaiting a page the founder supplies or
confirms; no value is typed in from memory. No source text, tables or scans are
stored (licence hygiene, AGENTS.md).
"""

from . import garrett_table_4_4, peters_timmerhaus, seider, towler_sinnott, turton

PAGE_CHECKED = "page_checked"
PENDING = "pending_source_check"
SOURCES = (garrett_table_4_4, turton, peters_timmerhaus, towler_sinnott, seider)


def all_rows():
    return [dict(row, method=module.METHOD) for module in SOURCES for row in module.ROWS]


def get_ranges(category, method="garrett"):
    """Active (page-checked) range rows for one category and method."""
    return [r for r in all_rows()
            if r["category"] == category and r["method"] == method and r["status"] == PAGE_CHECKED
            and r.get("kind", "range") == "range"]


def get_correlation(category, method="turton"):
    """A page-checked correlation row (e.g. operators per shift), or None."""
    return next((r for r in all_rows()
                 if r["category"] == category and r["method"] == method and r["status"] == PAGE_CHECKED
                 and r.get("kind") == "correlation"), None)


def pending_slots():
    """Library slots awaiting page-checked values (never used in a calculation)."""
    return [r for r in all_rows() if r["status"] == PENDING]
