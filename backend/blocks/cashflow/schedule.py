"""User-owned project calendar and revenue-realization scenarios; no cashflow engine."""

import copy
from decimal import Decimal
from datetime import datetime, timezone
from backend.opex.consumption import decimal


def make_policy(horizon, build, previous=None):
    if type(horizon) is not int or type(build) is not int:
        raise ValueError("Project and construction years must be integers")
    previous = previous or {}
    count = horizon - build
    old = previous.get("production_ramp") or [0.2, 0.4, 0.6, 0.8]
    # New studies use an explicit staged planning example. Existing policies
    # without cost timing keep legacy financial weights until the user edits them.
    initial_timing = (
        {}
        if previous
        else {
            "capital_spend_fractions": (
                {"1": 0.3, "2": 0.5, "3": 0.2}
                if build == 2
                else {
                    str(i + 1 if build else 0): 1 / max(1, build)
                    for i in range(max(1, build))
                }
            ),
            "startup_spend_fractions": {str(build + 1): 1},
            "working_capital_funding_year": build + 1,
        }
    )
    return validate(
        {
            **initial_timing,
            "analysis_years": horizon,
            "construction_years": build,
            "production_ramp": [
                old[min(i, len(old) - 1)] for i in range(max(0, count))
            ],
            **{
                k: copy.deepcopy(previous[k])
                for k in (
                    "capital_spend_fractions",
                    "startup_spend_fractions",
                    "working_capital_funding_year",
                    "fixed_opex_factors",
                )
                if k in previous
            },
            "revenue_factors": {
                y: v
                for y, v in previous.get("revenue_factors", {}).items()
                if build < int(y) <= horizon
            },
            "rationale": previous.get("rationale")
            or "FlowValue editable planning example: fixed capital 30/50/20 across project years 1–3 when two pre-operation construction years are selected; start-up capital and working capital at first operation. Other construction durations use equal capital shares. These percentages are not prescribed by Garrett. Production: 20%, 40%, 60%, then 80% throughput utilization during scheduled operating hours. Annual steps are not published Garrett factors. Garrett pp.45,76,104 discusses downtime, gradual market uptake and historical utilization near 80%; operating hours remain a separate assumption.",
        },
        {
            "sales": [
                {"id": k.split(":", 1)[1]}
                for v in previous.get("revenue_factors", {}).values()
                for k in v
                if k.startswith("product:")
            ],
            "commercial_lines": [
                {"id": k.split(":", 1)[1]}
                for v in previous.get("revenue_factors", {}).values()
                for k in v
                if k.startswith("commercial:")
            ],
        },
    )


def validate(policy, config=None):
    policy = copy.deepcopy(policy)
    horizon = policy["analysis_years"]
    build = policy["construction_years"]
    if (
        type(horizon) is not int
        or type(build) is not int
        or not 1 <= horizon <= 60
        or not 0 <= build <= 10
        or not 1 <= horizon - build <= 50
    ):
        raise ValueError(
            "Use 1–60 project years, 0–10 construction years and 1–50 operating years"
        )
    ramp = policy["production_ramp"]
    if not isinstance(ramp, list) or len(ramp) != horizon - build:
        raise ValueError("Supply one production fraction for every operating year")
    policy["production_ramp"] = [float(decimal(v, maximum=1)) for v in ramp]
    factors = policy.setdefault("revenue_factors", {})
    if not isinstance(factors, dict):
        raise ValueError("Revenue factors must be a year/stream map")
    allowed = {
        prefix + str(r["id"])
        for group, prefix in [
            ("sales", "product:"),
            ("commercial_lines", "commercial:"),
        ]
        for r in (config or {}).get(group, [])
    }
    for year, streams in factors.items():
        if (
            not str(year).isdigit()
            or not build < int(year) <= horizon
            or not isinstance(streams, dict)
        ):
            raise ValueError("Revenue overrides must refer to operating project years")
        for key, value in streams.items():
            if key not in allowed:
                raise ValueError(
                    "Select an existing revenue stream; do not add income through the schedule"
                )
            streams[key] = float(decimal(value, maximum=1))
    for name in ("capital_spend_fractions", "startup_spend_fractions"):
        if name not in policy:
            continue  # Legacy schedules retain their saved capital timing.
        shares = policy[name]
        if not isinstance(shares, dict) or not shares:
            raise ValueError(name + " requires project-year percentages totaling 100%")
        for year, share in shares.items():
            if not str(year).isdigit() or str(year) != str(int(year)):
                raise ValueError("Use canonical integer project-year keys")
            if not 0 <= int(year) <= horizon:
                raise ValueError("Capital spending falls outside the project calendar")
            shares[year] = float(decimal(share, maximum=1))
        if abs(
            sum((Decimal(str(v)) for v in shares.values()), Decimal(0)) - 1
        ) > Decimal("1e-12"):
            raise ValueError(name + " must total 100%; no silent normalization")
    if "working_capital_funding_year" in policy:
        year = policy["working_capital_funding_year"]
        if type(year) is not int or not 0 <= year <= build + 1:
            raise ValueError(
                "Fund working capital no later than the first operating year"
            )
    if not isinstance(policy.setdefault("fixed_opex_factors", {}), dict):
        raise ValueError("Fixed OPEX factors must be a project-year map")
    for year, value in policy["fixed_opex_factors"].items():
        if not str(year).isdigit() or not build < int(year) <= horizon:
            raise ValueError("Fixed OPEX factors must refer to operating project years")
        policy["fixed_opex_factors"][year] = float(decimal(value, maximum=1))
    if not str(policy.get("rationale", "")).strip():
        raise ValueError("Record the schedule basis")
    return policy


