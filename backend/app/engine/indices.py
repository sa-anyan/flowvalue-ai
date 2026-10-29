"""Compatibility imports. Index validation/catalog now live in price_escalation/catalog.py."""

from app.engine.price_escalation.catalog import IndexRecord, index_catalog

__all__ = ["IndexRecord", "index_catalog"]
