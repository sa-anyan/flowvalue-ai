"""Explicit physical operating plan for the existing Revenue engine."""

from dataclasses import dataclass

from backend.revenue.models import Assumption


@dataclass(frozen=True)
class ProductionPlan:
    financial_year: int
    revenue_year: int
    annual_hours: Assumption
    availability: Assumption
    utilisation: Assumption
    source: str
