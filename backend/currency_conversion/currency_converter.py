"""Dated, deterministic Decimal FX shared by quotes, research and reporting.

FX changes currency, never a price year, quantity, uncertainty or evidence status.
No network call, LLM arithmetic, hidden rounding or inferred currency symbols.
"""

import copy
import json
from datetime import date
from decimal import Decimal, InvalidOperation, localcontext
from pathlib import Path


def rate_snapshot():
    return json.loads(Path(__file__).with_name("rates.json").read_text(encoding="utf-8"))


def number(value):
    if isinstance(value, bool):
        raise ValueError("Boolean is not a monetary amount")  # noqa: TRY004 -- API validation uses ValueError/422
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError):
        raise ValueError("A finite monetary amount is required") from None
    if not result.is_finite() or (result and abs(result.adjusted()) > 100):
        raise ValueError("A finite monetary amount is required")
    return result


def convert_currency(
    amount, source_currency, target_currency, *, snapshot=None, rate_date=None
):
    """Return amount plus full conversion basis; negative cash flows are supported.

    Explicit dates must match the supplied snapshot. The packaged snapshot is
    pinned, not a claim of continuously refreshed market/transaction rates.
    """
    data = copy.deepcopy(snapshot if snapshot is not None else rate_snapshot())
    observed = date.fromisoformat(data["date"])
    if rate_date is not None and date.fromisoformat(rate_date) != observed:
        raise ValueError("No exchange-rate snapshot for the requested date")
    if not data.get("source") or not data.get("url") or not data.get("base"):
        raise ValueError("Sourced, dated exchange rates are required")
    for code in (source_currency, target_currency):
        if (
            not isinstance(code, str)
            or len(code) != 3
            or not code.isalpha()
            or not code.isupper()
        ):
            raise ValueError(
                "Use an uppercase three-letter currency code, not a symbol"
            )
        if code not in data["rates"]:
            raise ValueError("Unsupported currency: " + code)
    base, target = (
        number(data["rates"][source_currency]),
        number(data["rates"][target_currency]),
    )
    if base <= 0 or target <= 0:
        raise ValueError("Exchange rates must be positive")
    original = number(amount)
    with localcontext() as ctx:
        ctx.prec = 40
        multiplier = target / base
        converted = original * multiplier
    return {
        "original_amount": str(original),
        "source_currency": source_currency,
        "amount": str(converted),
        "currency": target_currency,
        "rate": str(multiplier),
        "rate_date": observed.isoformat(),
        "reference_base": data["base"],
        "source": data["source"],
        "url": data["url"],
        "notice": "Pinned informational reference rate; excludes bank spreads, fees and FX forecasts.",
    }


def convert_price(
    price, target_currency, *, amount_field="amount", snapshot=None, rate_date=None
):
    """Adapt an explicit quote/assumption; preserve its original record and basis.

    Supports amount or unit_price via amount_field. Caller must supply ISO
    currency. Product unit, price period, citation and uncertainty stay unchanged.
    """
    result = copy.deepcopy(price)
    audit = convert_currency(
        price[amount_field],
        price["currency"],
        target_currency,
        snapshot=snapshot,
        rate_date=rate_date,
    )
    result[amount_field] = audit["amount"]
    result["currency"] = target_currency
    result["fx_conversion"] = {**audit, "original_price": copy.deepcopy(price)}
    return result
