"""Future LLM contract only; no providers, networking or AI numerical calculations."""

from dataclasses import dataclass
from typing import Protocol

from backend.revenue.models import Assumption

from .models import FinancialInputs


@dataclass(frozen=True)
class FinancialProposal:
    field_path: str
    assumption: Assumption
    methodology: str
    explanation: str
    references: tuple[str, ...]


class FutureFinancialAdvisor(Protocol):
    def propose(self, context: FinancialInputs) -> tuple[FinancialProposal, ...]: ...
