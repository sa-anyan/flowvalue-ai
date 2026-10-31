"""Commercial assumptions are separate from observed prices and never auto-verified."""

from datetime import date

from backend.equipment_costing.quotes import safe_source
from backend.opex.consumption import decimal


def adjusted_price(observation, *, currency, price_period, quantity_unit):
    for key in ("rationale", "observed_at", "source_url", "observation_type"):
        if not observation.get(key):
            raise ValueError("Commercial observation requires " + key)
    safe_source(observation["source_url"])
    date.fromisoformat(observation["observed_at"])
    if observation["observation_type"] not in {
        "retail_listing",
        "commodity_benchmark",
        "bulk_listing",
        "supplier_quote",
        "user_assumption",
    }:
        raise ValueError("Unknown commercial observation type")
    if (
        observation.get("currency"),
        observation.get("price_period"),
        observation.get("quantity_unit"),
    ) != (currency, price_period, quantity_unit):
        raise ValueError(
            "Align commercial currency, price period and unit explicitly before using a researched price"
        )
    discount = decimal(observation.get("discount_fraction", 0), maximum=1)
    if discount == 1:
        raise ValueError("A 100% discount is not a supported supplier-price estimate")
    observed = decimal(observation["observed_price"])
    return {
        "unit_price": observed * (1 - discount),
        "observed_price": observed,
        "discount_fraction": discount,
        "status": "user_commercial_assumption",
        "basis": observation,
        "formula": "observed price × (1 − assumed commercial discount)",
        "notice": "A discount is a scenario assumption, not evidence of a supplier quotation or achievable selling price.",
    }
