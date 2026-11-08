"""Net water removal for an explicitly selected dryer feed/product boundary.

This is not a heat-duty calculation or proof that all missing water evaporates.
The selected boundary must exclude mechanical drains, reactions and other water
paths. Those scope assumptions remain visible alongside the source measurements.
"""

import math
import unicodedata


def water_evaporation(feed, product, convert):
    if feed["entity_key"] == product["entity_key"]:
        raise ValueError("Dryer feed and product must be different streams")
    values = []
    for observation in (feed, product):
        component = (
            unicodedata.normalize("NFKC", str(observation.get("component", "")))
            .strip()
            .casefold()
        )
        if observation.get("property") != "component_mass_flow" or component not in {
            "water",
            "h2o",
        }:
            raise ValueError(
                "Select water component mass flows, not total wet feed or concentrations"
            )
        value = convert(observation["value"], observation["unit"], "kg/h")
        if isinstance(value, bool) or not math.isfinite(value) or value < 0:
            raise ValueError("Water component flows must be finite and non-negative")
        values.append(value)
    evaporation = values[0] - values[1]
    if evaporation <= 0:
        raise ValueError("Selected dryer boundary has no positive net water removal")
    return (
        evaporation,
        "kg/h",
        {
            "formula": "net_water_removed_kg_h = feed_water_kg_h - product_water_kg_h",
            "feed_water_kg_h": values[0],
            "product_water_kg_h": values[1],
            "assumption": "Net water removal is evaporation: steady selected dryer boundary, no other water feeds, drains or water-producing/consuming reaction. Not an independently verified whole-plant balance.",
        },
    )
