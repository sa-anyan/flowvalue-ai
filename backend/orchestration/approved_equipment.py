"""Keep accepted user inputs when a specialist refresh returns replacement rows."""

import copy


def retain_approved(previous, proposed):
    from backend.equipment_resolution.scope import confirmed

    protected = {}
    for row in previous:
        price = row.get("manual_price") or {}
        quote = row.get("external_quote") or {}
        if (
            (price.get("approved") is True and price.get("locked", True) is not False)
            or (
                quote.get("same_configuration_confirmed") is True
                and quote.get("locked", True) is not False
            )
            or confirmed(row)
        ):
            protected[row["equipment_key"]] = row
    result = []
    seen = set()
    for row in proposed:
        key = row.get("equipment_key")
        result.append(copy.deepcopy(protected.get(key, row)))
        seen.add(key)
    result.extend(
        copy.deepcopy(row) for key, row in protected.items() if key not in seen
    )
    return result
