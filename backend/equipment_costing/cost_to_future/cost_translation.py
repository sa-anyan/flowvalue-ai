"""Source-aware price-period translation, independent of costing methodology.

No web or LLM calls in arithmetic. Native same-series indices take priority;
a currency-specific consumer-inflation proxy requires explicit policy consent.
"""

import copy
import json
import re
from dataclasses import asdict, dataclass, replace
from decimal import Decimal, InvalidOperation, localcontext
from pathlib import Path

DEFAULT_POLICY = {
    "target_period": "2026-09",
    "allow_general_inflation_proxy": True,
    # Plant-capital index for equipment estimates only (never operating prices
    # or working capital). Used once the catalogue holds a target-period value;
    # until then equipment falls back to the CPI proxy.
    "equipment_index_series": "CEPCI",
}


def catalogue():
    return json.loads(Path(__file__).with_name("index_catalogue.json").read_text(encoding="utf-8"))


def numeric(value, *, positive=False):
    if isinstance(value, bool):
        raise TypeError("Boolean is not a monetary/index value")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError("Finite numeric monetary/index value required") from exc
    if not result.is_finite() or result < 0 or (positive and result == 0):
        raise ValueError("Money must be nonnegative and index values positive")
    return result


def indexed_amount(amount, *, base_index, target_index):
    """Canonical same-series numerical primitive; callers establish applicability."""
    with localcontext() as context:
        context.prec = 40
        return (
            numeric(amount)
            * numeric(target_index, positive=True)
            / numeric(base_index, positive=True)
        )


def price_years(period):
    return list(dict.fromkeys(re.findall(r"(?<!\d)\d{4}(?!\d)", str(period))))


def year(period):
    matches = price_years(period)
    if len(matches) != 1 or int(matches[0]) == 0:
        raise ValueError("A single explicit source price year is required")
    return matches[0]


@dataclass(frozen=True)
class Translation:
    original_amount: Decimal
    amount: Decimal
    currency: str
    source_period: str
    target_period: str
    source_series: str
    source_index: Decimal | None
    applied_series: str
    base_observation: dict
    target_observation: dict
    multiplier: Decimal
    status: str
    method_id: str
    notice: str


class MissingIndexObservation(ValueError):
    """The requested price conversion has no matching index observation."""


def _equipment_index_points(policy, series, currency, source_period, source_year, target):
    """Base and target observations of the policy's equipment index, or None.

    Used only when the policy names an equipment cost index series, the series
    is in the estimate's currency, and it holds both the source year and the
    target period. Otherwise the caller falls back to its existing rules.
    """
    name = policy.get("equipment_index_series")
    selected = series.get(name) if name else None
    if not selected or selected.get("currency") != currency:
        return None
    observations = selected.get("observations", {})
    base = observations.get(source_period) or observations.get(source_year)
    target_point = observations.get(target)
    return (base, target_point) if base and target_point else None


