"""Before/after values from the same canonical stage outputs; no second valuation."""


def compare_results(before, after):
    def cells(results):
        stages = (results or {}).get("stages", {})
        values = {}
        for stage, fields in {
            "equipment": [
                "equipment_cost_total",
                "installation_cost_total",
                "equipment_and_installation_cost_total",
            ],
            "capex": ["total_capex"],
            "opex": ["first_year_cash_opex"],
        }.items():
            result = stages.get(stage, {}).get("result") or {}
            for field in fields:
                values[stage + "." + field] = result.get(field)
        finance = stages.get("financial", {}).get("result") or {}
        for key, metric in finance.get("metrics", []):
            values["financial." + key] = metric.get("value")
        return values

    left, right = cells(before), cells(after)
    return [
        {"metric": key, "previous": left.get(key), "updated": right.get(key)}
        for key in sorted(left.keys() | right.keys())
        if left.get(key) != right.get(key)
    ]
