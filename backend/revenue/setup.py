"""Structured revenue set-up from the Entry page (no free-text interpretation).

The user picks what is sold (an M&E stream, optionally the component actually
sold), the price, unit and currency, and the operating schedule. Python writes
the sales lines and the Revenue Box sentence that authorises them, then runs
the normal revenue approval, which validates the full revenue calculation.
Because the user chose every term, nothing is left for an AI to interpret;
an item without a price stays visibly unpriced and is not approved.
"""

import copy
import re
from datetime import date

from .authority import update


def _slug(text):
    return re.sub(r"[^a-z0-9]+", "-", str(text).casefold()).strip("-")[:40] or "product"


def _stream(report, key):
    entity = next((e for e in report.get("entities", []) if e.get("key") == key), None)
    if not entity or entity.get("kind") != "material":
        raise ValueError("Choose a material stream from the M&E balance")
    return entity


def _label(stream):
    for v in stream.get("values", []):
        if v.get("property") in ("description", "name") and v.get("original_value") not in (None, ""):
            return f"{stream.get('identifier')} ({str(v['original_value'])[:60]})"
    return str(stream.get("identifier"))


def _check_flow(report, stream, component, unit):
    """The chosen stream (or component) must have a usable workbook flow."""
    from .product_basis import product_observation

    try:
        product_observation(report, {"stream_key": stream["key"], "component": component, "quantity_unit": unit})
    except (ValueError, KeyError, TypeError):
        prop = "volume" if unit in {"m3", "L"} else "mass"
        raw = [str(v.get("original_value")) for v in stream.get("values", [])
               if v.get("property") in (f"{prop}_flow", f"component_{prop}_flow")
               and (not component or v.get("component") == component)]
        why = (" — its cells show " + raw[0]) if raw and all(r.startswith("#") for r in raw) else ""
        what = f"{component} in stream {_label(stream)}" if component else f"stream {_label(stream)}"
        raise ValueError(
            f"{what[0].upper() + what[1:]} has no usable {prop} flow in the workbook{why}. "
            "Choose the stream (or component) that actually carries the product."
        ) from None


def _review_shared_streams(report, sales):
    """Several products from one stream: distinct components are fine (and recorded
    as reviewed); a whole stream plus a part of it would count that part twice."""
    by_stream = {}
    for sale in sales:
        by_stream.setdefault(sale["stream_key"], []).append(sale)
    for key, items in by_stream.items():
        if len(items) < 2:
            continue
        stream = _stream(report, key)
        whole = [i["name"] for i in items if not i["component"]]
        if whole:
            parts = [i["name"] for i in items if i["component"]] or whole[1:]
            raise ValueError(
                f"{whole[0]} is the whole of stream {_label(stream)}, which already includes "
                f"{', '.join(parts)}. Sell each product as its own component of the stream instead."
            )
        components = [i["component"] for i in items]
        if len(set(components)) != len(components):
            raise ValueError(f"The same component is sold twice from stream {_label(stream)}.")
        for i in items:
            i["shared_stream_review"] = {
                "basis": f"Different components of stream {stream.get('identifier')} chosen on the Entry page: "
                         + ", ".join(components) + "; no quantity is counted twice.",
                "origin": "entry_page",
            }


def sentence(sale, stream_tag):
    what = sale["name"] + (f" ({sale['component']} in stream {stream_tag})" if sale.get("component")
                           else f" (stream {stream_tag})")
    if sale.get("unit_price") is None:
        return f"We sell {what}; price to be confirmed."
    return f"We sell {what} at {sale['unit_price']:g} {sale['currency']} per {sale['quantity_unit']}."


