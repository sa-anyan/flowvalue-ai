"""Read scenario equipment without modifying saved runs."""


def equipment_records(run):
    if "equipment_records" in run:
        yield from run["equipment_records"]
        return
    # Historical runs have display tags only. Keep the record key unknown.
    costs = run.get("equipment_costs", {})
    installation = run.get("equipment_installation_costs", {})
    for tag in dict.fromkeys([*costs, *installation]):
        yield {
            "record_key": None,
            "display_tag": tag,
            "physical_asset_id": None,
            "quantity": None,
            "equipment_count": None,
            "quantity_unit": None,
            "cost_scope": run.get("equipment_cost_scopes", {}).get(tag),
            "price_coverage": "priced",
            "cost": costs.get(tag),
            "installation_cost": installation.get(tag),
            "model_id": run.get("equipment_models", {}).get(tag),
        }
