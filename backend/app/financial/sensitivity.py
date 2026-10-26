"""One-at-a-time sensitivities: deterministic stresses, never probabilities."""

from app.financial.dcf_model import FinancialInputs, calculate_dcf


def tornado(inputs: FinancialInputs, swing: float = 0.2) -> dict:
    baseline = calculate_dcf(inputs).npv_usd
    rows = []
    for key, label in [
        ("total_capex_usd", "CAPEX"),
        ("feedstock_opex_usd_per_year", "Feedstock"),
        ("utility_opex_usd_per_year", "Utilities"),
        ("fixed_opex_usd_per_year", "Fixed OPEX"),
        ("product_selling_price_usd_per_unit", "Selling price"),
        ("discount_rate", "Discount rate"),
    ]:
        outcomes = []
        for change in (-swing, swing):
            data = inputs.model_dump()
            data[key] *= 1 + change
            if key in ("feedstock_opex_usd_per_year", "utility_opex_usd_per_year"):
                data["variable_opex_usd_per_year"] += getattr(inputs, key) * change
            outcomes.append(calculate_dcf(FinancialInputs.model_validate(data)).npv_usd)
        rows.append(
            {
                "parameter": key,
                "label": label,
                "low_input_npv_usd": outcomes[0],
                "high_input_npv_usd": outcomes[1],
                "low_delta_usd": min(outcomes) - baseline,
                "high_delta_usd": max(outcomes) - baseline,
                "span_usd": abs(outcomes[1] - outcomes[0]),
            }
        )
    return {
        "baseline_npv_usd": baseline,
        "swing_fraction": swing,
        "rows": sorted(rows, key=lambda r: r["span_usd"], reverse=True),
    }
