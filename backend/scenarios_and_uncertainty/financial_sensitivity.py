"""Independent financial previews from the last calculated immutable inputs.

No upstream stage runs, AI calls, baseline edits or new financial arithmetic.
Each result retains its exact CAPEX/OPEX/revenue snapshots and is saved as a
separate version through the existing owner-scoped persistence interface.
"""

import copy
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from backend.financial_modelling import calculate_financials, restore_inputs, snapshot_id
from backend.financial_modelling.connectors.playground.interface import recalculate_scenario
from backend.orchestration.codec import plain

FIELDS = {"discount_rate", "tax_rate", "depreciation_years", "salvage_fraction",
          "working_capital_recovery_fraction", "closure_allowance"}


def original(state):
    result = (((state.get("results") or {}).get("stages") or {}).get("financial") or {}).get("result") or {}
    if not result.get("assumptions_json") or not result.get("ledger"):
        raise ValueError("Calculate a financial baseline once before using sensitivity.")
    return restore_inputs(result["assumptions_json"])


def uniform(values):
    values = set(values)
    return str(next(iter(values))) if len(values) == 1 else None


def policy(inputs):
    a = inputs.assumptions
    assets = [c for c in inputs.capital if c.depreciation.depreciable_fraction.value > 0 and c.amount.amount]
    return {"discount_rate": str(a.project_discount_rate.value),
            "tax_rate": uniform(rate.value for _, rate in a.tax.annual_rates),
            "depreciation_years": uniform(c.depreciation.life for c in assets),
            "salvage_fraction": uniform(c.disposal_proceeds.amount / (c.amount.amount * c.depreciation.depreciable_fraction.value) for c in assets),
            "working_capital_recovery_fraction": str(a.working_capital.recovery_fraction.value),
            "closure_allowance": str(a.closure_cost.amount)}


def baseline(state):
    inputs = original(state)
    return {"baseline_snapshot_id": snapshot_id(inputs), "policy": policy(inputs),
            "result": plain(calculate_financials(inputs))}


def preview(state, overrides, expected_snapshot_id):
    inputs = original(state)
    if snapshot_id(inputs) != expected_snapshot_id:
        raise ValueError("The financial baseline changed. Reset to original and try again.")
    if set(overrides) - FIELDS:
        raise ValueError("Unsupported sensitivity variable")
    values = {}
    for key, raw in overrides.items():
        if isinstance(raw, bool) or not isinstance(raw, (int, float, str, Decimal)):
            raise ValueError(key + " must be a finite number")
        try:
            value = Decimal(str(raw))
        except InvalidOperation as exc:
            raise ValueError(key + " must be a finite number") from exc
        if not value.is_finite() or value < 0:
            raise ValueError(key + " must be a finite nonnegative number")
        if key not in {"depreciation_years", "closure_allowance"} and value > 1:
            raise ValueError(key + " must be between 0 and 1")
        if key == "depreciation_years" and (value != int(value) or not 1 <= value <= 50):
            raise ValueError("Depreciation life must be an integer from 1 to 50")
        values[key] = value

    def assumption(old, value):
        return replace(old, value=value, status="user_assumption",
                       rationale="Independent financial sensitivity override", source="User scenario; original baseline unchanged")

    a = inputs.assumptions
    if "discount_rate" in values:
        a = replace(a, **{k: assumption(getattr(a, k), values["discount_rate"]) for k in
                         ("project_discount_rate", "equity_discount_rate", "mirr_finance_rate", "mirr_reinvestment_rate")})
    if "tax_rate" in values:
        a = replace(a, tax=replace(a.tax, annual_rates=tuple((year, assumption(rate, values["tax_rate"])) for year, rate in a.tax.annual_rates)))
    if "working_capital_recovery_fraction" in values:
        a = replace(a, working_capital=replace(a.working_capital, recovery_fraction=assumption(a.working_capital.recovery_fraction, values["working_capital_recovery_fraction"])))
    if "closure_allowance" in values:
        a = replace(a, closure_cost=replace(a.closure_cost, amount=values["closure_allowance"], source="User sensitivity closure allowance, same saved currency/year"))
    capital = []
    for item in inputs.capital:
        dep = item.depreciation
        if dep.depreciable_fraction.value > 0:
            if "depreciation_years" in values:
                dep = replace(dep, life=int(values["depreciation_years"]))
            if "salvage_fraction" in values:
                salvage = item.amount.amount * dep.depreciable_fraction.value * values["salvage_fraction"]
                dep = replace(dep, residual_basis=replace(dep.residual_basis, amount=salvage))
                item = replace(item, disposal_proceeds=replace(item.disposal_proceeds, amount=salvage))
        capital.append(replace(item, depreciation=dep))
    scenario, result = recalculate_scenario(inputs, actor="user", reason="Independent financial sensitivity",
                                          expected_snapshot_id=expected_snapshot_id, assumptions=a, capital=tuple(capital))
    if result.issues:
        raise ValueError("Scenario could not calculate: " + "; ".join(result.issues))
    return scenario, result


def save(store, key, overrides, expected_snapshot_id, name=""):
    state = store.get(key)
    inputs, result = preview(state, overrides, expected_snapshot_id)
    snapshot = copy.deepcopy(state)
    snapshot.update(running=False, status="Independent financial sensitivity")
    snapshot["financial_sensitivity"] = {"baseline_id": key, "baseline_snapshot_id": expected_snapshot_id,
                                         "overrides": overrides, "upstream_snapshots_json": inputs.upstream_snapshots_json}
    snapshot.setdefault("results", {}).setdefault("stages", {})["financial"] = {
        "status": result.status, "result": plain(result), "issues": list(result.issues)}
    snapshot.setdefault("stage_outputs", {})["financial"] = {"financial_inputs": plain(inputs)}
    snapshot["results"]["financial_inputs"] = plain(inputs)
    snapshot.setdefault("plan", {}).setdefault("operating_economics", {}).setdefault("financial", {}).update(
        {k: (int(v) if k == "depreciation_years" else float(v)) for k, v in policy(inputs).items() if v is not None})
    version = store.version(key, name.strip() or "Sensitivity " + datetime.now(timezone.utc).isoformat(timespec="seconds"), snapshot=snapshot)
    return {"version_id": version, "baseline_snapshot_id": expected_snapshot_id,
            "policy": policy(inputs), "overrides": overrides, "result": plain(result)}
