"""Server-owned Revenue Box authority and revision-bound user approval.

No model calls, market prices or inferred revenue sources. Draft economics may
exist, but only the approved commercial inputs can enter a financial calculation.
"""

import copy
import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from .commercial_intent import validate_intent


def bind(state):
    """Keep policy outside editable assumptions so proposals cannot approve themselves."""
    if "id" in state:
        state.setdefault("revenue_description", "")
    if "revenue_description" in state:
        state.setdefault("plan", {})["revenue_authority"] = {
            "text": state.get("revenue_description", ""),
            "approval": state.get("revenue_approval"),
        }
    return state


def fingerprint(config, text, report):
    inputs = {
        k: config.get(k)
        for k in (
            "sales",
            "commercial_lines",
            "avoided_costs",
            "commercial_intent",
            "pending_inputs",
            "operating",
            "price_basis",
        )
    }
    inputs["production"] = {
        k: config.get("financial", {}).get(k)
        for k in ("operating_years", "production_ramp")
    }
    # Quantities and source mappings changing also require a new approval.
    inputs["report"] = {
        "sha256": report.get("sha256"),
        "streams": [
            e
            for e in report.get("entities", [])
            if e.get("kind") in {"material", "energy"}
        ],
    }
    if config.get("cashflow_schedule"):
        inputs["cashflow_schedule"] = config["cashflow_schedule"]
    payload = json.dumps(
        [text, inputs],
        sort_keys=True,
        separators=(",", ":"),
        default=str,
        allow_nan=False,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def questions(config, text, report, *, approval=None, require_approval=True):
    if not text.strip():
        return [
            "How will this project earn revenue? Enter each payment source in the Revenue Box."
        ]
    if not config:
        return [
            "Which streams, prices and operating hours apply to the revenue sources in the Revenue Box?"
        ]
    problems = []
    for pending in config.get("pending_inputs", []):
        missing = pending.get("missing_inputs") or [
            "Confirm the missing commercial terms and quantity basis"
        ]
        problems.append(
            "Pending "
            + str(pending.get("name", pending.get("id", "opportunity")))
            + ": "
            + "; ".join(missing)
        )
    try:
        if not config.get("commercial_intent"):
            raise ValueError("Identify the stated payment methods first")
        validate_intent(config, text)
    except (ValueError, KeyError, TypeError) as exc:
        problems.append("Clarify the Revenue Box payment methods: " + str(exc))
    if config.get("commercial_intent", {}).get("status") == "needs_clarification":
        problems.extend(
            config["commercial_intent"].get("questions", [])
            or ["Which payment sources should this project use?"]
        )
    # Manual-edit rationales cannot substitute for the Revenue Box itself.
    for mechanism in config.get("commercial_intent", {}).get("mechanisms", []):
        quote = mechanism.get("context_quote", "").strip()
        if not quote or quote.casefold() not in text.casefold():
            problems.append(
                "Which Revenue Box statement authorises "
                + mechanism.get("id", "this payment")
                + "?"
            )

    def number(value):
        try:
            return (
                not isinstance(value, bool) and D(value).is_finite() and D(value) >= 0
            )
        except (InvalidOperation, ValueError, TypeError):
            return False

    def D(value):
        return Decimal(str(value))

    from backend.opex.consumption import observation

    for sale in config.get("sales", []):
        name = sale.get("name", sale.get("id", "product"))
        quote = sale.get("context_quote", "").strip()
        if not quote or quote.casefold() not in text.casefold():
            problems.append("Confirm the sale of " + name + " in the Revenue Box.")
        if sale.get("price_mode") != "assumed_price" or not number(
            sale.get("unit_price")
        ):
            problems.append(
                "What selling price and price unit should be used for " + name + "?"
            )
        try:
            from .product_basis import product_observation

            source = product_observation(report, sale)
            if not sale.get("manual_rate") and (
                not source.get("sheet") or not source.get("cell")
            ):
                raise ValueError("No workbook cell")
        except (ValueError, KeyError, TypeError):
            problems.append(
                (
                    "Confirm a compatible custom flow rate and its time unit for "
                    if sale.get("manual_rate")
                    else "Which measured M&E stream supplies the saleable quantity for "
                )
                + name
                + "?"
            )
    for line in config.get("commercial_lines", []):
        quote = line.get("context_quote", "").strip()
        name = line.get("name", line.get("id", "service"))
        if not quote or quote.casefold() not in text.casefold():
            problems.append("Confirm the payment for " + name + " in the Revenue Box.")
        if not line.get("years") or any(
            not number(y.get(k))
            for y in line.get("years", [])
            for k in ("rate", "fixed_payment")
        ):
            problems.append(
                "What fee, billing unit and payment terms apply to " + name + "?"
            )
        if line.get("manual_rate"):
            try:
                from .indexes.openpytea.rate_model import hourly_rate

                hourly_rate(line)
            except (ValueError, KeyError, TypeError):
                problems.append(
                    "Enter a compatible flow rate and time unit for " + name + "."
                )
        elif line.get("stream_key"):
            try:
                source = observation(
                    report,
                    line["stream_key"],
                    line.get("property"),
                    line.get("component"),
                )
                if not source.get("sheet") or not source.get("cell"):
                    raise ValueError("No workbook cell")
            except (ValueError, KeyError, TypeError):
                problems.append(
                    "Which measured M&E stream supplies the billable quantity for "
                    + name
                    + "?"
                )
        elif any(not number(y.get("quantity")) for y in line.get("years", [])):
            problems.append(
                "What contracted quantity should be billed for " + name + "?"
            )
    basis = config.get("price_basis", {})
    if not basis.get("currency") or not basis.get("price_period"):
        problems.append(
            "What currency and price period apply to the supplied revenue prices?"
        )
    operating = config.get("operating", {})
    if (
        not number(operating.get("days_per_year"))
        or not number(operating.get("hours_per_day"))
        or not 0 < D(operating["days_per_year"]) <= 366
        or not 0 < D(operating["hours_per_day"]) <= 24
    ):
        problems.append(
            "How many days per year and hours per day will the plant operate?"
        )
    if (
        not problems
        and require_approval
        and (
            not approval
            or approval.get("fingerprint") != fingerprint(config, text, report)
        )
    ):
        problems.append(
            "Review and approve the current revenue prices, quantities, commercial terms and operating schedule before using them in finance."
        )
    return list(dict.fromkeys(problems))


def runtime(config, policy, report):
    """Validate original approved prices before deterministic FX/escalation adapters."""
    return {
        "text": policy.get("text", ""),
        "questions": questions(
            config, policy.get("text", ""), report, approval=policy.get("approval")
        ),
    }


def require(config):
    policy = config.get("_revenue_authority")
    if policy and policy["questions"]:
        raise ValueError("Revenue Box: " + "; ".join(policy["questions"]))


MAX_REVENUE_REVIEW_LENGTH = 48_000


def update(store, key, revision, *, text=None, approve=False, clarifications=()):
    state = store.get(key)
    if state.get("running") or state["revision"] != revision:
        raise ValueError("Wait for completion or reload the current revision")
    if clarifications:
        base = state.get("revenue_description", "") if text is None else text
        block = "\n\n".join(
            f"Question: {question.strip()}\nMy answer: {answer.strip()}"
            for question, answer in clarifications
        )
        text = f"{base}\n\nREVENUE CLARIFICATIONS:\n{block}"
        if len(text) > MAX_REVENUE_REVIEW_LENGTH:
            raise ValueError(
                "The saved revenue description and clarification history exceed 48,000 characters. "
                "Consolidate earlier clarifications in the Revenue description and try again."
            )
    if text is not None:
        from .price_edits import reconcile_product_price

        previous_text = state.get("revenue_description", "")
        config = state.get("plan", {}).get("operating_economics", {})
        revised = reconcile_product_price(config, previous_text, text)
        if revised is not None:
            state["plan"]["operating_economics"] = revised
            state.setdefault("revenue_price_edits", []).append(
                {
                    "previous_text": previous_text,
                    "text": text,
                    "origin": "explicit_user_revenue_box_edit",
                }
            )
            from backend.orchestration.register import register

            state["assumption_register"] = register(
                state["plan"], state.get("assumptions", {})
            )
        state["revenue_description"] = text
        state["description"] = (
            state.get("process_description", state.get("description", ""))
            + "\n\nUSER REVENUE DESCRIPTION:\n"
            + text
        )
        state.pop("revenue_approval", None)
    config = state.get("plan", {}).get("operating_economics", {})
    if state.get("analysis_schedule"):
        from backend.blocks.cashflow.schedule import apply_policy

        config = apply_policy(config, state["analysis_schedule"])
        state["plan"]["operating_economics"] = config
    report = (
        state.get("scoped_report")
        or state.get("effective_report")
        or state.get("parsed", {}).get("report", {})
    )
    text = state.get("revenue_description", "")
    if approve:
        missing = questions(config, text, report, require_approval=False)
        if missing:
            raise ValueError(" ".join(missing))
        # Validate the actual calculation contracts, not just a checked UI control.
        from backend.orchestration.operating_economics import (
            _revenue_project,
            operating_schedule,
        )
        from backend.opex.models import Basis
        from . import calculate_revenue

        hours, ramp = operating_schedule(config)
        basis = Basis(**config["price_basis"])
        checked = copy.deepcopy(config)
        checked.pop("_revenue_authority", None)
        revenue = calculate_revenue(
            _revenue_project(report, text, checked, basis, hours, ramp, {}),
            engineering_scenario=True,
        )
        if revenue.issues:
            raise ValueError(" ".join(revenue.issues))
        state["revenue_approval"] = {
            "fingerprint": fingerprint(config, text, report),
            "approved_at": datetime.now(timezone.utc).isoformat(),
            "origin": "explicit_user_approval",
        }
    bind(state)
    state["revenue_questions"] = questions(
        config, text, report, approval=state.get("revenue_approval")
    )
    # Do not show stale cash flows while changed commercial inputs await recalculation.
    if state.get("results"):
        for name in (
            ("revenue",)
            if state.get("workflow") == "revenue"
            else ("revenue", "financial")
        ):
            state["results"].setdefault("stages", {})[name] = {
                "status": "pending_user_input",
                "result": None,
                "issues": state["revenue_questions"]
                or ["Recalculate using the approved revenue assumptions."],
            }
    state["status"] = (
        "Revenue approved; Run Again required"
        if approve
        else "Revenue Box updated; review commercial assumptions"
    )
    return store.put(state, revision)
