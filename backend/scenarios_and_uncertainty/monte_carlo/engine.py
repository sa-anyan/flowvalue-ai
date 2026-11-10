"""Monte Carlo calls canonical TEA; no LLM, alternate DCF or imputed missing costs."""

from backend.equipment_costing.models import priced_record


import copy
import hashlib
import json
import math
from functools import lru_cache

import numpy as np
from scipy import stats

from backend.orchestration.pipeline import run

from .discovery import discover
from .models import Settings
from .sampling import sample
from .scenarios import apply, prepare


def number(value):
    try:
        n = float(value)
        return n if math.isfinite(n) else None
    except (ValueError, TypeError):
        return None


def evaluate(report, description, plan, confirmed_aliases):
    if plan.get("_monte_carlo_revenue_approved"):
        from backend.equipment_resolution.scope import expand
        from backend.revenue.authority import fingerprint

        expanded, _ = expand(report, plan)
        authority = plan["revenue_authority"]
        plan = {
            **plan,
            "revenue_authority": {
                **authority,
                "approval": {
                    "fingerprint": fingerprint(
                        plan["operating_economics"], authority["text"], expanded
                    )
                },
            },
        }
    result = run(report, description, plan, calculate_ranges=False)
    stages = result["stages"]
    equipment = (stages.get("equipment", {}).get("result") or {}).get("equipment", [])
    confirmed = set(confirmed_aliases)
    excluded = [
        r
        for r in equipment
        if r.get("parsed_source", {}).get("equipment_key") in confirmed
        or r.get("parsed_source", {}).get("confirmed_alias")
    ]
    counted = [r for r in equipment if r not in excluded]
    priced = [r for r in counted if priced_record(r)]
    costs = {
        r["equipment_tag"]: number(
            r.get("equipment_cost")
            if r.get("equipment_cost") is not None
            else r["amount"]
        )
        for r in priced
    }
    missing = [
        {
            "tag": r["equipment_tag"],
            "reason": "; ".join(r.get("issues", [])),
            "rationale": r.get("decision", {}).get("rationale", ""),
        }
        for r in counted
        if not priced_record(r)
    ]
    financial = stages.get("financial", {}).get("result") or {}
    metrics = dict(financial.get("metrics") or [])
    capex = stages.get("capex", {}).get("result") or {}
    opex = stages.get("opex", {}).get("result") or {}
    revenue = stages.get("revenue", {}).get("result") or {}
    year_one = next(
        (row for row in revenue.get("annual", []) if row.get("year") == 1), {}
    )
    vals = {
        "npv": number(metrics.get("project_npv", {}).get("value")),
        "irr": number(metrics.get("project_irr", {}).get("value")),
        "payback": number(metrics.get("project_discounted_payback", {}).get("value")),
        "capex": number(capex.get("total_capex")),
        "opex": number(opex.get("first_year_cash_opex")),
        "revenue": (
            number(year_one.get("sales_revenue")) if not revenue.get("issues") else None
        ),
        "known_opex": number(
            opex.get("known_cash_opex_subtotal", opex.get("first_year_cash_opex"))
        ),
    }
    finance_ready = (
        financial.get("status") == "calculated_preliminary" and vals["npv"] is not None
    )
    complete = finance_ready and not missing and len(counted) > 0
    cash = [
        {
            "year": r["period"]["year"],
            "fcff": number(r.get("fcff")),
            "revenue": number(r.get("revenue")),
            "capex": number(r.get("capex")),
            "known_cash_opex": number(r.get("known_cash_opex_subtotal")),
        }
        for r in financial.get("ledger", [])
    ]
    issues = [
        {
            "stage": key,
            "status": value.get("status"),
            "issues": list(
                dict.fromkeys(
                    [
                        *value.get("issues", []),
                        *((value.get("result") or {}).get("issues") or []),
                    ]
                )
            ),
        }
        for key, value in stages.items()
        if value.get("issues") or (value.get("result") or {}).get("issues")
    ]
    return {
        "status": "complete" if complete else "partial",
        "metrics": vals,
        "equipment_costs": costs,
        "equipment_cost_scopes": {
            r["equipment_tag"]: r.get("cost_scope") for r in priced
        },
        "equipment_installation_costs": {
            r["equipment_tag"]: number(r.get("installation_cost")) for r in priced
        },
        "capex_components": {
            r["id"]: number(r.get("amount")) for r in capex.get("lines", [])
        },
        "opex_components": {
            r["id"]: number(r.get("amount")) for r in opex.get("first_year_lines", [])
        },
        "equipment_models": {r["equipment_tag"]: r.get("curve_id") for r in equipment},
        "coverage": {
            "priced": len(priced),
            "total": len(counted),
            "confirmed_aliases": len(excluded),
            "fraction": len(priced) / len(counted) if counted else 0,
        },
        "unpriced": missing,
        "invalid_calculations": [
            {
                "tag": r["equipment_tag"],
                "issues": r.get("issues", []),
                "sizing_issue": r.get("parsed_source", {}).get("sizing_issue"),
            }
            for r in counted
            if r.get("curve_id")
            and not priced_record(r)
            and r.get("decision", {}).get("scope_decision") != "alias"
        ],
        "issues": issues,
        "cash_flow": cash,
        "metric_status": {k: v.get("status") for k, v in metrics.items()},
        "currency": capex.get("currency") or financial.get("currency"),
        "price_period": capex.get("period") or financial.get("financial_base_year"),
    }


