"""Read-only commercial preflight: collect known blockers before asking the analyst."""

import copy
from decimal import Decimal, InvalidOperation
from .authority import questions


def inspect_revenue(config, text, report):
    config = copy.deepcopy(config)
    config.pop("_revenue_authority", None)
    problems = questions(config, text, report, require_approval=False)

    def valid(value, maximum=None):
        try:
            n = Decimal(str(value))
            return (
                not isinstance(value, bool)
                and n.is_finite()
                and n >= 0
                and (maximum is None or n <= maximum)
            )
        except (InvalidOperation, ValueError, TypeError):
            return False

    for sale in config.get("sales", []):
        name = sale.get("name", sale.get("id", "product"))
        for field, label in [
            ("allocation_fraction", "allocation"),
            ("saleable_fraction", "saleable output"),
            ("sold_fraction", "sold output"),
        ]:
            if not valid(sale.get(field), 1):
                problems.append(f"What {label} fraction (0–1) applies to {name}?")
        for field, label in [
            ("net_freight_deduction_per_unit", "freight deduction"),
            ("net_packaging_deduction_per_unit", "packaging deduction"),
        ]:
            if not valid(sale.get(field)):
                problems.append(
                    f"What {label} per unit applies to {name}? Select zero only if none is assumed."
                )
    for line in config.get("commercial_lines", []):
        name = line.get("name", line.get("id", "payment"))
        for annual in line.get("years", []):
            year = annual.get("year")
            for field in (
                "minimum_quantity",
                "minimum_payment",
                "availability",
                "escalation",
            ):
                value = annual.get(field)
                ok = valid(value, 1 if field == "availability" else None)
                if field == "escalation":
                    try:
                        n = Decimal(str(value))
                        ok = n.is_finite() and n > -1
                    except (InvalidOperation, ValueError, TypeError):
                        ok = False
                if not ok:
                    problems.append(
                        f'Confirm {field.replace("_", " ")} for {name}, operating year {year}.'
                    )
    # Run each fully specified source independently to expose different source/unit
    # failures in one review rather than failing at the first line in the workbook.
    from backend.blocks.revenue.input_builder import _revenue_project
    from backend.blocks.shared import operating_schedule
    from backend.opex.models import Basis
    from . import calculate_revenue

    try:
        hours, ramp = operating_schedule(config)
        basis = Basis(**config["price_basis"])
    except (ValueError, TypeError, KeyError, ArithmeticError) as exc:
        problems.append("Complete the operating calendar and price basis: " + str(exc))
    else:
        for group in ("sales", "commercial_lines"):
            for source in config.get(group, []):
                isolated = copy.deepcopy(config)
                isolated["sales"] = [source] if group == "sales" else []
                isolated["commercial_lines"] = (
                    [source] if group == "commercial_lines" else []
                )
                isolated["pending_inputs"] = []
                isolated["avoided_costs"] = []
                intent = isolated.get("commercial_intent", {})
                intent["mechanisms"] = [
                    m
                    for m in intent.get("mechanisms", [])
                    if m.get("id") == source.get("intent_id")
                ]
                if questions(isolated, text, report, require_approval=False):
                    continue
                if group == "sales" and any(
                    not valid(source.get(field), maximum)
                    for field, maximum in [
                        ("allocation_fraction", 1),
                        ("saleable_fraction", 1),
                        ("sold_fraction", 1),
                        ("net_freight_deduction_per_unit", None),
                        ("net_packaging_deduction_per_unit", None),
                    ]
                ):
                    continue
                try:
                    result = calculate_revenue(
                        _revenue_project(
                            report, text, isolated, basis, hours, ramp, {}
                        ),
                        engineering_scenario=True,
                    )
                    problems.extend(str(x) for x in result.issues)
                except (ValueError, TypeError, KeyError, ArithmeticError) as exc:
                    problems.append(
                        str(source.get("name", source.get("id", "Income")))
                        + ": "
                        + str(exc)
                    )
    if not problems:
        try:
            complete = calculate_revenue(
                _revenue_project(report, text, config, basis, hours, ramp, {}),
                engineering_scenario=True,
            )
            problems.extend(str(x) for x in complete.issues)
        except (ValueError, TypeError, KeyError, ArithmeticError) as exc:
            problems.append(str(exc))
    problems = list(dict.fromkeys(problems))
    return {
        "questions": problems,
        "ready": not problems,
        "line_count": len(config.get("sales", []))
        + len(config.get("commercial_lines", [])),
    }
