"""Concise implementation metadata; no reproduced textbook prose or tables."""

from backend.capex.models import Source

SOURCE = Source(
    "Donald E. Garrett, Chemical Engineering Economics (1989), Ch.5 Product Sales Value / Market Research, pp.75–76",
    "Chemical Engineering Economics for me.pdf",
    "fe1084a476baece3a8afd4711311780b314b08ca085dbcb766f193903bfe3eff",
    76,
    88,
    "Sales section within Chapter 5; quantity sold is distinct from capacity. Historical 10% established-market guidance is contextual, not a hard cap.",
)
MODEL = {
    "id": "garrett",
    "title": "Garrett product sales and market research",
    "default": True,
    "source": SOURCE,
    "market_share_review_threshold": ".10",
    "automatic_price_factors": (),
    "formula": "annual revenue = sum(quantity sold × net selling price)",
}