def distribution(values):
    data = np.array(
        [v for v in values if v is not None and math.isfinite(v)], dtype=float
    )
    if not len(data):
        return {"count": 0, "p10": None, "p50": None, "p90": None, "histogram": []}
    if np.ptp(data) == 0:
        v = float(data[0])
        return {
            "count": len(data),
            "p10": v,
            "p50": v,
            "p90": v,
            "histogram": [{"low": v, "high": v, "count": len(data)}],
        }
    counts, edges = np.histogram(data, bins=min(30, max(1, int(np.sqrt(len(data))))))
    return {
        "count": len(data),
        "p10": float(np.quantile(data, 0.1)),
        "p50": float(np.quantile(data, 0.5)),
        "p90": float(np.quantile(data, 0.9)),
        "histogram": [
            {"low": float(edges[i]), "high": float(edges[i + 1]), "count": int(c)}
            for i, c in enumerate(counts)
        ],
    }


def summarize(rows, parameters, settings):
    good = [r for r in rows if r["status"] == "complete"]
    valid = [r for r in rows if r["status"] != "failed"]
    cost_valid = [r for r in valid if not r.get("invalid_calculations")]
    metrics = {
        name: distribution(
            [
                (r.get("metrics") or {}).get(name)
                for r in (good if name in {"npv", "irr", "payback"} else cost_valid)
            ]
        )
        for name in ("npv", "irr", "payback", "capex", "opex", "known_opex", "revenue")
    }
    tags = sorted({tag for r in valid for tag in r.get("equipment_costs", {})})
    equipment = {
        tag: distribution([r.get("equipment_costs", {}).get(tag) for r in valid])
        for tag in tags
    }
    cash_years = sorted({p["year"] for r in good for p in r["cash_flow"]})
    cash = [
        {
            "year": year,
            **{
                field: distribution(
                    [
                        p.get(field)
                        for r in good
                        for p in r["cash_flow"]
                        if p["year"] == year
                    ]
                )
                for field in ("fcff", "revenue", "capex")
            },
        }
        for year in cash_years
    ]
    npvs = [r["metrics"]["npv"] for r in good]
    irrs = [r["metrics"]["irr"] for r in good if r["metrics"]["irr"] is not None]
    drivers = []
    for p in parameters:
        for target in ("npv", "capex"):
            source = good if target == "npv" else cost_valid
            if p.kind == "configuration":
                grouped = {}
                for r in source:
                    outcome = r.get("metrics", {}).get(target)
                    if outcome is not None:
                        grouped.setdefault(str(r["samples"][p.id]), []).append(outcome)
                if len(grouped) > 1:
                    medians = {k: float(np.median(v)) for k, v in grouped.items()}
                    low = min(medians.values())
                    high = max(medians.values())
                    median = float(
                        np.median([v for values in grouped.values() for v in values])
                    )
                    drivers.append(
                        {
                            "parameter": p.id,
                            "label": p.label,
                            "metric": target,
                            "spearman": None,
                            "low_group_median": low,
                            "high_group_median": high,
                            "low_effect": low - median,
                            "high_effect": high - median,
                            "span": high - low,
                            "groups": [
                                {
                                    "configuration": k,
                                    "count": len(v),
                                    "median": medians[k],
                                }
                                for k, v in grouped.items()
                            ],
                            "basis": "Conditional medians by discrete configuration; no ordinal correlation or causal effect asserted",
                        }
                    )
                continue
            pairs = [
                (number(r["samples"].get(p.id)), r.get("metrics", {}).get(target))
                for r in source
            ]
            pairs = [(x, y) for x, y in pairs if x is not None and y is not None]
            if len(pairs) < 3:
                continue
            x, y = np.array(pairs).T
            if np.ptp(x) == 0 or np.ptp(y) == 0:
                continue
            rho = float(stats.spearmanr(x, y).statistic)
            lo, hi = np.quantile(x, [0.1, 0.9])
            low = float(np.median(y[x <= lo]))
            high = float(np.median(y[x >= hi]))
            drivers.append(
                {
                    "parameter": p.id,
                    "label": p.label,
                    "metric": target,
                    "spearman": rho,
                    "low_group_median": low,
                    "high_group_median": high,
                    "span": abs(high - low),
                    "median": float(np.median(y)),
                    "low_effect": low - float(np.median(y)),
                    "high_effect": high - float(np.median(y)),
                    "basis": "Sampled rank association and conditional extreme-decile medians, not causal one-at-a-time sensitivity; correlations can confound attribution",
                }
            )
    drivers.sort(key=lambda d: (d["metric"] != "npv", -d["span"]))
    representatives = []
    if good:
        for label, q in [("P10", 0.1), ("P50", 0.5), ("P90", 0.9)]:
            value = float(np.quantile(npvs, q))
            selected = min(good, key=lambda r: abs(r["metrics"]["npv"] - value))
            representatives.append(
                {
                    "label": label,
                    "run": selected["index"],
                    "npv": selected["metrics"]["npv"],
                }
            )
    elif valid:
        representatives = [
            {"label": "Partial example", "run": valid[len(valid) // 2]["index"]}
        ]
    return {
        "attempted": len(rows),
        "price_period": next(
            (r.get("price_period") for r in valid if r.get("price_period")), None
        ),
        "currency": next((r.get("currency") for r in valid if r.get("currency")), None),
        "payback_not_recovered_or_undefined": sum(
            r["metrics"]["payback"] is None for r in good
        ),
        "complete_runs": len(good),
        "partial_runs": sum(r["status"] == "partial" for r in rows),
        "excluded_from_aggregate_cost_distributions": len(valid) - len(cost_valid),
        "failed_runs": sum(r["status"] == "failed" for r in rows),
        "runs_with_invalid_calculations": sum(
            bool(r.get("invalid_calculations")) for r in rows
        ),
        "invalid_calculation_count": sum(
            len(r.get("invalid_calculations", [])) for r in rows
        ),
        "valid_run_rate": len(good) / len(rows) if rows else 0,
        "equipment_coverage": distribution([r["coverage"]["fraction"] for r in valid]),
        "metrics": metrics,
        "equipment": equipment,
        "cash_flow": cash,
        "probability_negative_npv": (
            sum(n < 0 for n in npvs) / len(npvs) if npvs else None
        ),
        "probability_below_target_irr": (
            sum(v < settings.target_irr for v in irrs) / len(irrs) if irrs else None
        ),
        "irr_probability_denominator": len(irrs),
        "undefined_irr_runs": len(good) - len(irrs),
        "drivers": drivers,
        "representative_runs": representatives,
        "percentile_convention": "P10/P50/P90 are ascending numeric quantiles (10th/50th/90th). Lower cost is favourable; lower NPV is unfavourable. Not exceedance percentiles.",
        "correlation_convention": "Gaussian-copula latent-normal correlation, not a guaranteed physical Pearson correlation. Shared targets use the same draw.",
        "complete_run_definition": "All non-alias registered items priced and canonical financial model calculated; not proof of an exhaustive plant register or validated engineering design.",
        "scope_notice": "NPV/IRR/payback risk uses complete-scope financial runs only. CAPEX/known OPEX and equipment distributions may describe a partial plant; inspect cost coverage and per-metric counts.",
    }


def simulate(state, settings, progress=lambda *args: None):
    discovery = discover(state)
    original = Settings.model_validate(discovery["settings"])
    parameters, draws = sample(settings, original)
    plan = prepare(state, settings)
    report = (
        state.get("scoped_report")
        or state.get("effective_report")
        or state["parsed"]["report"]
    )
    aliases = [a.equipment_key for a in settings.aliases]
    rows = []
    exception_register = {}

    # Reuse repeated discrete/fixed scenarios, bounded to avoid unbounded audit caches.
    @lru_cache(maxsize=64)
    def cached(payload):
        return evaluate(report, state["description"], json.loads(payload), aliases)

    for index in range(settings.iterations):
        try:
            apply(plan, parameters, draws[index])
            payload = json.dumps(
                plan, sort_keys=True, allow_nan=False, separators=(",", ":")
            )
            outcome = copy.deepcopy(cached(payload))
            outcome.update(
                index=index,
                samples={
                    p.id: (v.item() if hasattr(v, "item") else v)
                    for p, v in zip(parameters, draws[index])
                },
            )
        except (
            ValueError,
            TypeError,
            KeyError,
            ArithmeticError,
            AttributeError,
        ) as exc:
            outcome = {
                "index": index,
                "status": "failed",
                "reason": str(exc)[:1000],
                "samples": {p.id: str(v) for p, v in zip(parameters, draws[index])},
            }
        compact_exceptions = []
        for issue in outcome.get("unpriced", []):
            code = hashlib.sha256(
                json.dumps(issue, sort_keys=True).encode()
            ).hexdigest()[:20]
            exception_register.setdefault(code, issue)
            compact_exceptions.append({"tag": issue["tag"], "exception_id": code})
        if compact_exceptions:
            outcome["unpriced"] = compact_exceptions
        rows.append(outcome)
        if (index % 25 == 0 or index == settings.iterations - 1) and progress(
            index + 1, settings.iterations
        ) is False:
            break
    from backend.equipment_costing.registry import list_equipment_models

    selected = {r.get("curve_id") for r in state["plan"].get("equipment", [])}
    selected.update(
        v for p in parameters if p.kind == "configuration" for v in p.choices
    )
    sources = [
        {
            k: m[k]
            for k in (
                "id",
                "equipment",
                "configuration",
                "printed_page",
                "pdf_page",
                "size_unit",
                "formula_note",
                "review_status",
                "caveats",
            )
            if k in m
        }
        for m in list_equipment_models()
        if m["id"] in selected
    ]
    return {
        "summary": summarize(rows, parameters, settings),
        "runs": rows,
        "settings": settings.model_dump(),
        "input_hash": hashlib.sha256(
            json.dumps(
                [
                    report,
                    state["description"],
                    prepare(state, settings),
                    settings.model_dump(),
                ],
                sort_keys=True,
            ).encode()
        ).hexdigest(),
        "baseline_revision": state["revision"],
        "baseline_id": state["id"],
        "baseline_plan": copy.deepcopy(state["plan"]),
        "effective_fixed_plan": prepare(state, settings),
        "audit": {
            "sampling": "NumPy PCG64 + SciPy inverse CDF Gaussian copula",
            "numpy_version": np.__version__,
            "scipy_version": __import__("scipy").__version__,
            "exception_register": exception_register,
            "costing_cache": "Canonical Garrett curve-fit cache plus up to 64 repeated complete scenarios",
            "llm_calls_per_iteration": 0,
            "operating_years": settings.operating_years,
            "baseline_operating_years": state["plan"]
            .get("operating_economics", {})
            .get("financial", {})
            .get("operating_years"),
            "parameter_sources": [p.model_dump() for p in parameters],
            "baseline_unchanged": True,
            "source_workbook_filename": report.get("filename", state.get("filename")),
            "source_workbook_sha256": report.get("sha256"),
            "source_report_hash": hashlib.sha256(
                json.dumps(report, sort_keys=True).encode()
            ).hexdigest(),
            "catalogue_sources": sources,
            "scope_convention": "Coverage counts register records, not capital-dollar completeness. Saved AB quantities are included in their costed record.",
            "uncertainty_limit": "Distributions cover selected engineering/economic assumptions. Systematic model bias and unverified graph-digitisation errors are not statistically calibrated.",
            "exceptions": discovery["exceptions"],
        },
    }
