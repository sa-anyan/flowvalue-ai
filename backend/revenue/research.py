"""Future sourced-market connector contract; no research implementation or calls."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class MarketResearchRequest:
    product_id: str
    grade: str
    geography: str
    quantity_unit: str
    price_period: str
    consent_reference: str


@dataclass(frozen=True)
class MarketEvidence:
    url: str
    published_at: str
    retrieved_at: str
    price_quantity_basis: str
    product_grade: str
    delivery_terms: str
    geography: str
    uncertainty: str


class FutureMarketResearch(Protocol):
    def research(
        self, request: MarketResearchRequest
    ) -> tuple[MarketEvidence, ...]: ...


def research_readiness(*, permission, consent_reference=""):
    """Return consent state only; never perform an external call, even if approved."""
    if permission is None:
        return "permission_required"
    if permission is False:
        return "declined"
    if (
        permission is not True
        or not isinstance(consent_reference, str)
        or not consent_reference.strip()
    ):
        raise ValueError("Explicit consent reference required")
    return "ready_for_future_connector"
