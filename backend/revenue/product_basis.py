"""Resolve explicit product units and component bases against actual source evidence."""

import re
from backend.opex.consumption import observation


def quantity_unit(item):
    unit = item["quantity_unit"]
    if unit == "t":
        if re.search(
            r"\btonnes?\b|\bmetric tons?\b", item.get("context_quote", ""), re.I
        ):
            return "tonne"
        raise ValueError(
            "Specify tonne, short_ton or long_ton for the product selling-price basis"
        )
    return unit


def product_observation(report, item):
    unit = quantity_unit(item)
    if item.get("manual_rate"):
        from .indexes.openpytea.rate_model import hourly_rate

        _, source = hourly_rate({**item, "quantity_unit": unit})
        return source
    prop = "volume_flow" if unit in {"m3", "L"} else "mass_flow"
    component = item.get("component")
    if not component:
        entity = next(
            (e for e in report["entities"] if e["key"] == item["stream_key"]), None
        )
        candidates = set()
        for value in (entity or {}).get("values", []):
            name = value.get("component")
            if (
                name
                and value.get("property") == "component_" + prop
                and re.search(
                    r"\bbased on\s+(?:the\s+)?(?:[\d.,]+\s*\S+\s+)?"
                    + re.escape(name)
                    + r"\s+component\b",
                    item.get("context_quote", ""),
                    re.I,
                )
            ):
                candidates.add(name)
        if len(candidates) > 1:
            raise ValueError("Choose one component as the sale quantity basis")
        if candidates:
            component = candidates.pop()
    return observation(
        report,
        item["stream_key"],
        "component_" + prop if component else prop,
        component,
    )
