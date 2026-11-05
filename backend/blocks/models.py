"""Execution envelopes only; engineering/economic values retain their canonical models."""

from dataclasses import dataclass, field
from typing import Any


class DataRequired(ValueError):
    def __init__(self, message, stages=(), updates=None):
        super().__init__(message)
        self.stages = list(stages)
        self.updates = updates or {}


@dataclass(frozen=True)
class Product:
    result: Any
    payload: dict = field(default_factory=dict)
    updates: dict = field(default_factory=dict)
    complete: bool = True
    issues: tuple[str, ...] = ()


@dataclass(frozen=True)
class Context:
    state: dict
    report: dict
    upstream: dict
    store: Any
    content: bytes | None = None
    provider: Any = None
    use_ai: bool = False

    @property
    def plan(self):
        return self.state.get("plan", {})

    @property
    def operating(self):
        return self.plan.get("operating_economics", {})