def factor(config, kind, identity, operating_year):
    policy = config.get("cashflow_schedule") or {}
    project_year = int(operating_year) + int(
        config.get("financial", {}).get("construction_years", 0)
    )
    return decimal(
        policy.get("revenue_factors", {})
        .get(str(project_year), {})
        .get(kind + ":" + str(identity), 1),
        maximum=1,
    )


def apply_policy(config, policy):
    if not policy:
        return copy.deepcopy(config)
    result = copy.deepcopy(config)
    policy = validate(policy, result)
    life = policy["analysis_years"] - policy["construction_years"]
    build = policy["construction_years"]
    fin = result.setdefault("financial", {})
    old_build = fin.get("construction_years")
    fin.update(
        operating_years=life,
        construction_years=build,
        production_ramp=policy["production_ramp"],
    )
    if old_build != build or len(fin.get("construction_spend_fractions", [])) != max(
        1, build
    ):
        fin["construction_spend_fractions"] = [1 / max(1, build)] * max(1, build)
    # Horizon changes repeat last saved commercial terms as an explicit planning
    # assumption. The prior complete model remains in the named version history.
    for group in ("commercial_lines", "avoided_costs"):
        for item in result.get(group, []):
            original = item.get("years", [])
            if not original:
                continue
            by_year = {int(r["year"]): r for r in original}
            last_year = max(by_year)
            if any(y not in by_year for y in range(1, min(life, last_year) + 1)):
                raise ValueError(
                    "Resolve missing commercial years before extending the schedule"
                )
            item["years"] = [
                dict(copy.deepcopy(by_year.get(y, by_year[last_year])), year=y)
                for y in range(1, life + 1)
            ]
            if life > len(original):
                item["schedule_extension_basis"] = (
                    "User-selected horizon; last saved annual terms repeated as provisional planning assumptions, not a new contract"
                )
    result["cashflow_schedule"] = policy
    return result


def save(store, key, revision, policy, *, approve_revenue=False):
    from backend.blocks.execution import refresh, view
    from backend.revenue.authority import questions, fingerprint
    from backend.blocks.revenue.input_builder import _revenue_project
    from backend.blocks.shared import operating_schedule
    from backend.opex.models import Basis
    from backend.revenue import calculate_revenue

    state = store.get(key)
    if state["revision"] != revision or state.get("running"):
        raise ValueError("Reload the current revision after the calculation finishes")
    config = state["plan"].get("operating_economics", {})
    policy = validate(policy, config)
    revised = apply_policy(config, policy)
    revised.pop("_revenue_authority", None)
    report = (
        state.get("stage_outputs", {}).get("engineering_data", {}).get("report", {})
    )
    approval = None
    if approve_revenue:
        missing = questions(
            revised,
            state.get("revenue_description", ""),
            report,
            require_approval=False,
        )
        if missing:
            raise ValueError(" ".join(missing))
        hours, ramp = operating_schedule(revised)
        checked = calculate_revenue(
            _revenue_project(
                report,
                state.get("revenue_description", ""),
                revised,
                Basis(**revised["price_basis"]),
                hours,
                ramp,
                {},
            ),
            engineering_scenario=True,
        )
        if checked.issues:
            raise ValueError(" ".join(checked.issues))
        approval = {
            "fingerprint": fingerprint(
                revised, state.get("revenue_description", ""), report
            ),
            "approved_at": datetime.now(timezone.utc).isoformat(),
            "origin": "explicit_user_cashflow_schedule_approval",
        }
    store.version(key, "Before cashflow schedule change")
    state["analysis_schedule"] = policy
    state["plan"]["operating_economics"] = revised
    if approval:
        state["revenue_approval"] = approval
    else:
        state.pop("revenue_approval", None)
    state.setdefault("cashflow_schedule_edits", []).append(
        {
            "revision": revision,
            "policy": policy,
            "source": "Explicit user schedule input",
        }
    )
    from backend.revenue.authority import bind

    bind(state)
    refresh(state)
    return view(store.put(state, revision))
