"""Route explicitly mapped parsed equipment through the canonical registry.

No tag-based guessing, sizing, unit conversion or silent missing-item exclusion.
This totals equipment costs, not whole-plant CAPEX.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from math import fsum, isfinite

from .. import registry
from ..cost_to_future.cost_translation import aggregation_basis
from ..indexes.garrett.integrated import CostingResult
from ..models import positive, is_scoped_capital
from ..unit_conversion import ConversionResult, convert

# Unit-price scopes require a physical quantity, not an equipment count.
UNIT_SCOPES = {
    "unit_price_per_ft": ("ft", "purchased_equipment"),
    "installed_unit_price_per_tray": ("tray", "installed_equipment"),
    "duct_unit_price_per_ft": ("ft", "purchased_equipment"),
    "unit_price_per_ft3": ("ft3", "purchased_equipment"),
    "packing_unit_price_per_ft3": ("ft3", "purchased_equipment"),
    "unit_price_per_ft2": ("ft2", "purchased_equipment"),
    "unit_price_per_ft_height": ("ft_height", "purchased_equipment"),
    "unit_price_per_tray": ("tray", "purchased_equipment"),
    "installed_unit_price_per_ft": ("ft", "installed_equipment"),
    "installed_pipeline_unit_price_per_ft": ("ft", "installed_equipment"),
    "installed_unit_price_per_ft2": ("ft2", "installed_equipment"),
    "pipe_unit_price_per_ft": ("ft", "pipe_total_cost"),
}


@dataclass(frozen=True)
class EquipmentCostLine:
    equipment_tag: str
    curve_id: str | None
    status: str
    amount: float | None
    quantity: float | None
    quantity_unit: str | None
    cost_scope: str | None
    calculation: CostingResult | None
    issues: tuple[str, ...]
    parsed_source: object = None
    equipment_cost: float | None = None
    installation_cost: float | None = None
    equipment_and_installation_cost: float | None = None
    quantity_conversion: ConversionResult | None = None


@dataclass(frozen=True)
class CostSubtotal:
    currency: str
    cost_index: float
    period: str
    cost_scope: str
    amount: float
    equipment_tags: tuple[str, ...]
    index_series: str = "CEPCI"


@dataclass(frozen=True)
class EquipmentInstallationSubtotal:
    currency: str
    cost_index: float
    period: str
    equipment_cost: float | None
    installation_cost: float | None
    equipment_and_installation_cost: float | None
    equipment_tags: tuple[str, ...]
    missing_equipment_tags: tuple[str, ...]
    missing_installation_tags: tuple[str, ...]
    missing_combined_tags: tuple[str, ...]
    index_series: str = "CEPCI"


def _complete_sum(lines, attribute):
    if not lines or any(getattr(line, attribute) is None for line in lines):
        return None
    return fsum(getattr(line, attribute) for line in lines)


@dataclass(frozen=True)
class EquipmentCostTotal:
    status: str
    total: float | None
    subtotals: tuple[CostSubtotal, ...]
    equipment: tuple[EquipmentCostLine, ...]
    issues: tuple[str, ...]
    equipment_cost_total: float | None = None
    installation_cost_total: float | None = None
    equipment_and_installation_cost_total: float | None = None
    component_subtotals: tuple[EquipmentInstallationSubtotal, ...] = ()
    cost_breakdown_status: str = "needs_review"
    installation_issues: tuple[str, ...] = ()


def calculate_total_cost(equipment, *, translation_policy=None, indices=None):
    """Accept an iterable of parsed/mapped equipment dictionaries.

    Required per item: equipment_tag, curve_id, size, size_unit.
    Optional: source ('garrett'), quantity/quantity_unit, costing_options,
    parsed_source (parser cell/stream evidence). Material/pressure/configuration
    choices belong to the selected curve and scoped registry factors.
    Unresolved items preserve partial subtotals but suppress the complete total.
    """
    items = list(equipment)
    if translation_policy and indices is None:
        from ..cost_to_future.cost_translation import catalogue

        indices = catalogue()
    tags = set()
    for item in items:
        if not isinstance(item, Mapping):
            raise TypeError("Each equipment item must be a mapping")
        tag = item.get("equipment_tag")
        if not isinstance(tag, str) or not tag.strip():
            raise ValueError("Every equipment item needs a nonempty equipment_tag")
        canonical_tag = tag.strip().casefold()
        if canonical_tag in tags:
            raise ValueError("Duplicate equipment tag would double-count cost: " + tag)
        tags.add(canonical_tag)
    lines = []
    groups = {}
    for item in items:
        calculation = None
        quantity = None
        quantity_unit = None
        scope = None
        quantity_conversion = None
        try:
            if item.get("manual_price"):
                from ..manual import manual_result

                calculation = manual_result(item["manual_price"])
                options = {}
            elif item.get("external_quote"):
                from ..quotes import quote_result

                calculation = quote_result(
                    item["external_quote"], item["size"], item["size_unit"]
                )
                options = {}
            else:
                if not item.get("curve_id"):
                    raise ValueError(
                        "Exact equipment configuration/curve mapping is missing"
                    )
                if item.get("size") is None:
                    raise ValueError(
                        "Sizing input missing: choose a supported conversion or supply the model design coordinate"
                    )
                options = item.get("costing_options", {})
                if not isinstance(options, Mapping):
                    raise TypeError("costing_options must be a mapping")
                estimator = registry.estimate_cost
                if item.get("separate_scope_conflicts") is True:
                    from ..component_scope import estimate_component

                    estimator = estimate_component
                calculation = estimator(
                    item.get("curve_id")
                    or ("manual:user-price" if item.get("manual_price") else None),
                    item["size"],
                    size_unit=item["size_unit"],
                    source=item.get("source", "garrett"),
                    **options,
                )
            if calculation.estimate is None:
                raise ValueError("; ".join(calculation.issues))
            from ..cost_to_future.cost_translation import translate_calculation

            calculation = translate_calculation(
                calculation,
                method_id=item.get("source", "garrett"),
                policy=translation_policy,
                indices=indices,
            )
            if item.get("source") == "nottingham":
                # Convert dated GBP estimates to the study USD basis only after inflation translation.
                # Pinned FX provenance is preserved in calculation.evidence.
                from ..manual import convert_calculation

                calculation = convert_calculation(
                    calculation, item.get("calculation_currency", "USD")
                )
            if item.get("manual_price"):
                from ..manual import convert_calculation

                calculation = convert_calculation(
                    calculation, item["manual_price"].get("calculation_currency")
                )
            estimate = calculation.estimate
            scope = estimate.cost_scope
            if scope in UNIT_SCOPES:
                expected_unit, total_scope = UNIT_SCOPES[scope]
                raw_quantity = item.get("quantity")
                if item.get("quantity_unit") != expected_unit:
                    quantity_conversion = convert(
                        raw_quantity,
                        item.get("quantity_unit"),
                        expected_unit,
                        context=options.get("unit_context"),
                        source=item.get(
                            "quantity_source", item.get("parsed_source", {})
                        ),
                    )
                    if quantity_conversion.status != "converted":
                        raise ValueError(
                            "Physical quantity conversion unresolved: "
                            + "; ".join(quantity_conversion.issues)
                        )
                    raw_quantity = quantity_conversion.value
                quantity = positive(raw_quantity, "physical quantity")
                quantity_unit = expected_unit
                scope = total_scope
            else:
                if scope not in {
                    "purchased_equipment",
                    "installed_equipment",
                    "module_estimate",
                    "building_cost",
                    "unit_capital",
                }:
                    raise ValueError("Unsupported cost scope for aggregation: " + scope)
                quantity = positive(item.get("quantity", 1), "equipment count")
                quantity_unit = item.get("quantity_unit", "item")
                if quantity_unit != "item" or not quantity.is_integer():
                    raise ValueError(
                        "Whole equipment prices require an integer item count"
                    )
            amount = positive(estimate.amount * quantity, "extended line cost")
            component_costs = {
                name: (
                    getattr(calculation, name) * quantity
                    if getattr(calculation, name) is not None
                    else None
                )
                for name in (
                    "equipment_cost",
                    "installation_cost",
                    "equipment_and_installation_cost",
                )
            }
            if any(
                value is not None and not isfinite(value)
                for value in component_costs.values()
            ):
                raise ValueError(
                    "Extended equipment/installation cost exceeds numerical limits"
                )
            currency, index, period, series = aggregation_basis(calculation)
            key = (currency, index, period, scope, series)
            groups.setdefault(key, []).append((item["equipment_tag"], amount))
            lines.append(
                EquipmentCostLine(
                    item["equipment_tag"],
                    item.get("curve_id")
                    or ("manual:user-price" if item.get("manual_price") else None),
                    calculation.status,
                    amount,
                    quantity,
                    quantity_unit,
                    scope,
                    calculation,
                    calculation.issues,
                    item.get("parsed_source"),
                    **component_costs,
                    quantity_conversion=quantity_conversion,
                )
            )
        except (ValueError, KeyError, TypeError, OverflowError) as exc:
            lines.append(
                EquipmentCostLine(
                    item["equipment_tag"],
                    item.get("curve_id"),
                    "needs_review",
                    None,
                    quantity,
                    quantity_unit,
                    scope,
                    calculation,
                    (str(exc),),
                    item.get("parsed_source"),
                    quantity_conversion=quantity_conversion,
                )
            )
    subtotals = tuple(
        CostSubtotal(
            *key[:4],
            positive(fsum(v for _, v in rows), "subtotal"),
            tuple(t for t, _ in rows),
            index_series=key[4],
        )
        for key, rows in sorted(groups.items())
    )
    issues = []
    if not items:
        issues.append("No equipment supplied; no total can be calculated")
    if any(line.amount is None for line in lines):
        issues.append(
            "Unresolved equipment: subtotals are partial; complete total unavailable"
        )
    if len(subtotals) > 1:
        issues.append(
            "Different currencies, index/date bases or cost scopes must be reconciled before a combined total"
        )
    total = subtotals[0].amount if len(subtotals) == 1 and not issues else None
    status = (
        "needs_review"
        if issues
        else (
            "provisional"
            if any(line.status == "provisional" for line in lines)
            else "calculated"
        )
    )
    component_groups = {}
    installation_issues = []
    for line in lines:
        if line.calculation and line.calculation.estimate and line.amount is not None:
            estimate = line.calculation.estimate
            key = aggregation_basis(line.calculation)
            component_groups.setdefault(key, []).append(line)
        if is_scoped_capital(line.cost_scope, line.calculation.evidence if line.calculation else None):
            installation_issues.append(
                f"{line.equipment_tag}: source-defined scoped capital cost; purchase/installation not decomposed, no extra installation factor applied"
            )
            continue
        if line.installation_cost is None:
            reason = (
                line.calculation.installation.status
                if line.calculation and line.calculation.installation
                else "equipment price unresolved"
            )
            installation_issues.append(
                f"{line.equipment_tag}: installation breakdown unavailable ({reason})"
            )
    components = tuple(
        EquipmentInstallationSubtotal(
            *key[:3],
            _complete_sum(rows, "equipment_cost"),
            _complete_sum(rows, "installation_cost"),
            _complete_sum(rows, "equipment_and_installation_cost"),
            tuple(line.equipment_tag for line in rows),
            tuple(line.equipment_tag for line in rows if line.equipment_cost is None),
            tuple(
                line.equipment_tag for line in rows if line.installation_cost is None
            ),
            tuple(
                line.equipment_tag
                for line in rows
                if line.equipment_and_installation_cost is None
            ),
            index_series=key[3],
        )
        for key, rows in sorted(component_groups.items())
    )
    compatible = (
        bool(lines)
        and len(component_groups) == 1
        and all(line.amount is not None for line in lines)
    )
    equipment_total = _complete_sum(lines, "equipment_cost") if compatible else None
    installation_total = (
        _complete_sum(lines, "installation_cost") if compatible else None
    )
    combined_total = (
        _complete_sum(lines, "equipment_and_installation_cost") if compatible else None
    )
    if len(component_groups) > 1:
        installation_issues.append(
            "Component totals require a common currency and index/date basis"
        )
    breakdown_status = (
        "provisional"
        if compatible
        and all(
            v is not None for v in (equipment_total, installation_total, combined_total)
        )
        else "needs_review"
    )
    return EquipmentCostTotal(
        status,
        total,
        subtotals,
        tuple(lines),
        tuple(issues),
        equipment_total,
        installation_total,
        combined_total,
        components,
        breakdown_status,
        tuple(installation_issues),
    )
