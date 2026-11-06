"""Inactive pure adapters. Preparing inputs never calculates or saves CAPEX."""

from backend.equipment_costing.models import is_scoped_capital

import copy

from backend.equipment_costing.cost_to_future.cost_translation import aggregation_basis

from .models import CapexInputs, EquipmentCost, UnitCapitalCost


def prepare_capex_inputs(
    equipment_total, *, process_type, delivery_basis, process_description="", **options
):
    """Read only canonical per-line equipment components, not legacy .total.

    Delivered versus ex-works basis must be supplied explicitly. Installed-only
    costs without a purchase split are blocked; bare-module amounts never become
    purchased-equipment inputs. No equipment engine function is invoked.
    """
    records = []
    capital = []
    if not equipment_total.equipment:
        raise ValueError("No canonical equipment records")
    for line in equipment_total.equipment:
        if (
            is_scoped_capital(
                line.cost_scope, line.calculation.evidence if line.calculation else None
            )
            and line.amount is not None
            and line.calculation
            and line.calculation.estimate
        ):
            currency, index, period, series = aggregation_basis(line.calculation)
            capital.append(
                UnitCapitalCost(
                    tag=line.equipment_tag,
                    amount=line.amount,
                    currency=currency,
                    period=period,
                    index_series=series,
                    index_value=index,
                    cost_scope=line.cost_scope,
                    quantity=1,
                    included_categories=tuple(
                        line.calculation.evidence.get("included_categories", [])
                    ),
                    provenance={
                        "component": "pre-costed unit capital, already quantity-extended; never factorial purchase base",
                        "costing_evidence": copy.deepcopy(line.calculation.evidence),
                    },
                    provisional=True,
                )
            )
            continue
        if (
            line.equipment_cost is None
            or line.amount is None
            or line.calculation is None
            or line.calculation.estimate is None
        ):
            raise ValueError(
                line.equipment_tag
                + ": canonical purchased-equipment component is unresolved"
            )
        currency, index, period, series = aggregation_basis(line.calculation)
        records.append(
            EquipmentCost(
                tag=line.equipment_tag,
                purchased_cost=line.equipment_cost,
                currency=currency,
                period=period,
                index_series=series,
                index_value=index,
                quantity=1,
                cost_scope="purchased_equipment",
                delivery_basis=delivery_basis,
                provenance={
                    "component": "equipment_cost; already quantity-extended",
                    "parser_source": copy.deepcopy(line.parsed_source),
                    "costing_evidence": copy.deepcopy(line.calculation.evidence),
                },
                provisional=line.status == "provisional",
            )
        )
    return CapexInputs(
        tuple(records),
        process_type,
        process_description,
        pre_costed_capital=tuple(capital),
        **options
    )
