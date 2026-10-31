"""Deterministic quantity-sold × net-price schedules. No model calls or prices."""

from datetime import date
from decimal import Decimal, localcontext

from backend.equipment_costing.unit_conversion import convert
from backend.opex.engine import overlaps

from .indexes.garrett.model import MODEL, SOURCE
from .models import AnnualRevenue, ProductRevenue, RevenueProject, RevenueResult

ZERO = Decimal(0)
ONE = Decimal(1)


def read(assumption, unit=None, *, minimum=ZERO, maximum=None):
    if assumption.value is None:
        raise ValueError("Missing assumption value: " + (unit or assumption.unit))
    if assumption.status not in {"source_supported", "user_assumption", "llm_estimate"}:
        raise ValueError("Unsupported assumption evidence status")
    if not assumption.rationale.strip() or not assumption.uncertainty.strip():
        raise ValueError("Assumption rationale and uncertainty required")
    if assumption.status == "source_supported" and not assumption.source.strip():
        raise ValueError("Source-supported assumption needs a source")
    try:
        date.fromisoformat(assumption.as_of)
    except ValueError as exc:
        raise ValueError("Assumption requires an ISO evidence/assumption date") from exc
    if unit is not None and assumption.unit != unit:
        raise ValueError(
            "Unit mismatch: expected " + unit + ", received " + assumption.unit
        )
    value = assumption.value
    if (
        minimum is not None
        and value < minimum
        or maximum is not None
        and value > maximum
    ):
        raise ValueError(
            "Assumption outside allowed physical/commercial bounds: " + assumption.unit
        )
    return value


def _calculate_products(project, *, preview=False, engineering_scenario=False):
    if not isinstance(project, RevenueProject):
        raise TypeError("project must be RevenueProject")
    if project.model_id != "garrett":
        raise ValueError("Unsupported revenue methodology: " + project.model_id)
    if not isinstance(engineering_scenario, bool):
        raise TypeError("engineering_scenario must be boolean")
    if not isinstance(preview, bool):
        raise TypeError("preview must be boolean")
    with localcontext() as context:
        context.prec = 40
        return _calculate(project, preview, engineering_scenario)


