"""Inactive future LLM contract. No provider, credentials, networking or execution."""

from dataclasses import dataclass
from typing import Protocol

from .models import number
from .registry import get_factor_ranges, get_model


@dataclass(frozen=True)
class FactorProposal:
    factor_id: str
    fraction: str
    base: str
    rationale: str
    references: tuple[str, ...]


@dataclass(frozen=True)
class CapexProposal:
    model_id: str
    process_type: str
    classification_rationale: str
    factors: tuple[FactorProposal, ...]


class FutureCapexAdvisor(Protocol):
    def propose(
        self, *, model_id: str, project_description: str, engineering_evidence: dict
    ) -> CapexProposal: ...


def validate_proposal(proposal):
    """Validate a draft only. Never apply factors or invoke an LLM/calculation."""
    issues = []
    try:
        model = get_model(proposal.model_id)
        if proposal.process_type not in model.process_types:
            return ("Unsupported proposed classification",)
        ranges = {
            f["id"]: f
            for f in get_factor_ranges(proposal.model_id, proposal.process_type)
        }
    except (ValueError, TypeError) as exc:
        return (str(exc),)
    if not proposal.classification_rationale.strip():
        issues.append("Classification rationale required")
    seen = set()
    for item in proposal.factors:
        if item.factor_id in seen:
            issues.append("Duplicate proposed factor: " + item.factor_id)
        seen.add(item.factor_id)
        definition = ranges.get(item.factor_id)
        if (
            definition is None
            or not definition["additive"]
            or definition["minimum"] is None
        ):
            issues.append("Unsupported proposed factor: " + item.factor_id)
            continue
        try:
            fraction = number(item.fraction)
            if (
                not number(definition["minimum"])
                <= fraction
                <= number(definition["maximum"])
            ):
                issues.append(item.factor_id + ": outside published range")
        except (ValueError, TypeError) as exc:
            issues.append(str(exc))
        if item.base != definition["base"]:
            issues.append(item.factor_id + ": calculation base mismatch")
        if not item.rationale.strip() or not item.references:
            issues.append(item.factor_id + ": rationale and references required")
        elif definition["source"]["reference"] not in item.references:
            issues.append(item.factor_id + ": selected model source reference required")
    return tuple(issues)
