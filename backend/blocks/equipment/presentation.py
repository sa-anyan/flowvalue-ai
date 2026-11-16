"""Known equipment prices for display; never turn a missing price into zero."""

from decimal import Decimal


def priced_summary(result):
    groups = {}
    scopes = {}
    for subtotal in result.get("subtotals") or []:
        if subtotal.get("amount") is None:
            continue
        # Keep currencies and escalation/date bases separate. Source subtotal
        # rows already exclude aliases and include quantity exactly once.
        basis = tuple(subtotal.get(k) for k in ("currency", "period", "index_series", "cost_index"))
        amount = Decimal(str(subtotal["amount"]))
        groups[basis] = groups.get(basis, Decimal(0)) + amount
        scope = subtotal.get("cost_scope") or "unspecified"
        component = scopes.setdefault(basis, {}).setdefault(scope, {"amount": Decimal(0), "equipment_tags": []})
        component["amount"] += amount
        component["equipment_tags"] = list(dict.fromkeys(component["equipment_tags"] + list(subtotal.get("equipment_tags") or [])))
    lines = [line for line in result.get("equipment") or []
             if not (line.get("parsed_source") or {}).get("confirmed_alias")]
    unpriced = [line for line in lines if line.get("amount") is None]
    return {"amounts": [{"amount": str(amount), "currency": basis[0], "period": basis[1],
                          "components": [{"cost_scope": scope, "amount": str(row["amount"]),
                                          "equipment_tags": row["equipment_tags"]}
                                         for scope, row in scopes[basis].items()]}
                         for basis, amount in groups.items()],
            "priced_count": len(lines) - len(unpriced), "unpriced_count": len(unpriced),
            "excludes_unpriced_items": True}


def project(state):
    result = (((state.get("results") or {}).get("stages") or {}).get("equipment") or {}).get("result")
    if result:
        result["priced_summary"] = priced_summary(result)
    capital = (((state.get("results") or {}).get("stages") or {}).get("capex") or {}).get("result")
    if capital:
        capital["equipment_summary"] = capex_summary(capital)
    return state


def capex_summary(result):
    """Equipment headline from CAPEX's own saved scope bases, never a newer stage."""
    scopes = result.get("scope_subtotals") or {}
    if not scopes or any(value is None for value in scopes.values()):
        return {"amounts": []}
    components = []
    for scope, value in scopes.items():
        amount = Decimal(str(value))
        if not amount and scope != "purchased_equipment":
            continue
        tags = [row["tag"] for row in result.get("inclusion_records") or []
                if row.get("scope") == scope and row.get("tag")]
        components.append({"cost_scope": scope, "amount": str(amount), "equipment_tags": list(dict.fromkeys(tags))})
    return {"amounts": [{"amount": str(sum((Decimal(row["amount"]) for row in components), Decimal(0))),
                         "currency": result.get("currency"), "period": result.get("period"),
                         "components": components}]}
