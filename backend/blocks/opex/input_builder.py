"""Canonical _costs_for_year adapter, owned by this block."""

import copy
from contextlib import contextmanager
from backend.opex import calculate_opex
from backend.opex.consumption import annual_consumption, decimal, observation
from backend.opex.energy_costs import equipment_energy_cost
from backend.opex.indexes.garrett.model import CATEGORIES, PLANT_BASE, SOURCE
from backend.opex.models import Assumption as Expense
from backend.opex.models import Basis, MoneyBase, OpexInputs
from backend.orchestration.codec import plain
from backend.blocks.shared import _a, operating_schedule, production_schedule


PAYMENT_OWNERS = ("project", "customer", "third_party")
DEFAULT_ESCALATION = "Study price basis and financial escalation policy; no line-specific escalation"


class PriceNeeded(ValueError):
    """A proposed item whose quantity is known but whose price is not."""

    def __init__(self, message, quantity, unit):
        super().__init__(message)
        self.annual_quantity, self.unit = quantity, unit


def _costs_for_year(report, config, basis, hours, ramp, year, *, partial=False):
    costs = []
    detail = {
        "materials": [],
        "energy": [],
        "labour": [],
        "additional_expenses": [],
        "factor_replacements": [],
        "paid_by_others": [],
    }
    seen = set()
    material_sources = set()
    feed_ownership = {}
    detail["pending_items"] = []

    @contextmanager
    def boundary(group, item):
        length = len(costs)
        old_seen, old_sources, old_owners = (
            set(seen),
            set(material_sources),
            copy.deepcopy(feed_ownership),
        )
        lengths = {k: len(v) for k, v in detail.items() if isinstance(v, list)}
        try:
            yield
        except (ValueError, TypeError, KeyError, ArithmeticError) as exc:
            if not partial:
                raise
            del costs[length:]
            for k, n in lengths.items():
                del detail[k][n:]
            seen.clear()
            seen.update(old_seen)
            material_sources.clear()
            material_sources.update(old_sources)
            feed_ownership.clear()
            feed_ownership.update(old_owners)
            detail["pending_items"].append(
                {
                    "group": group,
                    "id": item.get("id", item.get("category", "unknown")),
                    "status": "pending",
                    "reason": str(exc),
                    "excluded_from_known_subtotal": True,
                    **({"annual_quantity": float(exc.annual_quantity), "unit": exc.unit}
                       if isinstance(exc, PriceNeeded) else {}),
                }
            )

    def add(
        key,
        category,
        behavior,
        rationale,
        uncertainty,
        *,
        method,
        quantity=None,
        rate=None,
        amount=None,
        unit="",
        evidence=(),
        item=None,
    ):
        if key in seen:
            raise ValueError("Duplicate operating expense ID: " + key)
        seen.add(key)
        # M4.1: who pays, and the escalation basis, are recorded on every line.
        owner = (item or {}).get("payment_owner") or "project"
        if owner not in PAYMENT_OWNERS:
            raise ValueError(key + ": payment_owner must be one of " + ", ".join(PAYMENT_OWNERS))
        escalation = str((item or {}).get("escalation_basis") or DEFAULT_ESCALATION).strip()
        evidence = (*tuple(evidence), "payment owner: " + owner, "escalation basis: " + escalation)
        if owner != "project":
            # Paid by someone else: shown, never counted in project OPEX.
            if not str((item or {}).get("payment_owner_basis") or "").strip():
                raise ValueError(key + ": a cost paid by " + owner + " needs payment_owner_basis")
            detail["paid_by_others"].append({
                "id": key, "category": category, "payment_owner": owner,
                "basis": item["payment_owner_basis"], "quantity": quantity, "rate": rate,
                "amount": amount if amount is not None else (
                    decimal(quantity) * decimal(rate) if quantity is not None and rate is not None else None),
                "escalation_basis": escalation,
            })
            return
        costs.append(
            Expense(
                key,
                category,
                method,
                behavior,
                basis,
                rationale,
                "Stored operating study / " + SOURCE.reference,
                uncertainty,
                (category + ":" + key,),
                amount=amount,
                quantity=quantity,
                rate=rate,
                quantity_unit=(
                    unit + "/year"
                    if method == "quantity_price"
                    else "FTE" if method == "headcount_salary" else ""
                ),
                rate_unit=(
                    unit
                    if method == "quantity_price"
                    else "FTE/year" if method == "headcount_salary" else ""
                ),
                evidence=tuple(evidence),
            )
        )

    for item in config.get("materials", []):
        with boundary("materials", item):
            item = dict(item)
            if item.get("price_observation"):
                from backend.orchestration.commercial_pricing import adjusted_price

                item["unit_price"] = adjusted_price(
                    item["price_observation"],
                    currency=basis.currency,
                    price_period=basis.price_period,
                    quantity_unit=item["quantity_unit"],
                )["unit_price"]
            if item["property"] == "assumed_annual":
                quantity = decimal(item["annual_quantity_assumption"]) * ramp
                lineage = {
                    "basis": "Explicit assumed annual makeup/consumption, not a workbook quantity"
                }
            else:
                source_key = (item["stream_key"], item["property"], item["component"])
                if source_key in material_sources:
                    raise ValueError("Same feed observation charged more than once")
                previous = feed_ownership.setdefault(item["stream_key"], [])
                component = item.get("component")
                if any(
                    component is None
                    or old is None
                    or component.casefold() == old.casefold()
                    for old in previous
                ):
                    raise ValueError(
                        "Whole delivered feed and its component/alternate-unit observations cannot be charged twice"
                    )
                previous.append(component)
                material_sources.add(source_key)
                lineage = annual_consumption(
                    report,
                    stream_key=item["stream_key"],
                    property=item["property"],
                    component=item["component"],
                    quantity_unit=item["quantity_unit"],
                    operating_hours=hours,
                    throughput_fraction=ramp,
                )
                quantity = lineage["annual_quantity"]
            if item.get("unit_price") in (None, ""):
                # A proposed feed keeps its quantity visible; the price is a question, never 0.
                raise PriceNeeded(
                    f"Price needed for {item.get('name') or item['id']}: "
                    f"{float(quantity):,.0f} {item['quantity_unit']}/year from the M&E balance",
                    quantity, item["quantity_unit"],
                )
            add(
                "feed:" + item["id"],
                item["category"],
                "variable",
                item["rationale"],
                item["uncertainty"],
                method="quantity_price",
                quantity=quantity,
                rate=item["unit_price"],
                unit=item["quantity_unit"],
                item=item,
            )
            detail["materials"].append(
                dict(
                    item,
                    annual_quantity=quantity,
                    annual_cost=quantity * decimal(item["unit_price"]),
                    lineage=plain(lineage),
                )
            )
    equipment_keys = {e["key"] for e in report["entities"] if e["kind"] == "equipment"}
    for item in config.get("energy", []):
        with boundary("energy", item):
            if item["equipment_key"] not in equipment_keys:
                raise ValueError("Energy item must link to an actual equipment record")
            if item.get("tariff_per_kwh") in (None, ""):
                demand = equipment_energy_cost(
                    {**item, "tariff_per_kwh": 0}, report, operating_hours=hours, throughput_fraction=ramp
                )
                raise PriceNeeded(
                    f"Electricity tariff needed for {item.get('name') or item['id']}: "
                    f"{float(demand['annual_energy_kwh']):,.0f} kWh/year from study data",
                    demand["annual_energy_kwh"], "kWh",
                )
            result = equipment_energy_cost(
                item, report, operating_hours=hours, throughput_fraction=ramp
            )
            add(
                "energy:" + item["id"],
                "utilities",
                item["behavior"],
                item["rationale"],
                item["uncertainty"],
                method="quantity_price",
                quantity=result["annual_energy_kwh"],
                rate=item["tariff_per_kwh"],
                unit="kWh",
                evidence=result["source_evidence"],
                item=item,
            )
            detail["energy"].append(result)
    for item in config.get("labour", []):
        with boundary("labour", item):
            fte = decimal(item["headcount_fte"]) * decimal(
                item["allocation_fraction"], maximum=1
            )
            factor_owned = fte == 0 and any(
                c.id == item["category"] and c.base for c in CATEGORIES
            )
            if item["behavior"] == "variable":
                fte *= ramp
            if not factor_owned:
                add(
                    "staff:" + item["id"],
                    item["category"],
                    item["behavior"],
                    item["rationale"],
                    item["uncertainty"],
                    method="headcount_salary",
                    quantity=fte,
                    rate=item["annual_base_salary"],
                    item=item,
                )
            detail["labour"].append(
                dict(
                    item,
                    allocated_fte=fte,
                    annual_cost=fte * decimal(item["annual_base_salary"]),
                    **(
                        {
                            "coverage": "No separate staffing; applicable Garrett category retained"
                        }
                        if factor_owned
                        else {}
                    ),
                )
            )
    for item in config.get("additional_expenses", []):
        with boundary("additional_expenses", item):
            amount = decimal(item["annual_allowance"]) * (
                ramp if item["behavior"] == "variable" else 1
            )
            add(
                "other:" + item["id"],
                item["category"],
                item["behavior"],
                item["rationale"],
                item["uncertainty"],
                method="fixed_annual",
                amount=amount,
                item=item,
            )
            detail["additional_expenses"].append(
                dict(item, effective_annual_cost=amount)
            )
    # A category paid entirely by others is an explicit zero for the project.
    for category in sorted({p["category"] for p in detail["paid_by_others"]} - {c.category for c in costs}):
        costs.append(
            Expense(
                "paid-by-others:" + category, category, "fixed_annual", "fixed", basis,
                "Every item in this category is paid by another party; see paid_by_others",
                "Recorded payment owner decision", "As recorded", (category,), amount=0,
                evidence=("payment owner: others", "escalation basis: not applicable"),
            )
        )
    itemized = {c.category for c in costs}
    # Explicit zero allowances only for categories whose study decision is none, never missing coverage.
    # A proposed item that is only waiting for a price already covers its category.
    awaiting = {"materials": "raw_materials", "energy": "utilities", "labour": "operating_labor"}
    covered = {awaiting[p["group"]] for p in detail["pending_items"] if p.get("group") in awaiting}
    for key in ("raw_materials", "utilities", "operating_labor"):
        if key not in itemized and key not in covered:
            message = (
                "Engineering operating plan needs "
                + key
                + " itemisation (or an explicit zero applicability item)"
            )
            if not partial:
                raise ValueError(message)
            detail["pending_items"].append(
                {
                    "group": "coverage",
                    "id": key,
                    "reason": message,
                    "status": "pending",
                    "excluded_from_known_subtotal": True,
                }
            )
    costs.append(
        Expense(
            "financing:none",
            "interest",
            "fixed_annual",
            "fixed",
            basis,
            "Explicit unlevered planning study: no borrowing/interest; financing is separate from cash OPEX",
            "Study financing policy",
            "Editable unlevered scenario",
            ("interest",),
            amount=0,
        )
    )
    # Net-price deductions and OPEX allowances cannot both own the same charge.
    revenue_owned = set()
    for sale in config.get("sales", []):
        with boundary("sales_charge_ownership", sale):
            if decimal(sale["net_freight_deduction_per_unit"]):
                revenue_owned.add("distribution_sales")
            if decimal(sale["net_packaging_deduction_per_unit"]):
                revenue_owned.add("packaging_storage")
    for definition in CATEGORIES:
        with boundary("garrett_factors", {"id": definition.id}):
            if not definition.base:
                continue
            choice = config["garrett_factors"][definition.id]
            if definition.id in revenue_owned and definition.id not in itemized:
                costs.append(
                    Expense(
                        "revenue-owned:" + definition.id,
                        definition.id,
                        "fixed_annual",
                        "variable",
                        basis,
                        "Charge is already deducted in net selling price; blanket OPEX factor excluded. Remaining selling/packaging scope needs explicit itemisation if applicable.",
                        "Canonical revenue/OPEX charge ownership",
                        "No duplicate charge; residual scope disclosed",
                        (definition.id,),
                        amount=0,
                    )
                )
                detail["factor_replacements"].append(
                    {
                        "category": definition.id,
                        "selected_reference_fraction": choice["fraction"],
                        "reason": "Revenue owns the deduction; no duplicate blanket OPEX allowance. Remaining scope is not separately priced.",
                    }
                )
                continue
            if definition.id in itemized:
                detail["factor_replacements"].append(
                    {
                        "category": definition.id,
                        "selected_reference_fraction": choice["fraction"],
                        "reason": "Detailed itemisation replaces the blanket factor; no double counting",
                        "rationale": choice["rationale"],
                    }
                )
                continue
            behavior = "variable" if definition.base == "annual_revenue" else "fixed"
            costs.append(
                Expense(
                    "garrett:" + definition.id,
                    definition.id,
                    "percentage",
                    behavior,
                    basis,
                    choice["rationale"],
                    SOURCE.reference + "; printed p.52/Table 4-4",
                    "Historical preliminary range; selected engineering assumption",
                    (definition.id,),
                    rate=choice["fraction"],
                    base=definition.base,
                    override=choice.get("override", False),
                    override_reason=choice.get("override_reason", ""),
                )
            )
    return tuple(costs), detail


def _opex(capex, basis, assumptions, annual_sales, *, allow_partial=False):
    bases = []
    if capex is not None:
        for key, amount in (
            ("fixed_capital", capex.fixed_capital),
            ("purchased_equipment", capex.purchased_equipment),
            (
                PLANT_BASE,
                (
                    capex.fixed_capital + capex.startup_expenses
                    if capex.fixed_capital is not None
                    and capex.startup_expenses is not None
                    else None
                ),
            ),
        ):
            if amount is not None:
                bases.append(
                    MoneyBase(key, amount, basis, "Canonical calculated capital scope")
                )
    if annual_sales is not None:
        bases.append(
            MoneyBase("annual_revenue", annual_sales, basis, "Matching annual sales")
        )
    bases = tuple(bases)
    inputs = OpexInputs(
        basis, assumptions, bases, reviewed_categories=tuple(c.id for c in CATEGORIES)
    )
    result = calculate_opex(inputs=inputs)
    if result.annual_cash_opex is None and not allow_partial:
        raise ValueError("Operating plan: " + "; ".join(result.issues))
    return result
