"""Canonical capex handoff; no other stage is executed here."""

import copy
import dataclasses
from backend.capex import calculate_capex
from backend.capex.connectors import prepare_capex_inputs
from backend.capex.models import CapexInputs, WorkingCapital
from backend.orchestration.codec import construct, plain


def calculate_capital(priced, total, plan, description, translation_policy=None):
    objects = {"equipment": total}
    if not priced:
        raise ValueError(
            "No priced purchased-equipment components; CAPEX is unresolved, not zero"
        )
    config = copy.deepcopy(plan.get("capex", {}))
    model = config.pop("model_id", "garrett")
    if model == "nottingham_lang":
        raise ValueError(
            "Lang is a screening comparison only; select a detailed CAPEX methodology"
        )
    delivery = config.pop("delivery_basis")
    config.pop("equipment", None)
    subset = dataclasses.replace(total, equipment=tuple(priced))
    prepared = prepare_capex_inputs(
        subset,
        process_type=config.pop("process_type"),
        delivery_basis=delivery,
        process_description=description,
    )
    config.pop("process_description", None)
    if translation_policy and translation_policy.get("enabled") is not False:
        from backend.equipment_costing.cost_to_future.cost_translation import (
            translate_cost,
        )

        for key, override in config.get("overrides", {}).items():
            if override.get("amount") is not None:
                basis = override.get("price_basis")
                if not basis:
                    raise ValueError(
                        "CAPEX monetary override requires price_basis for translation: "
                        + key
                    )
                adjusted = translate_cost(
                    override["amount"],
                    currency=basis["currency"],
                    source_period=basis["price_period"],
                    policy=translation_policy,
                )
                objects.setdefault("capex_price_translation", []).append(
                    {"path": "overrides." + key, **dataclasses.asdict(adjusted)}
                )
                override["amount"] = str(adjusted.amount)
                override.pop("price_basis")
        working = config.get("working_capital", {})
        if any(
            working.get(k) is not None
            for k in ("amount", "annual_opex", "installed_equipment_cost")
        ):
            basis = working.pop("price_basis", None)
            if not basis:
                raise ValueError(
                    "Monetary working-capital assumptions require price_basis for translation"
                )
            for key in ("amount", "annual_opex", "installed_equipment_cost"):
                if working.get(key) is not None:
                    adjusted = translate_cost(
                        working[key],
                        currency=basis["currency"],
                        source_period=basis["price_period"],
                        policy=translation_policy,
                    )
                    objects.setdefault("capex_price_translation", []).append(
                        {
                            "path": "working_capital." + key,
                            **dataclasses.asdict(adjusted),
                        }
                    )
                    working[key] = str(adjusted.amount)
    prepared = construct(CapexInputs, dict(plain(prepared), **config))
    try:
        screening = calculate_capex(
            "nottingham_lang",
            dataclasses.replace(
                prepared,
                factor_selection="minimum",
                selected_factors={},
                overrides={},
                exclusions={},
                working_capital=WorkingCapital(
                    excluded=True,
                    rationale="Fixed-capital screening comparison only; working capital is not included",
                ),
            ),
        )
        objects["screening_comparisons"] = [
            {
                "method": "nottingham_lang",
                "result": plain(screening),
                "included_in_capex": False,
                "purpose": "Independent whole-plant screening comparison only; never added to detailed CAPEX",
            }
        ]
    except (ValueError, TypeError):
        objects["screening_comparisons"] = [
            {
                "method": "nottingham_lang",
                "included_in_capex": False,
                "status": "unavailable_for_selected_basis",
            }
        ]
    return calculate_capex(model, prepared), objects
