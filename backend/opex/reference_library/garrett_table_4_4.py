"""Garrett, Chemical Engineering Economics (1989), Ch.4 Table 4-4 (page-checked).

Rows are generated from the existing Garrett model so every number and the
page reference are reused unchanged. Garrett prints ranges without a typical
value, so ``typical`` is None; the default rule uses the midpoint and says so.
"""

from backend.opex.indexes.garrett.model import CATEGORIES, SOURCE

METHOD = "garrett"
PAGE = f"printed p.{SOURCE.printed_page} / PDF p.{SOURCE.pdf_page}, Table 4-4"

ROWS = tuple(
    {
        "category": c.id,
        "base": c.base,
        "low": c.minimum,
        "typical": None,
        "high": c.maximum,
        "units": f"fraction of {c.base}",
        "source": SOURCE.reference,
        "page": PAGE,
        "applicability": c.applicability,
        "status": "page_checked",
    }
    for c in CATEGORIES
    if c.base and c.minimum is not None and c.maximum is not None
)
