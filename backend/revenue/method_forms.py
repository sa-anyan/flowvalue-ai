"""Shared method-specific form contracts and adapters to existing payment engines."""
import copy
from decimal import Decimal, InvalidOperation
import math
import uuid


def field(key, label, kind="number", required=True, choices=None):
    return {"key": key, "label": label, "kind": kind, "required": required, "choices": choices or []}

UNIT = field("unit", "Quantity unit (e.g. kg, tonne, pallet-day)", "text")
ESCALATION = field("escalation", "Annual escalation fraction (optional; blank = constant rate)", required=False)
FEE = [field("fixed_fee", "Additional fixed annual fee (optional)", required=False), field("fixed_scope", "Distinct scope of the additional fee (required when a fee is entered)", "text", False)]
FORMS = {
 "product_sales": {"label": "Product sales", "variants": {"sold_quantity": {"label": "Quantity sold × net price", "fields": [field("quantity", "Annual quantity actually sold"), field("rate", "Net selling price per unit"), UNIT, ESCALATION]}}},
 "processing_services": {"label": "Processing services", "variants": {"processed_quantity": {"label": "Billable processing quantity × tariff", "fields": [field("quantity", "Annual customer quantity processed (exclude own production)"), field("rate", "Processing tariff per unit"), UNIT, *FEE, ESCALATION]}}},
 "capacity_availability": {"label": "Capacity / availability", "variants": {"reservation": {"label": "Contracted capacity reservation", "fields": [field("quantity", "Reserved capacity (not annual throughput)"), field("rate", "Reservation rate per capacity unit per billing period"), UNIT, field("period", "Reservation billing period", "select", True, ["annual", "monthly"]), field("availability", "Qualifying availability fraction (0–1)"), *FEE, ESCALATION]}}},
 "infrastructure_usage": {"label": "Infrastructure usage", "variants": {"usage": {"label": "Measured annual usage × tariff", "fields": [field("quantity", "Total annual billable usage (e.g. occupied pallet-days)"), field("rate", "Tariff per usage unit"), UNIT, *FEE, ESCALATION]}, "subscription": {"label": "Reserved units charged monthly", "fields": [field("quantity", "Number of reserved units each month"), field("rate", "Monthly tariff per reserved unit"), UNIT, *FEE, ESCALATION]}}},
 "environmental_attributes": {"label": "Environmental attributes", "variants": {"credits": {"label": "Eligible credits sold × price", "fields": [field("quantity", "Annual credits / certificates actually sold"), field("rate", "Price per credit / certificate"), field("eligibility", "Eligibility basis or explicit scenario assumption", "text"), field("ownership", "Ownership and right to sell", "text"), ESCALATION]}}},
 "other_contractual_income": {"label": "Other contractual income", "variants": {"fixed": {"label": "Fixed annual payment / licence", "fields": [field("fixed", "Annual contractual payment"), ESCALATION]}, "variable": {"label": "Variable contractual payment", "fields": [field("quantity", "Annual contractual billable quantity"), field("rate", "Contractual rate per unit"), UNIT, *FEE, ESCALATION]}}},
}


def catalogue():
    return copy.deepcopy(FORMS)


def build_line(method, subtype, values, years, *, identity=None):
    if method not in FORMS or subtype not in FORMS[method]["variants"]:
        raise ValueError("Choose a valid MECE method and payment basis")
    if type(years) is not int or not 1 <= years <= 50:
        raise ValueError("Declare an operating life of 1–50 years")
    if not isinstance(values, dict):
        raise ValueError("Provide method inputs")
    rules = FORMS[method]["variants"][subtype]["fields"]
    allowed = {r["key"] for r in rules} | {"name", "description"}
    if set(values) - allowed:
        raise ValueError("Inputs do not belong to the selected payment method")
    clean = {}
    for r in [field("name", "Revenue name", "text"), field("description", "Payment description / basis", "text"), *rules]:
        value = values.get(r["key"])
        if value is None or value == "":
            if r["required"]:
                raise ValueError(r["label"] + " is required")
            continue
        if r["kind"] == "number":
            try:
                number = Decimal(str(value))
                if isinstance(value, bool) or not number.is_finite() or not math.isfinite(float(number)):
                    raise ValueError()
            except (ValueError, InvalidOperation, OverflowError):
                raise ValueError(r["label"] + " must be a finite number") from None
            if number < 0 and r["key"] != "escalation":
                raise ValueError(r["label"] + " cannot be negative")
            if r["key"] == "escalation" and number <= -1:
                raise ValueError("Escalation must be greater than -1")
            if r["key"] == "availability" and number > 1:
                raise ValueError("Availability must be between 0 and 1")
            clean[r["key"]] = float(number)
        else:
            if not isinstance(value, str) or not value.strip():
                raise ValueError(r["label"] + " is required")
            clean[r["key"]] = value.strip()
            if r["choices"] and value not in r["choices"]:
                raise ValueError("Choose a valid " + r["label"].lower())
    if clean.get("fixed_fee", 0) and not clean.get("fixed_scope"):
        raise ValueError("Explain the distinct scope of the additional fixed fee")
    unit = "credit" if subtype == "credits" else "payment" if subtype == "fixed" else clean["unit"]
    if "/" in unit or any(c in unit for c in "$£€"):
        raise ValueError("Quantity unit must not contain a price or billing period")
    period = clean.get("period", "monthly" if subtype == "subscription" else "per_unit")
    identifier = identity or uuid.uuid4().hex
    line = {"id": identifier, "payment_id": identifier, "name": clean["name"], "category": method,
        "quantity_unit": unit, "rate_period": period, "arrangement": "user_assumption", "context_quote": "",
        "rationale": clean["description"], "uncertainty": "Explicit user inputs; not an independently verified contract",
        "source_references": [], "stream_key": None, "property": "contract_quantity", "component": None,
        "fixed_variable_distinct": bool(clean.get("fixed_fee")),
        "eligibility_basis": (clean.get("eligibility", "") + "; ownership/right to sell: " + clean.get("ownership", "")) if subtype == "credits" else "",
        "years": [{"year": y, "quantity": clean.get("quantity", 0), "rate": clean.get("rate", 0),
                   "fixed_payment": clean.get("fixed", 0) + clean.get("fixed_fee", 0),
                   "minimum_quantity": 0, "minimum_payment": 0, "availability": clean.get("availability", 1),
                   "escalation": clean.get("escalation", 0), "periods": 12 if period == "monthly" else 1} for y in range(1, years + 1)],
        "method_form": {"method": method, "subtype": subtype, "inputs": clean}}
    return line


def validate_form_line(line, years):
    form = line.get("method_form")
    if not form:
        return  # Existing saved inputs retain their established contracts.
    expected = build_line(form.get("method"), form.get("subtype"), form.get("inputs"), years, identity=line["id"])
    for key in ("category", "name", "quantity_unit", "rate_period", "years", "fixed_variable_distinct", "eligibility_basis"):
        if line.get(key) != expected[key]:
            raise ValueError("Edit this line using its method-specific form: " + key + " does not match the selected method inputs")