def _calculate(project, preview, engineering_scenario=False):
    from .snapshots import snapshot_id

    issues, rows, warnings = (
        [],
        [],
        [
            "Preliminary commercial assumptions; no verified demand, buyer commitment or contract probability is implied."
        ],
    )
    if engineering_scenario:
        warnings.append(
            "Conditional AI engineering scenario: saleability/quality and commercial assumptions have not been user-approved or independently verified. Numerical outputs are conditional, not confirmed sales."
        )
    streams, schedule = {}, {}
    if (
        not project.id.strip()
        or not project.actor.strip()
        or not project.change_reason.strip()
    ):
        issues.append("Project identity and change provenance required")
    for stream in project.streams:
        if not stream.id.strip() or stream.id in streams:
            issues.append("Missing or duplicate stream identifier: " + stream.id)
        streams[stream.id] = stream
    for year in project.schedule:
        if year.year in schedule:
            issues.append("Duplicate operating year")
        schedule[year.year] = year
    if not schedule:
        issues.append("Explicit annual operating schedule required")
    if not project.products:
        issues.append(
            "No product decisions: outlet streams are not automatically sales"
        )
    allocated, product_ids = {}, set()
    for product in project.products:
        label = product.id + ": "
        if not product.id.strip() or product.id in product_ids:
            issues.append("Missing or duplicate product ID: " + product.id)
        product_ids.add(product.id)
        if not product.included:
            if not product.exclusion_reason.strip():
                issues.append(label + "excluded product needs a reason")
            continue
        try:
            if not product.name.strip():
                raise ValueError("Product name required")
            if (
                not preview
                and not engineering_scenario
                and (not product.reviewed or not product.review_reason.strip())
            ):
                raise ValueError("Saleability and assumptions need user review")
            if (
                product.specification_status != "confirmed"
                and not (
                    engineering_scenario
                    and product.specification_status in {"provisional", "assumed"}
                )
            ) or not product.specification_basis.strip():
                raise ValueError(
                    "Product specification/customer suitability unresolved"
                )
            if product.role not in {"main_product", "byproduct"}:
                raise ValueError("Select main_product or byproduct")
            stream = streams.get(product.stream_id)
            if stream is None or stream.boundary != "outlet":
                raise ValueError(
                    "Sale needs an identified outlet stream; no physical route is inferred"
                )
            if not stream.source_references or not all(
                ref.strip() for ref in stream.source_references
            ):
                raise ValueError("Stream source references required")
            if stream.flow.status == "llm_estimate":
                raise ValueError("LLM estimates cannot establish physical stream flow")
            if not engineering_scenario and (
                product.allocation_fraction.status == "llm_estimate"
                or product.saleable_fraction.status == "llm_estimate"
            ):
                raise ValueError(
                    "Physical allocation and quality fractions require engineering evidence or explicit user assumptions, not LLM values"
                )
            flow = read(stream.flow)
            converted = convert(
                float(flow),
                stream.flow.unit,
                product.quantity_unit + "/h",
                context=stream.conversion_context,
                source={"references": stream.source_references},
            )
            if converted.value is None:
                raise ValueError(
                    "Unsupported or inconsistent flow/price quantity units: "
                    + "; ".join(converted.issues)
                )
            normalized = Decimal(str(converted.value))
            if normalized < 0 or not normalized.is_finite():
                raise ValueError("Invalid normalized stream flow")
            allocation = read(product.allocation_fraction, "fraction", maximum=ONE)
            quality = read(product.saleable_fraction, "fraction", maximum=ONE)
            allocated[stream.id] = allocated.get(stream.id, ZERO) + allocation
            if allocated[stream.id] > ONE:
                raise ValueError(
                    "Product allocations exceed the available stream; duplicate sales risk"
                )
            if (
                product.price_basis not in {"net_fob", "gross_quote"}
                or not product.price_terms.strip()
            ):
                raise ValueError("Price basis and delivery/commercial terms required")
            if set(product.included_charges) & set(product.additional_charge_scopes):
                raise ValueError("A charge cannot be both included and additional")
            if len(set(product.included_charges)) != len(
                product.included_charges
            ) or len(set(product.additional_charge_scopes)) != len(
                product.additional_charge_scopes
            ):
                raise ValueError("Duplicate price charge scopes")
            product_years = {year.year: year for year in product.years}
            if len(product_years) != len(product.years) or set(product_years) != set(
                schedule
            ):
                raise ValueError(
                    "Product years must match the explicit project schedule exactly"
                )
            if (
                not product.market.geography.strip()
                or not product.market.customer_requirements.strip()
            ):
                warnings.append(
                    label + "market geography or customer requirements not established"
                )
            if not product.market.reference.strip():
                warnings.append(
                    label
                    + "market size, competition and buyer evidence require investigation; no research has been performed"
                )
            for number, year in sorted(product_years.items()):
                try:
                    if any(
                        value.status == "llm_estimate"
                        for value in (
                            product.allocation_fraction,
                            product.saleable_fraction,
                            year.selling_price,
                            year.sales_assumption,
                        )
                    ):
                        warnings.append(
                            label
                            + "contains unverified LLM assumptions; user review is not independent market or engineering verification"
                        )
                    operation = schedule[number]
                    hours = read(
                        operation.operating_hours, "h/year", maximum=Decimal(8784)
                    )
                    throughput = read(
                        operation.throughput_fraction, "fraction", maximum=ONE
                    )
                    produced = normalized * hours * throughput * allocation
                    saleable = produced * quality
                    demand = None
                    if product.market.base_demand is not None:
                        demand = read(
                            product.market.base_demand, product.quantity_unit + "/year"
                        )
                        if product.market.annual_growth is None:
                            raise ValueError(
                                "Explicit market growth assumption required, including zero"
                            )
                        growth = read(
                            product.market.annual_growth,
                            "fraction/year",
                            minimum=Decimal(-1),
                        )
                        if growth <= -1:
                            raise ValueError("Market growth must exceed -100%")
                        demand *= (ONE + growth) ** (number - product.market.base_year)
                    elif product.market.annual_growth is not None:
                        raise ValueError(
                            "Market growth without baseline demand is unresolved"
                        )
                    if year.sales_method == "fraction_of_saleable":
                        sold = saleable * read(
                            year.sales_assumption, "fraction", maximum=ONE
                        )
                    elif year.sales_method == "explicit_quantity":
                        sold = read(
                            year.sales_assumption, product.quantity_unit + "/year"
                        )
                        if sold > saleable:
                            raise ValueError(
                                "Quantity sold exceeds saleable production; no purchased resale or inventory assumed"
                            )
                    elif year.sales_method == "market_share":
                        if demand is None:
                            raise ValueError(
                                "Market-share method requires supported or explicitly assumed demand"
                            )
                        sold = min(
                            saleable,
                            demand
                            * read(year.sales_assumption, "fraction", maximum=ONE),
                        )
                    else:
                        raise ValueError("Unsupported sales method")
                    share = sold / demand if demand else None
                    if demand is not None and sold > demand:
                        raise ValueError(
                            "Sales exceed the defined addressable market; revise assumptions or market scope"
                        )
                    if share is not None and share > Decimal(
                        MODEL["market_share_review_threshold"]
                    ):
                        warnings.append(
                            label
                            + f"year {number}: market share exceeds Garrett's historical 10% guideline; review commercial rationale, not a universal limit"
                        )
                    price = read(
                        year.selling_price,
                        project.basis.currency + "/" + product.quantity_unit,
                    )
                    premium, deduction, opex, scopes, adjustment_ids = (
                        ZERO,
                        ZERO,
                        [],
                        set(),
                        set(),
                    )
                    for adjustment in year.adjustments:
                        if (
                            not adjustment.id.strip()
                            or adjustment.id in adjustment_ids
                            or not adjustment.cost_scope.strip()
                            or any(
                                overlaps(adjustment.cost_scope, scope)
                                for scope in scopes
                            )
                        ):
                            raise ValueError(
                                "Duplicate or missing adjustment identity/scope"
                            )
                        adjustment_ids.add(adjustment.id)
                        scopes.add(adjustment.cost_scope)
                        if adjustment.direction not in {
                            "premium",
                            "deduction",
                        } or adjustment.accounting not in {
                            "revenue",
                            "opex",
                            "included_in_quote",
                        }:
                            raise ValueError(
                                "Unsupported adjustment direction/accounting"
                            )
                        if adjustment.method == "per_unit":
                            per_unit = read(
                                adjustment.assumption,
                                project.basis.currency + "/" + product.quantity_unit,
                            )
                        elif adjustment.method == "fraction_of_quote":
                            fraction = read(
                                adjustment.assumption,
                                "fraction",
                                maximum=ONE
                                if adjustment.direction == "deduction"
                                else None,
                            )
                            per_unit = price * fraction
                        else:
                            raise ValueError(
                                "Unsupported adjustment method; annual selling allowances belong in OPEX"
                            )
                        if adjustment.accounting == "included_in_quote":
                            if adjustment.cost_scope not in product.included_charges:
                                raise ValueError(
                                    "Included adjustment not identified in quoted price scope"
                                )
                            continue
                        if adjustment.cost_scope in product.included_charges:
                            raise ValueError(
                                "Adjustment already included in the price; would double count"
                            )
                        if (
                            adjustment.direction == "deduction"
                            and adjustment.cost_scope
                            not in product.additional_charge_scopes
                        ):
                            raise ValueError(
                                "Additional deduction needs explicit confirmation it is outside quoted/net FOB price"
                            )
                        if adjustment.accounting == "opex":
                            if adjustment.direction != "deduction":
                                raise ValueError(
                                    "Premium is sales revenue, not negative OPEX"
                                )
                            opex.append((adjustment.cost_scope, sold * per_unit))
                        elif adjustment.direction == "premium":
                            premium += per_unit
                        else:
                            deduction += per_unit
                    net_price = price + premium - deduction
                    if net_price < 0:
                        raise ValueError(
                            "Negative net selling price: review disposal/purchasing cost separately in OPEX"
                        )
                    rows.append(
                        ProductRevenue(
                            product.id,
                            stream.id,
                            number,
                            product.quantity_unit,
                            normalized,
                            produced,
                            saleable,
                            sold,
                            saleable - sold,
                            demand,
                            share,
                            price,
                            premium,
                            deduction,
                            net_price,
                            sold * price,
                            sold * net_price,
                            tuple(opex),
                            stream.source_references
                            + (
                                "Conversion: "
                                + stream.flow.unit
                                + " → "
                                + product.quantity_unit
                                + "/h; "
                                + converted.reference,
                            )
                            + converted.assumptions,
                        )
                    )
                except ValueError as exc:
                    issues.append(label + "year " + str(number) + ": " + str(exc))
        except (ValueError, OverflowError) as exc:
            issues.append(label + str(exc))
    linked = {p.stream_id for p in project.products}
    for stream in project.streams:
        if stream.boundary == "outlet" and stream.id not in linked:
            warnings.append(
                stream.id
                + ": outlet has no reviewed commercial decision; not counted as a sale"
            )
    annual = (
        ()
        if issues
        else tuple(
            AnnualRevenue(
                year,
                sum((row.net_sales_revenue for row in rows if row.year == year), ZERO),
                sum(
                    (
                        amount
                        for row in rows
                        if row.year == year
                        for _, amount in row.opex_charges_separate
                    ),
                    ZERO,
                ),
            )
            for year in sorted(schedule)
        )
    )
    return RevenueResult(
        project.model_id,
        snapshot_id(project),
        "needs_review"
        if issues
        else "draft_preview"
        if preview
        else "calculated_preliminary",
        project.basis,
        tuple(rows),
        annual,
        tuple(dict.fromkeys(issues)),
        tuple(dict.fromkeys(warnings)),
        SOURCE.reference,
    )


