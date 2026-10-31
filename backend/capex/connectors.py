"""Inactive pure adapters. Preparing inputs never calculates or saves CAPEX."""

import copy

from .models import CapexInputs, EquipmentCost


def prepare_capex_inputs(
    equipment_total, *, process_type, delivery_basis, process_description="", **options
):
    """Read only canonical per-line equipment components, not legacy .total.

    Delivered versus ex-works basis must be supplied explicitly. Installed-only
    costs without a purchase split are blocked; bare-module amounts never become
    purchased-equipment inputs. No equipment engine function is invoked.
    """
    records = []
    if not equipment_total.equipment:
        raise ValueError("No canonical equipment records")
    for line in equipment_total.equipment:
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
        estimate = line.calculation.estimate
        records.append(
            EquipmentCost(
                tag=line.equipment_tag,
                purchased_cost=line.equipment_cost,
                currency=estimate.currency,
                period=estimate.period,
                index_series="CEPCI",
                index_value=estimate.cost_index,
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
    return CapexInputs(tuple(records), process_type, process_description, **options)