def apply(store, key, revision, setup):
    """Save the set-up as revenue inputs and approve them when complete.

    Returns {"state", "approved", "questions"}.
    """
    state = store.get(key)
    report = state.get("scoped_report") or state.get("effective_report") or (state.get("parsed") or {}).get("report") or {}
    currency = str(setup.get("currency") or "USD").upper()
    period = str(setup.get("price_period") or (state.get("plan", {}).get("cost_translation") or {}).get("target_period") or "")
    if not re.fullmatch(r"[A-Z]{3}", currency) or not re.fullmatch(r"\d{4}(?:-\d{2})?", period):
        raise ValueError("Enter a three-letter currency and a price date (YYYY or YYYY-MM)")
    sales, mechanisms, sentences = [], [], []
    for raw in setup.get("sales") or []:
        stream = _stream(report, raw.get("stream_key"))
        price = raw.get("unit_price")
        price = None if price in (None, "") else float(price)
        if price is not None and price < 0:
            raise ValueError("A selling price cannot be negative")
        unit = str(raw.get("quantity_unit") or "kg")
        if unit not in {"kg", "tonne", "lb", "m3", "L"}:
            raise ValueError("Choose kg, tonne, lb, m3 or L as the selling unit")
        component = str(raw.get("component") or "").strip() or None
        name = str(raw.get("name") or component or stream.get("identifier") or "Product").strip()
        _check_flow(report, stream, component, unit)
        sale = {"name": name, "component": component, "unit_price": price, "currency": currency, "quantity_unit": unit}
        quote = sentence(sale, stream.get("identifier"))
        ident = _slug(name)
        while any(s["id"] == ident for s in sales):
            ident += "-2"
        sales.append({
            "id": ident, "intent_id": ident, "name": name, "role": "main_product" if not sales else "byproduct",
            "stream_key": stream["key"], "component": component, "quantity_unit": unit,
            "price_mode": "assumed_price", "unit_price": price,
            "allocation_fraction": 1, "saleable_fraction": 1, "sold_fraction": 1, "cost_markup_fraction": 0,
            "net_freight_deduction_per_unit": 0, "net_packaging_deduction_per_unit": 0,
            "context_quote": quote,
            "rationale": "Selected by the user on the Entry page: stream, " + ("component, " if component else "")
                         + "price and unit.",
            "specification_basis": f"{component + ' component' if component else 'Total'} flow of stream "
                                   f"{stream.get('identifier')} from the M&E balance.",
            "uncertainty": "User-entered price; market, specification and delivery terms not verified.",
        })
        mechanisms.append({"id": ident, "category": "product_sales", "context_quote": quote,
                           "interpretation": "Product sale chosen explicitly on the Entry page."})
        sentences.append(quote)
    if not sales:
        raise ValueError("Add at least one product the project sells")
    _review_shared_streams(report, sales)
    config = copy.deepcopy((state.get("plan") or {}).get("operating_economics") or {})
    config["sales"] = sales
    config["commercial_lines"] = []  # the set-up defines all payments
    config["commercial_intent"] = {"status": "explicit", "mechanisms": mechanisms, "questions": []}
    config["price_basis"] = {**(config.get("price_basis") or {}), "currency": currency, "price_period": period}
    operating = dict(config.get("operating") or {})
    operating["days_per_year"] = float(setup.get("days_per_year") or operating.get("days_per_year") or 330)
    operating["hours_per_day"] = float(setup.get("hours_per_day") or operating.get("hours_per_day") or 24)
    if setup.get("days_per_year") or setup.get("hours_per_day") or not operating.get("rationale"):
        operating["rationale"] = "Operating schedule entered or confirmed on the Entry page"
    config["operating"] = operating
    config.setdefault("assumption_date", date.today().isoformat())
    config["revenue_setup"] = {"origin": "entry_page", "sales": [
        {k: s[k] for k in ("id", "name", "stream_key", "component", "unit_price", "quantity_unit")} for s in sales]}
    state["plan"]["operating_economics"] = config
    state = store.put(state, revision)
    text = "\n".join(sentences)
    state = update(store, key, state["revision"], text=text)
    if all(s["unit_price"] is not None for s in sales):
        try:
            state = update(store, key, state["revision"], approve=True)
            return {"state": state, "approved": True, "questions": []}
        except ValueError as exc:
            return {"state": state, "approved": False, "questions": [str(exc)]}
        except KeyError as exc:
            hint = ("Set the analysis and construction years on the Entry page, then save again."
                    if str(exc).strip("'") == "financial" else f"Missing revenue input: {exc}.")
            return {"state": state, "approved": False, "questions": [hint]}
    return {"state": state, "approved": False, "questions": state.get("revenue_questions") or []}