def calculate_revenue(project, *, preview=False, engineering_scenario=False):
    """Canonical six-category aggregation, retaining the established product engine."""
    from dataclasses import replace

    from .economic_savings.avoided_costs import validate_savings
    from .models import AnnualRevenue
    from .registry import get_category
    from .snapshots import snapshot_id

    if not isinstance(project, RevenueProject):
        raise TypeError("project must be RevenueProject")
    # Legacy product-only projects preserve their previous exact results/contracts.
    if not project.commercial_lines and not project.avoided_costs:
        return _calculate_products(
            project, preview=preview, engineering_scenario=engineering_scenario
        )
    result = _calculate_products(
        project, preview=preview, engineering_scenario=engineering_scenario
    )
    issues = list(result.issues)
    if not project.products:
        issues = [i for i in issues if not i.startswith("No product decisions:")]
    rows, ids, payments = (
        [],
        {p.id.strip().casefold() for p in project.products},
        {p.id.strip().casefold() for p in project.products},
    )
    schedule = [y.year for y in project.schedule]
    with localcontext() as context:
        context.prec = 40
        for line in project.commercial_lines:
            try:
                if (
                    line.id.strip().casefold() in ids
                    or line.payment_id.strip().casefold() in payments
                ):
                    raise ValueError(
                        "Duplicate revenue line/payment identity across categories"
                    )
                ids.add(line.id.strip().casefold())
                payments.add(line.payment_id.strip().casefold())
                rows.extend(
                    get_category(line.category)(
                        line, currency=project.basis.currency, schedule=schedule
                    )
                )
            except (ValueError, TypeError) as exc:
                issues.append(line.id + ": " + str(exc))
        try:
            validate_savings(project.avoided_costs, schedule, project.basis.currency)
        except (ValueError, TypeError) as exc:
            issues.append("Avoided costs: " + str(exc))
        annual = (
            ()
            if issues
            else tuple(
                AnnualRevenue(
                    y,
                    sum(
                        (p.net_sales_revenue for p in result.products if p.year == y),
                        ZERO,
                    )
                    + sum((r.revenue for r in rows if r.year == y), ZERO),
                    sum(
                        (
                            v
                            for p in result.products
                            if p.year == y
                            for _, v in p.opex_charges_separate
                        ),
                        ZERO,
                    ),
                )
                for y in sorted(schedule)
            )
        )
    return replace(
        result,
        snapshot_id=snapshot_id(project),
        commercial=tuple(rows),
        annual=annual,
        avoided_costs=project.avoided_costs,
        issues=tuple(dict.fromkeys(issues)),
        status="needs_review"
        if issues
        else "draft_preview"
        if preview
        else "calculated_preliminary",
    )
