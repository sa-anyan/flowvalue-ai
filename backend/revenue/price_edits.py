"""Reconcile unambiguous price-only Revenue Box edits without reclassifying income."""
import copy
from decimal import Decimal, InvalidOperation
import math
import re

from .commercial_intent import validate_intent

PRICE = re.compile(r"(?P<currency>USD|GBP|EUR|\$|£|€)\s*(?P<amount>\d+(?:\.\d+)?)\s*(?:/|per\s+)(?P<unit>kg|m3|t|L)\b", re.I)


def price_expression(text):
    matches = list(PRICE.finditer(text))
    if len(matches) != 1:
        return None
    match = matches[0]
    signature = text[:match.start("amount")] + "<price>" + text[match.end("amount"):]
    return match, " ".join(signature.casefold().split())


def reconcile_product_price(config, previous_text, text):
    """Return an updated copy only when a single product's price alone changed.

    Category, currency, quantity unit, physical mapping and all other words must
    remain unchanged. Ambiguous or semantic changes still need interpretation.
    """
    sales = config.get("sales", [])
    mechanisms = config.get("commercial_intent", {}).get("mechanisms", [])
    if len(sales) != 1 or len(mechanisms) != 1 or config.get("commercial_lines"):
        return None
    sale, mechanism = sales[0], mechanisms[0]
    if mechanism.get("category") != "product_sales" or sale.get("intent_id") != mechanism.get("id") or sale.get("price_mode") != "assumed_price":
        return None
    after = price_expression(text)
    before = price_expression(previous_text)
    # Re-saving an already edited Box can repair a stale original quote too.
    if previous_text == text:
        previous_text = mechanism.get("context_quote", "")
        before = price_expression(previous_text)
    if not before or not after or before[1] != after[1]:
        return None
    old, new = before[0], after[0]
    currency = {"$": "USD", "£": "GBP", "€": "EUR"}.get(new["currency"], new["currency"].upper())
    if currency != config.get("price_basis", {}).get("currency") or new["unit"].casefold() != sale.get("quantity_unit", "").casefold():
        return None
    try:
        old_price, new_price = Decimal(old["amount"]), Decimal(new["amount"])
        if Decimal(str(sale.get("unit_price"))) not in {old_price, new_price} or not math.isfinite(float(new_price)):
            return None
    except (InvalidOperation, TypeError, ValueError, OverflowError):
        return None
    if old.group(0) == new.group(0):
        return None
    result = copy.deepcopy(config)
    for line in [result["sales"][0], result["commercial_intent"]["mechanisms"][0]]:
        quote = line.get("context_quote", "")
        if not quote:
            return None
        if quote.casefold() not in text.casefold():
            quote = quote.replace(old.group(0), new.group(0))
            if quote.casefold() not in text.casefold():
                return None
            line["context_quote"] = quote
    result["sales"][0]["unit_price"] = float(new_price)
    validate_intent(result, text)
    return result
