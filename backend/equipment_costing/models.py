"""Small, immutable inputs/results for the Garrett costing methods."""

import re
from dataclasses import dataclass
from math import isfinite


def positive(value: float, name: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not isfinite(value)
        or value <= 0
    ):
        raise ValueError(f"{name} must be a finite positive number")
    return float(value)


@dataclass(frozen=True)
class ReferenceCost:
    """A documented comparable cost with explicit scope, NOT an invented graph price.

    Scope may be purchase, installed or unit price; methods enforce the match.

    valid_size_range is a caller-declared reference/anchor interval, not source validation.
    Targets outside it can produce explicitly flagged boundary extrapolation.
    Reference and target must retain the same variant, construction and scope.
    """

    equipment: str
    variant: str
    amount: float
    size: float
    size_unit: str
    currency: str
    cost_index: float
    period: str
    source: str
    valid_size_range: tuple[float, float]
    same_configuration_confirmed: bool
    cost_scope: str = "purchased_equipment"

    def __post_init__(self):
        for name in (
            "equipment",
            "variant",
            "size_unit",
            "period",
            "source",
            "cost_scope",
        ):
            if (
                not isinstance(getattr(self, name), str)
                or not getattr(self, name).strip()
            ):
                raise ValueError(f"{name} is required")
        for name in ("amount", "size", "cost_index"):
            positive(getattr(self, name), name)
        if not isinstance(self.currency, str) or not re.fullmatch(
            r"[A-Z]{3}", self.currency
        ):
            raise ValueError("currency must be an explicit three-letter code")
        if (
            not isinstance(self.valid_size_range, tuple)
            or len(self.valid_size_range) != 2
        ):
            raise ValueError("valid_size_range must contain lower and upper limits")
        low, high = self.valid_size_range
        positive(low, "lower limit")
        positive(high, "upper limit")
        if low > high or not low <= self.size <= high:
            raise ValueError("Reference size is outside its declared scaling limits")
        if self.same_configuration_confirmed is not True:
            raise ValueError("Comparable configuration must be explicitly confirmed")


@dataclass(frozen=True)
class CostEstimate:
    equipment: str
    variant: str
    amount: float
    currency: str
    cost_index: float
    period: str
    size: float
    size_unit: str
    cost_scope: str
    formula: str
    printed_page: int
    pdf_page: int
    source_title: str
    source_filename: str
    source_sha256: str
    exponent: float | None = None
    reference: ReferenceCost | None = None
    extrapolated: bool = False
    anchor_size: float | None = None
    anchor_cost: float | None = None
    exponent_basis: str = "printed size exponent"
    notes: tuple[str, ...] = ()
