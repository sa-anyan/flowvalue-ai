"""Extract only literal user-supplied time rates, never infer physical quantities."""

import re
from decimal import Decimal

_PATTERN = re.compile(
    r"(?<![\w.])(?P<value>[+-]?(?:\d+(?:,\d{3})*(?:\.\d+)?|\.\d+)(?:e[+-]?\d+)?)\s*(?P<unit>tonnes?|kg|kilograms?|lb|m3|m³|litres?|liters?|L)\s*(?:/|per\s+)(?P<time>hours?|hrs?|h|days?|d|minutes?|mins?|min|seconds?|secs?|s)\b",
    re.I,
)


def explicit_rates(text):
    found = []
    for match in _PATTERN.finditer(text):
        value = Decimal(match["value"].replace(",", ""))
        if not value.is_finite() or value < 0:
            continue
        raw = match["unit"].lower()
        unit = (
            "tonne"
            if raw.startswith("ton")
            else (
                "kg"
                if raw in {"kg", "kilogram", "kilograms"}
                else "lb" if raw == "lb" else "m3" if raw in {"m3", "m³"} else "L"
            )
        )
        time = match["time"].lower()
        denominator = (
            "h"
            if time.startswith("h")
            else (
                "day"
                if time.startswith("d")
                else "min" if time.startswith("m") else "s"
            )
        )
        rate_unit = unit + "/" + denominator
        from .indexes.openpytea.rate_model import RATE_UNITS

        if rate_unit in RATE_UNITS:
            found.append(
                {
                    "id": "explicit-rate-" + str(len(found) + 1),
                    "value": float(value),
                    "unit": rate_unit,
                    "context_quote": match.group(0),
                }
            )
    return found


def mark_literal_provenance(config, text):
    """Restore literal user provenance after generic AI-draft labelling; never approve."""
    supplied = explicit_rates(text)
    for group in ("sales", "commercial_lines"):
        for line in config.get(group, []):
            rate = line.get("manual_rate")
            if not isinstance(rate, dict):
                continue
            match = next(
                (
                    r
                    for r in supplied
                    if r["value"] == rate.get("value") and r["unit"] == rate.get("unit")
                ),
                None,
            )
            if match:
                rate.update(
                    confirmed_by_user=False,
                    status="user_assumption",
                    source="Literal user statement: " + match["context_quote"],
                )
    return config
