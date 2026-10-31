"""Future engineering-judgement/research interfaces only. No LLM or network calls."""

from dataclasses import dataclass
from typing import Protocol

from .models import Assumption, OpexInputs
from .registry import calculate_opex, get_model


@dataclass(frozen=True)
class AdvisorContext:
    model_id: str
    baseline: OpexInputs
    equipment_specs_json: str
    mass_energy_balance_json: str
    capex_evidence_json: str


@dataclass(frozen=True)
class DraftProposal:
    model_id: str
    assumptions: tuple[Assumption, ...]
    missing_categories: tuple[str, ...]
    clarification_questions: tuple[str, ...]
    classification_rationale: str


@dataclass(frozen=True)
class ResearchRequest:
    topic: str
    location: str
    quantity_unit: str
    price_period: str
    permission_reference: str  # future caller must obtain opt-in before research


@dataclass(frozen=True)
class ResearchEvidence:
    source_url: str
    publication_date: str
    retrieved_at: str
    quoted_basis: str
    applicability: str
    uncertainty: str


class FutureOpexAdvisor(Protocol):
    def propose(self, context: AdvisorContext) -> DraftProposal: ...


class FutureMarketResearch(Protocol):
    def research(self, request: ResearchRequest) -> tuple[ResearchEvidence, ...]: ...


def validate_proposal(proposal, baseline):
    """Validate a draft in isolation. Never apply, freeze, save or research it.

    No fabricated probabilities, prices or arithmetic from an LLM are accepted as
    verified. Complete deterministic input validation still precedes calculation.
    """
    get_model(proposal.model_id)
    if not proposal.classification_rationale.strip():
        return ("Engineering rationale required",)
    from dataclasses import replace

    draft = replace(baseline, assumptions=proposal.assumptions)
    return calculate_opex(proposal.model_id, draft).issues
