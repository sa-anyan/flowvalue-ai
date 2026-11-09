"""Project-year view of saved financial and revenue outputs. Never calculate a second ledger."""

from backend.blocks.execution import view as assessment_view


from decimal import Decimal, InvalidOperation


def cash_break_even(result, *, stale=False):
    """Expose canonical project payback; never infer recovery from sales revenue."""
    base = {"year": None, "basis": "Undiscounted cumulative project free cashflow"}
    if not result.get("ledger"):
        return {**base, "status": "pending"}
    if stale:
        return {**base, "status": "stale"}
    metric = dict(result.get("metrics") or []).get("project_payback") or {}
    status = metric.get("status", "pending")
    if status != "calculated":
        return {**base, "status": status}
    try:
        year = Decimal(str(metric["value"]))
        end = max(int(r["period"]["year"]) for r in result["ledger"])
        if not year.is_finite() or not 0 <= year <= end:
            raise ValueError("Payback falls outside the saved ledger")
    except (KeyError, TypeError, ValueError, InvalidOperation):
        return {**base, "status": "pending"}
    return {
        **base,
        "status": "calculated",
        "year": str(year),
        "method": metric.get("basis", "First cumulative recovery"),
    }


def snapshot(saved):
    state = assessment_view(saved)
    config = state.get("plan", {}).get("operating_economics", {})
    financial = config.get("financial", {})
    build = int(financial.get("construction_years", 0))
    life = int(financial.get("operating_years", 20))
    existing_ramp = financial.get("production_ramp") or [1]
    policy = (
        state.get("analysis_schedule")
        or config.get("cashflow_schedule")
        or {
            "analysis_years": life + build,
            "construction_years": build,
            "production_ramp": [
                existing_ramp[min(i, len(existing_ramp) - 1)] for i in range(life)
            ],
            "revenue_factors": {},
            "rationale": financial.get(
                "rationale",
                "Existing planning schedule; review construction and production timing",
            ),
        }
    )
    # Expose the current financial timing, including legacy saved shares, without
    # changing the user's approved baseline just by opening the page.
    import copy

    policy = copy.deepcopy(policy)
    weights = financial.get("construction_spend_fractions") or [1] * max(1, build)
    total = sum(Decimal(str(w)) for w in weights)
    legacy_spend = (
        {
            str(i + 1 if build else 0): float(Decimal(str(w)) / total)
            for i, w in enumerate(weights)
        }
        if total > 0
        else {}
    )
    policy.setdefault("capital_spend_fractions", legacy_spend)
    policy.setdefault(
        "startup_spend_fractions", copy.deepcopy(policy["capital_spend_fractions"])
    )
    policy.setdefault("working_capital_funding_year", build)
    policy.setdefault("fixed_opex_factors", {})
    streams = [
        {
            "id": prefix + str(r["id"]),
            "name": r.get("name", r["id"]),
            "category": r.get("category", "product_sales"),
        }
        for group, prefix in [
            ("sales", "product:"),
            ("commercial_lines", "commercial:"),
        ]
        for r in config.get(group, [])
    ]
    stages = state.get("results", {}).get("stages", {})
    fin = stages.get("financial", {})
    rev = stages.get("revenue", {})
    result = fin.get("result") or {}
    income = rev.get("result") or {}
    ledger = {int(r["period"]["year"]): r for r in result.get("ledger", [])}
    annual = {int(r["year"]): r for r in income.get("annual", [])}
    per_stream = {}
    for group, prefix, key, amount in [
        ("products", "product:", "product_id", "net_sales_revenue"),
        ("commercial", "commercial:", "line_id", "revenue"),
    ]:
        for r in income.get(group, []):
            per_stream.setdefault(int(r["year"]), {})[prefix + str(r[key])] = r.get(
                amount
            )
    rows = []
    for year in range(0, policy["analysis_years"] + 1):
        operating_year = year - build if year > build else None
        row = ledger.get(year, {})
        rows.append(
            {
                "year": year,
                "phase": (
                    "Initial"
                    if year == 0
                    else "Construction" if year <= build else "Operating"
                ),
                "operating_year": operating_year,
                "production_fraction": (
                    policy["production_ramp"][operating_year - 1]
                    if operating_year
                    else 0
                ),
                "revenue": row.get(
                    "revenue",
                    (
                        annual.get(operating_year, {}).get("sales_revenue")
                        if operating_year
                        else "0"
                    ),
                ),
                "stream_revenue": per_stream.get(operating_year, {}),
                **{
                    k: row.get(k)
                    for k in (
                        "fixed_opex",
                        "variable_opex",
                        "project_tax",
                        "capex",
                        "working_capital_change",
                        "fcff",
                        "fcfe",
                        "cumulative_project_cash",
                        "operating_cash_flow",
                        "depreciation",
                    )
                },
            }
        )
    stale = fin.get("result_is_stale", False) or fin.get("status") in (
        "stale",
        "data_required",
    )
    issues = list(fin.get("issues") or [])
    capital = stages.get("capex", {}).get("result") or {}
    if not ledger and capital.get("complete") is False:
        issues = list(dict.fromkeys([*(capital.get("issues") or []), *issues]))
    return {
        "id": state["id"],
        "revision": state["revision"],
        "filename": state["filename"],
        "running": state.get("running", False),
        "policy": policy,
        "streams": streams,
        "rows": rows,
        "currency": income.get("basis", {}).get("currency")
        or (stages.get("capex", {}).get("result") or {}).get("currency"),
        "financial_stale": fin.get("result_is_stale", False)
        or fin.get("status") in ("stale", "data_required"),
        "revenue_stale": rev.get("result_is_stale", False),
        "issues": issues,
        "has_financial_ledger": bool(ledger),
        "break_even": cash_break_even(result, stale=stale),
        "revenue_approved": bool(state.get("revenue_approval")),
    }
