"""Discrete IRR isolates positive polynomial roots; continuous uniform cases are labelled."""

import math
from decimal import Decimal
from itertools import pairwise

from ...models import Metric
from ..npv.calculator import npv


def _normalized(coefficients, x):
    terms = [
        (math.copysign(1, a), math.log(abs(a)) + i * math.log(x))
        for i, a in enumerate(coefficients)
        if a
    ]
    peak = max(v for _, v in terms)
    weighted = [(sign, math.exp(log - peak)) for sign, log in terms]
    return math.fsum(sign * weight for sign, weight in weighted) / math.fsum(
        weight for _, weight in weighted
    )


def _bisect(function, low, high, logarithmic=False):
    left = function(low)
    for _ in range(150):
        middle = (
            math.exp((math.log(low) + math.log(high)) / 2)
            if logarithmic
            else (low + high) / 2
        )
        value = function(middle)
        if abs(value) < 1e-14:
            return middle
        if left * value <= 0:
            high = middle
        else:
            low, left = middle, value
    return (low + high) / 2


def _positive_roots(coefficients, low, high):
    a = list(coefficients)
    while len(a) > 1 and a[-1] == 0:
        a.pop()
    while len(a) > 1 and a[0] == 0:
        a.pop(0)
    if len(a) <= 1:
        return []
    if len(a) == 2:
        root = -a[0] / a[1]
        return [root] if low <= root <= high else []
    critical = _positive_roots([i * a[i] for i in range(1, len(a))], low, high)
    knots = [low] + critical + [high]
    f = lambda x: _normalized(a, x)
    roots = [x for x in knots if abs(f(x)) < 1e-11]
    for left, right in pairwise(knots):
        if f(left) * f(right) < 0:
            roots.append(_bisect(f, left, right, True))
    roots.sort()
    unique = []
    for x in roots:
        if not unique or abs(math.log(x / unique[-1])) > 1e-7:
            unique.append(x)
    return unique


def irr(recurring, point, convention="discrete_end"):
    flows = [float(r + p) for r, p in zip(recurring, point)]
    if not all(math.isfinite(x) for x in flows):
        return Metric(
            None,
            "fraction/year",
            "undefined",
            "Cash values exceed supported numerical IRR range",
        )
    if not any(x < 0 for x in flows) or not any(x > 0 for x in flows):
        return Metric(
            None,
            "fraction/year",
            "undefined",
            "IRR requires both positive and negative net cash flows",
        )
    if convention == "garrett_uniform":

        def fn(rate):
            value = npv(recurring, point, Decimal(str(rate)), convention)
            return float(value / max(Decimal(1), abs(value)))

        components = [point[0]] + [
            x for pair in zip(recurring[1:], point[1:]) for x in pair
        ]
        signs = [x > 0 for x in components if x]
        changes = sum(left != right for left, right in pairwise(signs))
        conventional = bool(signs) and not signs[0] and signs[-1] and changes == 1
        if conventional:
            low, high = -2.0, 2.0
            while fn(low) < 0 and low > -64:
                low *= 2
            while fn(high) > 0 and high < 64:
                high *= 2
            if fn(low) * fn(high) > 0:
                return Metric(
                    None,
                    "continuous fraction/year",
                    "not_bracketed",
                    "IRR outside adaptive continuous-rate bracket [-64,64]",
                )
            root = Decimal(str(_bisect(fn, low, high)))
            return Metric(
                root,
                "continuous fraction/year",
                "calculated",
                "Chronologically conventional uniform/point cash series; adaptive bracketed continuous IRR",
                (root,),
            )
        knots = [-2 + i / 100 for i in range(401)]
        roots = []
        for left, right in pairwise(knots):
            if fn(left) == 0:
                roots.append(left)
            elif fn(left) * fn(right) < 0:
                roots.append(_bisect(fn, left, right))
        roots = tuple(
            Decimal(str(r))
            for i, r in enumerate(roots)
            if i == 0 or abs(r - roots[i - 1]) > 1e-7
        )
        status = (
            "calculated"
            if conventional and len(roots) == 1
            else "bounded_search_nonconventional"
        )
        return Metric(
            roots[0] if status == "calculated" else None,
            "continuous fraction/year",
            status,
            "Uniform recurring cash and point terminal/capital cash; numerical search [-2,2]; nonconventional root completeness not asserted",
            roots,
        )
    while len(flows) > 1 and flows[0] == 0:
        flows.pop(0)
    while len(flows) > 1 and flows[-1] == 0:
        flows.pop()
    scale = max(abs(x) for x in flows)
    flows = [x / scale for x in flows]
    if flows[0] == 0 or flows[-1] == 0:
        return Metric(
            None,
            "fraction/year",
            "undefined",
            "Cash ratios exceed supported numerical IRR range",
        )
    if not all(math.isfinite(x) for x in flows):
        return Metric(
            None,
            "fraction/year",
            "undefined",
            "Cash series exceeds numerical IRR range",
        )
    low = 1 / (1 + max(abs(x / flows[0]) for x in flows[1:]))
    high = 1 + max(abs(x / flows[-1]) for x in flows[:-1])
    if low <= 0 or not math.isfinite(high):
        return Metric(
            None,
            "fraction/year",
            "undefined",
            "Polynomial bound exceeds numerical IRR range",
        )
    roots = _positive_roots(flows, low, high)
    rates = sorted(
        1 / x - 1 if convention == "discrete_end" else -math.log(x) for x in roots
    )
    values = tuple(Decimal(str(x)) for x in rates)
    return Metric(
        values[0] if len(values) == 1 else None,
        "fraction/year" if convention == "discrete_end" else "continuous fraction/year",
        "calculated" if len(values) == 1 else "multiple" if values else "undefined",
        "All numerically isolated positive discount-polynomial roots; no arbitrary root selected",
        values,
    )
