"""Explicit revenue worksheet edits; canonical approval and Python calculation stay in charge."""

import copy
from datetime import date
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator
from .indexes.openpytea.rate_model import RATE_UNITS


class RateLine(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    @field_validator(
        "rate",
        "price",
        "sold_fraction",
        "saleable_fraction",
        "allocation_fraction",
        mode="before",
    )
    @classmethod
    def numeric_input(cls, value):
        if isinstance(value, bool):
            raise ValueError("Enter a number, not a boolean")
        return value

    id: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=200)
    kind: Literal["product", "service"]
    category: (
        Literal[
            "product_sales",
            "processing_services",
            "capacity_availability",
            "infrastructure_usage",
            "environmental_attributes",
            "other_contractual_income",
        ]
        | None
    ) = None
    role: Literal["main_product", "byproduct"] = "main_product"
    method_form: dict | None = None
    price_review: dict | None = None
    stream_key: str | None = None
    component: str | None = None
    rate: float | None = Field(default=None, ge=0)
    rate_unit: str = "m3/h"
    price: float | None = Field(default=None, ge=0)
    price_unit: str = Field(default="m3", min_length=1, max_length=80)
    price_period: str | None = Field(default=None, max_length=80)
    sold_fraction: float = Field(default=1, ge=0, le=1)
    saleable_fraction: float = Field(default=1, ge=0, le=1)
    allocation_fraction: float = Field(default=1, ge=0, le=1)
    rationale: str = Field(
        default="Explicit user revenue worksheet assumption",
        min_length=1,
        max_length=3000,
    )


class RateStudyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    revision: int
    lines: list[RateLine] = Field(default_factory=list, max_length=100)
    remove: list[str] = Field(default_factory=list, max_length=100)
    days_per_year: float = Field(gt=0, le=366)
    hours_per_day: float = Field(gt=0, le=24)
    operating_years: int | None = Field(default=None, ge=1, le=50)
    approve: bool = False


