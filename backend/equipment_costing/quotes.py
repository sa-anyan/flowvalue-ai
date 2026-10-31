"""Reviewed comparable quotations through the same equipment total and CAPEX contracts."""

import hashlib
import json
from decimal import Decimal, localcontext
from urllib.parse import urlparse

from .indexes.garrett.installation import InstallationBreakdown
from .indexes.garrett.integrated import CostingResult
from .models import CostEstimate, positive
from .unit_conversion import convert


def decimal(value, maximum=None):
    if isinstance(value, bool):
        raise TypeError("A finite number is required")
    try:
        result = Decimal(str(value))
    except (ArithmeticError, ValueError) as exc:
        raise ValueError("Comparable input must be numeric") from exc
    if (
        not result.is_finite()
        or result < 0
        or (maximum is not None and result > maximum)
    ):
        raise ValueError("Comparable input outside supported bounds")
    return result


def safe_source(url):
    parsed = urlparse(url)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    ):
        raise ValueError("A public HTTPS source is required")
    return url


def comparable_cost(
    reference, *, target_size, target_unit, exponent=None, rationale=""
):
    """Scale a documented comparable; never execute a paper's arbitrary formula."""
    required = {"source_url", "same_configuration_confirmed", "size", "size_unit", "amount", "currency", "price_period"}
    if not isinstance(reference, dict) or not required <= reference.keys():
        raise ValueError("Comparable reference needs source, configuration, size, amount and dated currency basis")
    safe_source(reference["source_url"])
    if reference.get("same_configuration_confirmed") is not True:
        raise ValueError(
            "Comparable material, design and scope must be explicitly confirmed"
        )
    with localcontext() as context:
        context.prec = 30
        conversion = convert(
            float(decimal(target_size)), target_unit, reference["size_unit"]
        )
        if conversion.status != "converted":
            raise ValueError(
                "Comparable size conversion unresolved: " + "; ".join(conversion.issues)
            )
        size = decimal(conversion.value)
        base = decimal(reference["size"])
        if size <= 0 or base <= 0:
            raise ValueError("Positive comparable and target sizes are required")
        if size != base and (exponent is None or not rationale.strip()):
            raise ValueError("Scaling needs an explicit exponent and justification")
        n = decimal(exponent if exponent is not None else 1, maximum=3)
        amount = decimal(reference["amount"]) * (size / base) ** n
        return {
            "amount": amount,
            "currency": reference["currency"],
            "price_period": reference["price_period"],
            "target_size": size,
            "size_unit": reference["size_unit"],
            "reference": reference,
            "exponent": n,
            "rationale": rationale,
            "status": "unverified_comparable_estimate",
            "formula": "C2 = C1 × (S2/S1)^n",
            "escalation_applied": False,
            "notice": "Original dated price basis retained; no automatic escalation or installation allowance.",
        }


def quote_result(quote, target_size, target_unit):
    # One shared comparable-price implementation; no generated formula execution.
    if quote.get("cost_scope") != "purchased_equipment":
        raise ValueError(
            "A comparable must identify the purchased-equipment component separately"
        )
    if not quote.get("price_period") or not quote.get("currency"):
        raise ValueError("Dated quotation currency and period are required")
    scaled = comparable_cost(
        quote,
        target_size=target_size,
        target_unit=target_unit,
        exponent=quote.get("exponent"),
        rationale=quote.get("rationale", ""),
    )
    index = positive(quote.get("cost_index"), "explicit price-period CEPCI index")
    amount = float(scaled["amount"])
    evidence = {
        "method": "reviewed_comparable",
        "reference": quote,
        "calibration": scaled,
        "index_note": "Index labels the price basis; no escalation applied",
        "verification": "user-reviewed assumption, not certified vendor quote",
    }
    estimate = CostEstimate(
        quote.get("equipment", "Comparable equipment"),
        quote.get("configuration", "User-confirmed comparable"),
        amount,
        quote["currency"],
        index,
        quote["price_period"],
        float(scaled["target_size"]),
        quote["size_unit"],
        "purchased_equipment",
        scaled["formula"],
        0,
        0,
        "User-reviewed dated comparable",
        quote["source_url"],
        hashlib.sha256(json.dumps(quote, sort_keys=True).encode()).hexdigest(),
        exponent=float(scaled["exponent"]),
        exponent_basis=quote.get("rationale", ""),
        notes=("Source metadata hash is not a downloaded source-file hash.",),
    )
    installation = InstallationBreakdown(
        amount, None, None, None, "installation_unresolved", evidence
    )
    return CostingResult(
        "provisional",
        estimate,
        amount,
        ("Unverified comparable estimate; installation not provided.",),
        evidence,
        installation=installation,
    )
