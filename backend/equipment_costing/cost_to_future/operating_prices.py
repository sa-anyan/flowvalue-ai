"""Rebase explicit monetary assumptions without changing quantities or percentages."""

import copy
from dataclasses import asdict

from .cost_translation import translate_cost


def translate_operating_prices(config, *, target_basis, policy, indices=None):
    config = copy.deepcopy(config)
    basis = config.get("price_basis")
    if not basis or not basis.get("currency") or not basis.get("price_period"):
        raise ValueError(
            "Source currency/price period required for automatic operating-price translation"
        )
    if basis["currency"] != target_basis["currency"]:
        raise ValueError("Operating-price translation does not convert currencies")

    def has_separate_basis(value):
        if isinstance(value, dict):
            if value.get("price_observation") or (
                value.get("price_basis") and value["price_basis"] != target_basis
            ):
                return True
            return any(
                has_separate_basis(v) for k, v in value.items() if k != "price_basis"
            )
        if isinstance(value, list):
            return any(has_separate_basis(v) for v in value)
        return False

    if basis == target_basis and not has_separate_basis(config):
        return config, []
    if target_basis["price_period"] != policy["target_period"]:
        raise ValueError("Capital and operating translation targets differ")
    audit = []

    def translate(row, keys, path):
        item_basis = row.get("price_basis") or basis
        if row.get("price_observation"):
            if row.get("price_mode") and row["price_mode"] != "assumed_price":
                raise ValueError(
                    "A cost-plus target cannot also own an observed selling price"
                )
            from backend.orchestration.commercial_pricing import adjusted_price

            observation = row["price_observation"]
            item_basis = {
                "currency": observation["currency"],
                "price_period": observation["price_period"],
            }
            result = adjusted_price(
                observation, **item_basis, quantity_unit=row["quantity_unit"]
            )
            row["unit_price"] = str(result["unit_price"])
            # Original observation stays in the audit; do not relabel a historical quote.
            row.pop("price_observation")
            audit.append({"path": path, "original_price_observation": observation})
        if item_basis["currency"] != target_basis["currency"]:
            raise ValueError(
                "Mixed-currency operating assumption needs separate FX conversion: "
                + path
            )
        for key in keys:
            if row.get(key) is None:
                continue
            translated = translate_cost(
                row[key],
                currency=item_basis["currency"],
                source_period=item_basis["price_period"],
                source_series="",
                method_id="operating_assumption",
                policy=policy,
                indices=indices,
            )
            row[key] = str(translated.amount)
            audit.append({"path": path + "." + key, **asdict(translated)})
        if "price_basis" in row:
            row["price_basis"] = dict(target_basis)

    for group, keys in {
        "materials": ("unit_price",),
        "energy": ("tariff_per_kwh",),
        "labour": ("annual_base_salary",),
        "additional_expenses": ("annual_allowance",),
        "sales": (
            "unit_price",
            "net_freight_deduction_per_unit",
            "net_packaging_deduction_per_unit",
        ),
    }.items():
        for i, row in enumerate(config.get(group, [])):
            translate(row, keys, f"{group}.{i}")
    for group, keys in {
        "commercial_lines": ("rate", "fixed_payment", "minimum_payment"),
        "avoided_costs": ("amount",),
    }.items():
        for i, item in enumerate(config.get(group, [])):
            for j, row in enumerate(item.get("years", [])):
                if item.get("price_basis"):
                    row["price_basis"] = item["price_basis"]
                translate(row, keys, f"{group}.{i}.years.{j}")
    translate(config["financial"], ("closure_allowance",), "financial")
    config["price_basis"] = dict(target_basis)
    return config, audit