def save_rates(store, key, request):
    from backend.blocks.execution import refresh, view
    from backend.blocks.cashflow.schedule import apply_policy
    from backend.orchestration.register import register
    from .authority import bind, update

    state = store.get(key)
    if state["revision"] != request.revision or state.get("running"):
        raise ValueError(
            "Reload the current assessment after the active calculation finishes"
        )
    if len({line.id for line in request.lines}) != len(request.lines):
        raise ValueError("Revenue line IDs must be unique")
    if set(request.remove) & {line.id for line in request.lines}:
        raise ValueError("A revenue line cannot be both changed and removed")
    config = copy.deepcopy(state["plan"].get("operating_economics") or {})
    config.pop("_revenue_authority", None)
    config.setdefault("methodology", "garrett")
    config.setdefault("assumption_date", date.today().isoformat())
    config.setdefault(
        "price_basis", {"currency": "USD", "price_period": str(date.today().year)}
    )
    config.setdefault("origin", "Explicit user revenue worksheet")
    config.setdefault("sales", [])
    config.setdefault("commercial_lines", [])
    config.setdefault("avoided_costs", [])
    config.setdefault(
        "financial",
        {"operating_years": 20, "construction_years": 0, "production_ramp": [1]},
    )
    config["operating"] = {
        **config.get("operating", {}),
        "days_per_year": request.days_per_year,
        "hours_per_day": request.hours_per_day,
        "rationale": "Explicit user-approved operating calendar; not a universal plant maximum",
    }
    schedule = state.get("analysis_schedule")
    if (
        request.operating_years is not None
        and request.operating_years != config["financial"]["operating_years"]
    ):
        from backend.blocks.cashflow.view import snapshot
        from backend.blocks.cashflow.schedule import make_policy

        previous = snapshot(state)["policy"]
        schedule = make_policy(
            request.operating_years + previous["construction_years"],
            previous["construction_years"],
            previous,
        )
    config = apply_policy(config, schedule)
    life = int(config["financial"]["operating_years"])
    changed = {r.id for r in request.lines} | set(request.remove)
    old_rows = [
        r
        for group in ("sales", "commercial_lines", "pending_inputs")
        for r in config.get(group, [])
        if r.get("id") in changed
    ]
    intents_removed = {r.get("intent_id") or r.get("id") for r in old_rows}
    for group in ("sales", "commercial_lines", "pending_inputs"):
        config[group] = [r for r in config.get(group, []) if r.get("id") not in changed]
    intent = copy.deepcopy(
        config.get("commercial_intent")
        or {"status": "explicit", "mechanisms": [], "questions": []}
    )
    intent["mechanisms"] = [
        r for r in intent.get("mechanisms", []) if r.get("id") not in intents_removed
    ]
    text = state.get("revenue_description") or ""
    report = (
        state.get("scoped_report")
        or state.get("effective_report")
        or state.get("parsed", {}).get("report", {})
    )
    for line in request.lines:
        previous = next((r for r in old_rows if r.get("id") == line.id), {})
        if previous.get("quantity_unit") != line.price_unit and any(
            previous.get(k)
            for k in (
                "net_freight_deduction_per_unit",
                "net_packaging_deduction_per_unit",
            )
        ):
            raise ValueError(
                line.name
                + ": update the existing per-unit deductions in Advanced contracts before changing the price unit"
            )
        quote = (
            "Sell "
            if line.kind == "product"
            else "Receive "
            + (line.category or "processing_services").replace("_", " ")
            + " income for "
        ) + line.name
        if quote.casefold() not in text.casefold():
            text += "\n" + quote
        if line.stream_key and not any(
            e.get("key") == line.stream_key and e.get("kind") == "material"
            for e in report.get("entities", [])
        ):
            raise ValueError(
                line.name + ": select a material stream from this workbook"
            )
        method = line.category or (
            "product_sales" if line.kind == "product" else "processing_services"
        )
        if not line.method_form and line.price_unit not in {
            "kg",
            "tonne",
            "m3",
            "L",
            "lb",
        }:
            raise ValueError("Choose a compatible physical price quantity unit")
        if (line.kind == "product") != (method == "product_sales"):
            raise ValueError("Revenue kind must agree with its MECE category")
        if (
            request.approve
            and not line.method_form
            and not line.stream_key
            and (line.rate is None or line.rate_unit not in RATE_UNITS)
        ):
            raise ValueError(line.name + ": enter a rate and time unit, such as 2 m3/h")
        identity = "worksheet:" + line.id
        category = method
        intent["mechanisms"].append(
            {
                "id": identity,
                "category": category,
                "context_quote": quote,
                "interpretation": "Explicit user-defined revenue method",
            }
        )
        common = {
            **previous,
            "id": line.id,
            "name": line.name,
            "stream_key": line.stream_key,
            "component": line.component,
            "quantity_unit": line.price_unit,
            "context_quote": quote,
            "intent_id": identity,
            "price_basis": {
                "currency": config["price_basis"]["currency"],
                "price_period": line.price_period
                or config["price_basis"]["price_period"],
            },
            "rationale": line.rationale,
            "uncertainty": "User planning assumption; not a verified market contract",
        }
        if line.price_review is not None:
            from .price_review import validate_review

            common["price_review"] = validate_review(
                line.price_review, line.price, line.price_unit, common["price_basis"]
            )
        # An explicit worksheet price supersedes an old researched observation.
        # The prior observation remains recoverable in the saved version history.
        common.pop("price_observation", None)
        common.pop("manual_rate", None)
        common.pop("method_form", None)
        if not line.stream_key and line.rate is not None:
            common["manual_rate"] = {
                "value": line.rate,
                "unit": line.rate_unit,
                "confirmed_by_user": True,
                "rationale": line.rationale,
            }
        if line.method_form:
            from .method_forms import build_line

            form = line.method_form
            if method == "product_sales" or form.get("method") != method:
                raise ValueError(
                    "Choose stream-rate inputs for products, and matching method-specific terms for contracts"
                )
            built = build_line(
                method, form.get("subtype"), form.get("inputs"), life, identity=line.id
            )
            built.update(
                context_quote=quote,
                intent_id=identity,
                price_basis=common["price_basis"],
            )
            if line.price_review is not None:
                built["price_review"] = common["price_review"]
            config["commercial_lines"].append(built)
        elif method not in {"product_sales", "processing_services"}:
            raise ValueError("Enter the required method-specific commercial terms")
        elif line.kind == "product":
            config["sales"].append(
                {
                    **common,
                    "role": line.role,
                    "price_mode": "assumed_price",
                    "unit_price": line.price,
                    "allocation_fraction": line.allocation_fraction,
                    "saleable_fraction": line.saleable_fraction,
                    "sold_fraction": line.sold_fraction,
                    "cost_markup_fraction": 0,
                    "net_freight_deduction_per_unit": previous.get(
                        "net_freight_deduction_per_unit", 0
                    ),
                    "net_packaging_deduction_per_unit": previous.get(
                        "net_packaging_deduction_per_unit", 0
                    ),
                    "specification_basis": "User-specified product; quality and acceptance fractions remain editable",
                }
            )
        else:
            config["commercial_lines"].append(
                {
                    **common,
                    "category": category,
                    "rate_period": "per_unit",
                    "payment_id": line.id,
                    "fixed_variable_distinct": True,
                    "eligibility_basis": "User-specified per-unit processing-fee forecast; no signed contract implied",
                    "property": (
                        "component_volume_flow"
                        if line.component and line.price_unit in {"m3", "L"}
                        else (
                            "component_mass_flow"
                            if line.component
                            else (
                                "volume_flow"
                                if line.price_unit in {"m3", "L"}
                                else "mass_flow"
                            )
                        )
                    ),
                    "payment_rule": "variable_fee",
                    "arrangement": "user_assumption",
                    "source_references": previous.get("source_references", []),
                    "years": [
                        {
                            "year": y,
                            "fixed_payment": 0,
                            "minimum_quantity": 0,
                            "minimum_payment": 0,
                            "availability": 1,
                            "escalation": 0,
                            "periods": 1,
                            **next(
                                (
                                    t
                                    for t in previous.get("years", [])
                                    if t.get("year") == y
                                ),
                                {},
                            ),
                            "rate": line.price,
                            "quantity": None,
                        }
                        for y in range(1, life + 1)
                    ],
                }
            )
    if len(text) > 48000:
        raise ValueError(
            "Consolidate the Revenue Box before adding more income methods"
        )
    intent["status"] = "explicit"
    config["commercial_intent"] = intent
    config["intent_source"] = "user_override"
    config["intent_override_reason"] = "Explicit structured revenue worksheet edit"
    if request.approve:
        from .authority import questions
        from backend.blocks.shared import operating_schedule
        from backend.blocks.revenue.input_builder import _revenue_project
        from backend.opex.models import Basis
        from . import calculate_revenue

        missing = questions(config, text, report, require_approval=False)
        if missing:
            raise ValueError(" ".join(missing))
        hours, ramp = operating_schedule(config)
        checked = calculate_revenue(
            _revenue_project(
                report, text, config, Basis(**config["price_basis"]), hours, ramp, {}
            ),
            engineering_scenario=True,
        )
        if checked.issues:
            raise ValueError(" ".join(checked.issues))
    store.version(key, "Before revenue rate worksheet edit")
    state["plan"]["operating_economics"] = config
    if schedule:
        state["analysis_schedule"] = schedule
    state["revenue_description"] = text.strip()
    state["description"] = (
        state.get("process_description", state.get("description", ""))
        + "\n\nUSER REVENUE DESCRIPTION:\n"
        + text.strip()
    )
    state.pop("revenue_approval", None)
    state["assumption_register"] = register(state["plan"], state.get("assumptions", {}))
    bind(state)
    refresh(state)
    state = store.put(state, request.revision)
    if request.approve:
        return update(store, key, state["revision"], approve=True)
    return view(state)
