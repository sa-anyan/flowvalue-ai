"""Portable saved revenue scenarios; edits never call an LLM or mutate baseline."""

import hashlib
import json
from dataclasses import asdict, replace

from backend.equipment_costing.unit_conversion import ConversionContext
from backend.opex.models import Basis

from .models import (
    Adjustment,
    Assumption,
    AvoidedCost,
    CommercialLine,
    MarketStudy,
    OperatingYear,
    PaymentYear,
    Product,
    ProductYear,
    RevenueProject,
    Stream,
)


def freeze_project(project):
    if not isinstance(project, RevenueProject):
        raise TypeError("project must be RevenueProject")
    return json.dumps(
        {"schema_version": 1, "project": asdict(project)},
        sort_keys=True,
        separators=(",", ":"),
        default=str,
        allow_nan=False,
    )


def snapshot_id(project):
    return hashlib.sha256(freeze_project(project).encode()).hexdigest()


def restore_project(snapshot):
    data = json.loads(snapshot)
    if (
        set(data) != {"schema_version", "project"}
        or type(data["schema_version"]) is not int
        or data["schema_version"] != 1
    ):
        raise ValueError("Unsupported revenue snapshot schema")
    project = data["project"]
    project["basis"] = Basis(**project["basis"])
    project["streams"] = tuple(
        Stream(
            **dict(
                s,
                flow=Assumption(**s["flow"]),
                source_references=tuple(s["source_references"]),
                conversion_context=ConversionContext(**s["conversion_context"]),
            )
        )
        for s in project["streams"]
    )
    project["schedule"] = tuple(
        OperatingYear(
            **dict(
                y,
                operating_hours=Assumption(**y["operating_hours"]),
                throughput_fraction=Assumption(**y["throughput_fraction"]),
            )
        )
        for y in project["schedule"]
    )
    products = []
    for product in project["products"]:
        market = product["market"]
        market = MarketStudy(
            **dict(
                market,
                competitors_and_capacity=tuple(market["competitors_and_capacity"]),
                prospective_customers=tuple(market["prospective_customers"]),
                base_demand=Assumption(**market["base_demand"])
                if market["base_demand"] is not None
                else None,
                annual_growth=Assumption(**market["annual_growth"])
                if market["annual_growth"] is not None
                else None,
            )
        )
        years = tuple(
            ProductYear(
                **dict(
                    y,
                    selling_price=Assumption(**y["selling_price"]),
                    sales_assumption=Assumption(**y["sales_assumption"]),
                    adjustments=tuple(
                        Adjustment(**dict(a, assumption=Assumption(**a["assumption"])))
                        for a in y["adjustments"]
                    ),
                )
            )
            for y in product["years"]
        )
        products.append(
            Product(
                **dict(
                    product,
                    market=market,
                    years=years,
                    allocation_fraction=Assumption(**product["allocation_fraction"]),
                    saleable_fraction=Assumption(**product["saleable_fraction"]),
                    included_charges=tuple(product["included_charges"]),
                    additional_charge_scopes=tuple(product["additional_charge_scopes"]),
                )
            )
        )
    project["products"] = tuple(products)
    project["commercial_lines"] = tuple(
        CommercialLine(
            **dict(
                line,
                source_references=tuple(line["source_references"]),
                years=tuple(
                    PaymentYear(
                        **dict(
                            y,
                            **{
                                k: Assumption(**y[k])
                                for k in (
                                    "quantity",
                                    "rate",
                                    "fixed_payment",
                                    "minimum_quantity",
                                    "minimum_payment",
                                    "availability",
                                    "escalation",
                                )
                            },
                        )
                    )
                    for y in line["years"]
                ),
            )
        )
        for line in project.get("commercial_lines", [])
    )
    project["avoided_costs"] = tuple(
        AvoidedCost(
            **dict(row, years=tuple((y, Assumption(**a)) for y, a in row["years"]))
        )
        for row in project.get("avoided_costs", [])
    )
    return RevenueProject(**project)


def revise_project(
    project,
    *,
    actor,
    reason,
    expected_snapshot_id,
    products=None,
    schedule=None,
    commercial_lines=None,
    avoided_costs=None,
):
    """Editable commercial assumptions. Changed products must be reviewed again."""
    if expected_snapshot_id != snapshot_id(project):
        raise ValueError("Stale revenue revision")
    if (
        not isinstance(actor, str)
        or not actor.strip()
        or not isinstance(reason, str)
        or not reason.strip()
    ):
        raise ValueError("Actor and change reason required")
    if products is None:
        products = project.products
    if schedule is None:
        schedule = project.schedule
    previous = {p.id: p for p in project.products}
    updated = tuple(
        replace(p, reviewed=False, review_reason="")
        if previous.get(p.id) != p or schedule != project.schedule
        else p
        for p in products
    )
    return replace(
        project,
        products=updated,
        commercial_lines=project.commercial_lines
        if commercial_lines is None
        else commercial_lines,
        avoided_costs=project.avoided_costs if avoided_costs is None else avoided_costs,
        schedule=schedule,
        revision=project.revision + 1,
        parent_snapshot_id=snapshot_id(project),
        actor=actor,
        change_reason=reason,
    )


def review_product(project, product_id, *, actor, reason, expected_snapshot_id):
    if not any(p.id == product_id for p in project.products):
        raise ValueError("Unknown product")
    if (
        expected_snapshot_id != snapshot_id(project)
        or not isinstance(actor, str)
        or not actor.strip()
        or not isinstance(reason, str)
        or not reason.strip()
    ):
        raise ValueError("Matching revision, actor and review rationale required")
    return replace(
        project,
        products=tuple(
            replace(p, reviewed=True, review_reason=reason) if p.id == product_id else p
            for p in project.products
        ),
        revision=project.revision + 1,
        parent_snapshot_id=snapshot_id(project),
        actor=actor,
        change_reason=reason,
    )
