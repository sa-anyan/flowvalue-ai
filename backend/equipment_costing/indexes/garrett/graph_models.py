"""Deterministic power-law fitting of provisional graph readings.

No industrial calibration is implied. Holdouts do not participate in fitting.
Every fit retains residuals, point references and the observed sample interval.
"""

from dataclasses import dataclass
from math import exp, isfinite, log
from statistics import fmean

from ...models import positive


@dataclass(frozen=True)
class PowerFit:
    anchor_size: float
    anchor_cost: float
    exponent: float
    lower: float
    upper: float
    training_rows: tuple[int, ...]
    diagnostics: tuple[dict, ...]
    exponent_basis: str

    def evaluate(self, size):
        from .general import scale_cost

        return scale_cost(self.anchor_cost, self.anchor_size, size, self.exponent)


def fit_points(points, *, multiplier, exponent=None):
    """Log-space least squares. Fixed printed n fits only the price intercept."""
    if exponent is not None and (
        isinstance(exponent, bool)
        or not isinstance(exponent, (int, float))
        or not isfinite(exponent)
    ):
        raise ValueError("Exponent must be finite")
    candidates = []
    for point in points:
        if point["size"] is None or point["source_price"] is None:
            continue
        x = positive(point["size"], "graph size")
        y = positive(point["source_price"], "graph price") * positive(
            multiplier, "unit multiplier"
        )
        candidates.append((x, y, point))
    training = [p for p in candidates if p[2]["purpose"].lower() != "holdout"]
    distinct = {}
    for x, y, _ in candidates:
        if x in distinct and abs(distinct[x] - y) > max(1e-9, abs(y) * 1e-9):
            raise ValueError(
                "Conflicting graph prices at duplicate sizes require review"
            )
        distinct[x] = y
    if not training or (exponent is None and len({p[0] for p in training}) < 2):
        raise ValueError(
            "At least two distinct non-holdout graph sizes are required for fitted n; one documented point suffices with printed n"
        )
    # Exact duplicate rows do not weight the regression twice.
    unique = {p[0]: p for p in training}
    training = list(unique.values())
    mx = fmean(log(x) for x, _, _ in training)
    my = fmean(log(y) for _, y, _ in training)
    n = exponent
    if n is None:
        n = sum((log(x) - mx) * (log(y) - my) for x, y, _ in training) / sum(
            (log(x) - mx) ** 2 for x, _, _ in training
        )
    anchor_x = exp(mx)
    anchor_y = exp(my)
    diagnostics = []
    for x, y, p in candidates:
        predicted = anchor_y * (x / anchor_x) ** n
        diagnostics.append(
            {
                "row": p["row"],
                "cell_range": p["cell_range"],
                "purpose": p["purpose"],
                "size": x,
                "observed": y,
                "predicted": predicted,
                "residual_percent": (predicted / y - 1) * 100,
            }
        )
    return PowerFit(
        anchor_x,
        anchor_y,
        n,
        min(x for x, _, _ in training),
        max(x for x, _, _ in training),
        tuple(p["row"] for _, _, p in training),
        tuple(diagnostics),
        "printed size exponent; log-space fitted reference cost"
        if exponent is not None
        else "log-space least-squares exponent from unverified graph points",
    )
