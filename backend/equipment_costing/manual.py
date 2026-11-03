"""Explicit user prices with auditable purchase/installation boundaries.

No size or public URL is required for a private quotation. No invented CEPCI is
attached to a dated manual amount: PRICE_BASIS is a monetary numeraire, not an index.
"""

import hashlib
import json
import re

from .indexes.garrett.installation import InstallationBreakdown
from .indexes.garrett.integrated import CostingResult
from .models import CostEstimate, positive


def manual_result(price):
    if not isinstance(price, dict):
        raise TypeError("Manual price must be a structured record")
    for name in ("source", "notes", "price_period", "currency"):
        if not isinstance(price.get(name), str) or not price[name].strip():
            raise ValueError("Manual price requires " + name)
    if not re.fullmatch(r"[A-Z]{3}", price["currency"]):
        raise ValueError("Manual currency must be an explicit three-letter code")
    if not re.fullmatch(r"\d{4}(?:-\d{2})?", price["price_period"]):
        raise ValueError("Manual cost year must be YYYY or YYYY-MM")
    if price.get("approved") is not True:
        raise ValueError("Manual price requires explicit user approval")
    amount = positive(price.get("amount"), "manual per-unit price")
    scope = price.get("cost_scope")
    factor = price.get("installation_factor")
    purchase = price.get("purchased_component")
    if scope == "purchased_equipment":
        purchase = amount
        if factor is not None:
            factor = positive(factor, "total installed / purchased factor")
            if factor < 1 or not price.get("installation_rationale"):
                raise ValueError("Installation factor must be >=1 with rationale")
        combined = amount * factor if factor is not None else None
    elif scope == "installed_equipment":
        if factor is not None:
            raise ValueError("Installed price cannot also add an installation factor")
        purchase = (
            positive(purchase, "explicit purchased component of installed quote")
            if purchase is not None
            else None
        )
        if purchase is not None and purchase > amount:
            raise ValueError("Purchased component cannot exceed installed quote")
        combined = amount
    else:
        raise ValueError(
            "Manual price must declare purchased_equipment or installed_equipment"
        )
    install = (
        combined - purchase if combined is not None and purchase is not None else None
    )
    basis = "PRICE_BASIS:" + price["currency"] + ":" + price["price_period"]
    evidence = {
        "method": "manual_user_price",
        "reference": price,
        "verification": "User assumption, not independently verified",
        "installation_boundary": "No inferred purchase split or installation factor",
    }
    estimate = CostEstimate(
        "User-priced equipment",
        price.get("configuration", "User-declared scope"),
        amount,
        price["currency"],
        1.0,
        price["price_period"],
        1.0,
        "item",
        scope,
        "User per-unit quotation × explicit quantity",
        0,
        0,
        "User-supplied price",
        price["source"],
        hashlib.sha256(json.dumps(price, sort_keys=True).encode()).hexdigest(),
        index_series=basis,
        notes=("PRICE_BASIS value 1 is not a published inflation index.",),
    )
    installation = InstallationBreakdown(
        purchase, install, combined, factor, "user_assumption", evidence
    )
    return CostingResult(
        "provisional",
        estimate,
        amount,
        ("User price requires engineering/source review.",),
        evidence,
        installation=installation,
    )


def convert_calculation(calculation, target_currency):
    """After native-year escalation, convert all price components once via shared FX."""
    from dataclasses import replace

    from backend.currency_conversion import convert_currency

    estimate = calculation.estimate
    if not target_currency or estimate.currency == target_currency:
        return calculation
    audit = convert_currency(estimate.amount, estimate.currency, target_currency)
    rate = float(audit["rate"])

    def scale(value):
        return None if value is None else value * rate

    installation = calculation.installation
    if installation:
        installation = replace(
            installation,
            equipment_cost=scale(installation.equipment_cost),
            installation_cost=scale(installation.installation_cost),
            equipment_and_installation_cost=scale(
                installation.equipment_and_installation_cost
            ),
        )
    return replace(
        calculation,
        estimate=replace(
            estimate,
            amount=float(audit["amount"]),
            currency=target_currency,
            cost_index=1,
            index_series="PRICE_BASIS:" + target_currency + ":" + estimate.period,
        ),
        installation=installation,
        evidence={**calculation.evidence, "currency_conversion": audit},
    )