def translate_cost(
    amount,
    *,
    currency,
    source_period,
    source_series="",
    source_index=None,
    method_id="",
    policy=None,
    indices=None,
    equipment=False,
):
    """Translate a dated price. ``equipment=True`` allows the policy's equipment
    cost index (e.g. CEPCI); other prices never use it."""
    policy = DEFAULT_POLICY if policy is None else policy
    indices = catalogue() if indices is None else indices
    original = numeric(amount)
    target = policy["target_period"]
    year(target)
    source_year = year(source_period)
    index = numeric(source_index, positive=True) if source_index is not None else None
    if not isinstance(currency, str) or not re.fullmatch(r"[A-Z]{3}", currency):
        raise ValueError("Explicit three-letter currency required")
    if source_year == year(target):
        return Translation(
            original,
            original,
            currency,
            source_period,
            source_period,
            source_series,
            index,
            source_series,
            {},
            {},
            Decimal(1),
            "already_target_year",
            method_id,
            "Already in target year; no within-year escalation or relabelling applied",
        )
    override = (
        policy.get("source_index_overrides", {}).get(method_id, {}).get(source_year)
    )
    if override is not None:
        if (
            not isinstance(override, dict)
            or not override.get("source")
            or not override.get("series")
        ):
            raise ValueError(
                "Source-index override requires series, value and source provenance"
            )
        source_series = override["series"]
        index = numeric(override.get("value"), positive=True)
    series = indices["series"]
    native = series.get(source_series, {})
    target_point = native.get("observations", {}).get(target)
    if target_point and index is not None:
        selected_series, selected, base = (
            source_series,
            native,
            {
                "value": str(index),
                "source": (
                    override["source"]
                    if override
                    else "Explicit index retained by source cost calculation"
                ),
                "period": source_period,
            },
        )
    elif equipment and _equipment_index_points(
        policy, series, currency, source_period, source_year, target
    ):
        # Opt-in equipment cost index (e.g. CEPCI) for sources without a native index.
        selected_series = policy["equipment_index_series"]
        selected = series[selected_series]
        base, target_point = _equipment_index_points(
            policy, series, currency, source_period, source_year, target
        )
    else:
        if policy.get("allow_general_inflation_proxy") is not True:
            raise ValueError(
                "Target native index unavailable; general-inflation proxy not authorised"
            )
        selected_series = indices.get("currency_proxy_series", {}).get(currency)
        if not selected_series:
            raise ValueError(
                "No currency-specific proxy registered for " + str(currency)
            )
        selected = series[selected_series]
        observations = selected["observations"]
        base = observations.get(source_period) or observations.get(source_year)
        target_point = observations.get(target)
        if not base or not target_point:
            raise MissingIndexObservation(
                f"Missing {selected_series} observation for {source_period} or {target}"
            )
    if selected.get("currency") != currency:
        raise ValueError("Index currency mismatch; inflation is not an FX conversion")
    for point in (base, target_point):
        if not isinstance(point.get("source"), str) or not point["source"].strip():
            raise ValueError("Every index observation needs a source")
    proxy = selected.get("kind") == "general_inflation_proxy"
    if proxy:
        status = "general_inflation_proxy"
        notice = "Consumer purchasing-power proxy, not CEPCI or a vendor quotation; annual source average may approximate a year-only/early-year cost basis. Monthly target is not a full-year average."
    elif selected_series != source_series:
        status = "equipment_index_ratio"
        notice = (
            f"Equipment cost index {selected_series} (policy opt-in): source-year "
            f"annual average to target {target}; the source did not state its own index value"
        )
    else:
        status = "same_series_index_ratio"
        notice = "Source and target use the same named index series; currency unchanged"
    with localcontext() as context:
        context.prec = 40
        multiplier = numeric(target_point["value"], positive=True) / numeric(
            base["value"], positive=True
        )
        adjusted = indexed_amount(
            original, base_index=base["value"], target_index=target_point["value"]
        )
    return Translation(
        original,
        adjusted,
        currency,
        source_period,
        target,
        source_series,
        index,
        selected_series,
        copy.deepcopy(base),
        copy.deepcopy(target_point),
        multiplier,
        status,
        method_id,
        notice,
    )


def translate_calculation(calculation, *, method_id, policy, indices=None):
    if not policy or policy.get("enabled") is False or calculation.estimate is None:
        return calculation
    estimate = calculation.estimate
    translated = translate_cost(
        estimate.amount,
        currency=estimate.currency,
        source_period=estimate.period,
        source_series=estimate.index_series,
        source_index=estimate.cost_index,
        method_id=method_id,
        policy=policy,
        indices=indices,
        equipment=True,
    )
    audit = asdict(translated)
    if translated.status == "already_target_year":
        if calculation.evidence.get("cost_translation"):
            return calculation
        return replace(
            calculation,
            evidence={**copy.deepcopy(calculation.evidence), "cost_translation": audit},
        )
    factor = translated.multiplier

    def scale(value):
        if value is None:
            return None
        result = float(numeric(value) * factor)
        numeric(result)
        return result

    installation = calculation.installation
    if installation:
        installation = replace(
            installation,
            equipment_cost=scale(installation.equipment_cost),
            installation_cost=scale(installation.installation_cost),
            equipment_and_installation_cost=scale(
                installation.equipment_and_installation_cost
            ),
            evidence={
                **copy.deepcopy(installation.evidence),
                "cost_translation": audit,
            },
        )
    target_index = numeric(translated.target_observation["value"], positive=True)
    return replace(
        calculation,
        estimate=replace(
            estimate,
            amount=float(translated.amount),
            period=translated.target_period,
            cost_index=float(target_index),
            index_series=translated.applied_series,
            notes=estimate.notes + (translated.notice,),
        ),
        installation=installation,
        evidence={**copy.deepcopy(calculation.evidence), "cost_translation": audit},
        index_adjustment={
            "previous_adjustment": copy.deepcopy(calculation.index_adjustment),
            **audit,
        },
        issues=calculation.issues + (translated.notice,),
        status=(
            "provisional"
            if translated.status == "general_inflation_proxy"
            else calculation.status
        ),
    )


def aggregation_basis(calculation):
    """One dated currency numeraire; actual inflation indices remain in each audit.

    Value 1 labels a normalized monetary basis, NOT a published inflation index.
    Different escalation methods can therefore feed one same-period USD total.
    """
    estimate = calculation.estimate
    audit = calculation.evidence.get("cost_translation")
    if audit and audit.get("target_period") == estimate.period:
        return (
            estimate.currency,
            1.0,
            estimate.period,
            "PRICE_BASIS:" + estimate.currency + ":" + estimate.period,
        )
    return (
        estimate.currency,
        estimate.cost_index,
        estimate.period,
        estimate.index_series,
    )
