"""Seeded vectorized Gaussian-copula sampling with bounded physical marginals."""

import math

import numpy as np
from scipy import stats


def validate(settings, discovered):
    # Discovery may group global utility tariffs into a single driver.
    allowed = {tuple(t): p for p in discovered.parameters for t in p.targets}
    enabled = [p for p in settings.parameters if p.enabled]
    if len(enabled) > 250:
        raise ValueError("Enable at most 250 sampling drivers per study")
    if len({p.id for p in settings.parameters}) != len(settings.parameters):
        raise ValueError("Duplicate parameter IDs")
    owned = set()
    for p in enabled:
        if not p.source.strip() or not p.rationale.strip():
            raise ValueError(p.label + ": source and rationale required")
        for target in p.targets:
            key = tuple(target)
            if key not in allowed:
                raise ValueError("Unrecognised parameter target")
            original = allowed[key]
            if p.unit != original.unit or p.kind != original.kind:
                raise ValueError(p.label + ": unit/kind mismatch")
            if key in owned:
                raise ValueError("Multiple distributions own the same input")
            owned.add(key)
            if p.kind == "configuration":
                if p.distribution != "discrete" or any(
                    v not in original.choices for v in p.choices
                ):
                    raise ValueError(
                        "Configuration must use existing candidate model IDs"
                    )
            else:
                if p.distribution == "discrete":
                    values = p.choices
                    if not values or any(isinstance(v, str) for v in values):
                        raise ValueError("Numeric discrete values required")
                    lo, hi = min(values), max(values)
                else:
                    if p.minimum is None or p.maximum is None or p.minimum >= p.maximum:
                        raise ValueError(
                            p.label + ": finite minimum < maximum required"
                        )
                    lo, hi = p.minimum, p.maximum
                if original.hard_min is not None and (
                    lo < original.hard_min
                    or original.strictly_positive
                    and lo <= original.hard_min
                ):
                    raise ValueError(p.label + ": below physical/method limit")
                if original.hard_max is not None and hi > original.hard_max:
                    raise ValueError(p.label + ": above physical/method limit")
                if p.distribution == "triangular" and (
                    p.mode is None or not lo <= p.mode <= hi
                ):
                    raise ValueError(p.label + ": mode must lie within bounds")
                if p.distribution in {"normal", "lognormal"}:
                    if p.mode is None or p.stddev is None or p.stddev <= 0:
                        raise ValueError(
                            p.label
                            + ": mean/median and positive standard deviation required"
                        )
                    if not lo <= p.mode <= hi:
                        raise ValueError(
                            p.label
                            + ": central value must lie within truncation bounds"
                        )
                    if p.distribution == "lognormal" and (lo <= 0 or p.mode <= 0):
                        raise ValueError("Lognormal bounds/median must be positive")
        if p.distribution == "discrete":
            if (
                not p.choices
                or len(p.choices) != len(p.probabilities)
                or len(set(p.choices)) != len(p.choices)
            ):
                raise ValueError(
                    "Discrete choices must be unique with matching probabilities"
                )
            if any(w < 0 for w in p.probabilities) or not math.isclose(
                sum(p.probabilities), 1, abs_tol=1e-9
            ):
                raise ValueError(
                    "Discrete probabilities must be nonnegative and sum to one"
                )
    ids = [p.id for p in enabled]
    matrix = np.eye(len(ids))
    pairs = set()
    for c in settings.correlations:
        if c.a == c.b or c.a not in ids or c.b not in ids:
            raise ValueError("Correlation must reference two enabled parameters")
        pair = tuple(sorted([c.a, c.b]))
        if pair in pairs:
            raise ValueError("Duplicate correlation pair")
        pairs.add(pair)
        i, j = ids.index(c.a), ids.index(c.b)
        matrix[i, j] = matrix[j, i] = c.rho
    if len(ids) and np.linalg.eigvalsh(matrix).min() < -1e-9:
        raise ValueError("Correlation matrix must be positive semidefinite")
    return enabled, matrix


def sample(settings, discovered):
    parameters, matrix = validate(settings, discovered)
    if not parameters:
        return [], np.empty((settings.iterations, 0), dtype=object)
    rng = np.random.default_rng(settings.seed)
    z = rng.multivariate_normal(
        np.zeros(len(parameters)),
        matrix,
        size=settings.iterations,
        check_valid="raise",
        tol=1e-8,
    )
    u = np.clip(stats.norm.cdf(z), np.finfo(float).eps, 1 - np.finfo(float).eps)
    output = np.empty(u.shape, dtype=object)
    for i, p in enumerate(parameters):
        q = u[:, i]
        if p.distribution == "uniform":
            value = p.minimum + q * (p.maximum - p.minimum)
        elif p.distribution == "triangular":
            value = stats.triang.ppf(
                q,
                (p.mode - p.minimum) / (p.maximum - p.minimum),
                loc=p.minimum,
                scale=p.maximum - p.minimum,
            )
        elif p.distribution == "normal":
            value = stats.truncnorm.ppf(
                q,
                (p.minimum - p.mode) / p.stddev,
                (p.maximum - p.mode) / p.stddev,
                loc=p.mode,
                scale=p.stddev,
            )
        elif p.distribution == "lognormal":
            distribution = stats.lognorm(s=p.stddev, scale=p.mode)
            low, high = distribution.cdf([p.minimum, p.maximum])
            if not np.isfinite([low, high]).all() or high <= low:
                raise ValueError(
                    "Lognormal truncation interval is numerically unresolved"
                )
            value = distribution.ppf(low + q * (high - low))
        else:
            weights = np.cumsum(p.probabilities)
            value = np.asarray(p.choices, dtype=object)[
                np.minimum(np.searchsorted(weights, q), len(p.choices) - 1)
            ]
        if p.distribution != "discrete" and not np.isfinite(value).all():
            raise ValueError("Numerically invalid marginal distribution")
        output[:, i] = value
    return parameters, output
