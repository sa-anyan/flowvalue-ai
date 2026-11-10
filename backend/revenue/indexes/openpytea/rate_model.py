"""OpenPyTEA 3.2.1 Plant.calculate_revenue convention, with explicit units/time.

Independently authored adapter, not vendored upstream code. OpenPyTEA expresses
production per day × price × 365 × utilization. FlowValue normalizes to hourly
rates and uses the saved operating hours/ramp once. It keeps the existing annual
revenue/financial engines, rather than introducing a second TEA calculation.
"""

from decimal import Decimal
from backend.equipment_costing.unit_conversion import convert
from backend.opex.consumption import decimal

REFERENCE = "OpenPyTEA 3.2.1 Plant.calculate_revenue; https://github.com/pbtamarona/OpenPyTEA (MIT, Panji Tamarona 2025)"
RATE_UNITS = (
    "kg/h",
    "kg/day",
    "kg/min",
    "kg/s",
    "tonne/h",
    "tonne/day",
    "lb/h",
    "m3/h",
    "m3/day",
    "m3/min",
    "L/h",
    "L/min",
    "L/s",
)


def manual_observation(item):
    rate = item.get("manual_rate") or {}
    if rate.get("confirmed_by_user") is not True:
        raise ValueError(
            "Confirm the custom flow rate as your assumption; AI cannot establish a physical flow"
        )
    unit = rate.get("unit")
    if unit not in RATE_UNITS:
        raise ValueError(
            "Enter a rate with a supported time unit, such as kg/h, m3/h or kg/day—not a one-off quantity"
        )
    value = decimal(rate.get("value"))
    if not str(rate.get("rationale") or "").strip():
        raise ValueError("Record the basis of the custom rate")
    identity = "user-rate:" + str(item["id"])
    return {
        "id": identity,
        "normalized_value": str(value),
        "normalized_unit": unit,
        "source": "Explicit user-supplied rate · " + str(rate["rationale"]),
        "status": "user_assumption",
        "source_kind": "user_rate",
    }


def hourly_rate(item):
    observation = manual_observation(item)
    result = convert(
        float(observation["normalized_value"]),
        observation["normalized_unit"],
        item["quantity_unit"] + "/h",
    )
    if result.value is None:
        raise ValueError(
            "Rate and price units are incompatible: " + "; ".join(result.issues)
        )
    return Decimal(str(result.value)), observation


def annual_manual_quantity(item, hours, utilization):
    rate, source = hourly_rate(item)
    return {
        "annual_quantity": rate * decimal(hours) * decimal(utilization, maximum=1),
        "hourly_rate": str(rate),
        "source": source,
        "model": REFERENCE,
        "basis": "Explicit user rate × scheduled hours × annual utilization; utilization applied once",
    }
