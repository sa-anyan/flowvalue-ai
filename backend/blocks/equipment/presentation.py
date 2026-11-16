"""Known equipment prices for display; never turn a missing price into zero."""

from decimal import Decimal


def priced_summary(result):
    groups = {}
    for subtotal in result.get("subtotals") or []:
        if subtotal.get("amount") is None:
            continue
        # Keep currencies and escalation/date bases separate. Source subtotal
        # rows already exclude aliases and include quantity exactly once.
        basis = tuple(subtotal.get(k) for k in ("currency", "period", "index_series", "cost_index"))
        groups[basis] = groups.get(basis, Decimal(0)) + Decimal(str(subtotal["amount"]))
    lines = [line for line in result.get("equipment") or []
             if not (line.get("parsed_source") or {}).get("confirmed_alias")]
    unpriced = [line for line in lines if line.get("amount") is None]
    return {"amounts": [{"amount": str(amount), "currency": basis[0], "period": basis[1]}
                         for basis, amount in groups.items()],
            "priced_count": len(lines) - len(unpriced), "unpriced_count": len(unpriced),
            "excludes_unpriced_items": True}


def project(state):
    result = (((state.get("results") or {}).get("stages") or {}).get("equipment") or {}).get("result")
    if result:
        result["priced_summary"] = priced_summary(result)
    return state
