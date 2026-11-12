"""Decimal text from canonical stages, separate from float statistics.

Schema version 1 uses JSON strings for finite amounts and null for missing
amounts. Invalid/non-finite fields also have a path in invalid_numeric_fields.
Existing float-valued stage fields are bridged by their decimal text, so the
projection preserves their published precision without inventing extra digits.
"""

from decimal import Decimal, InvalidOperation


def project_exact_values(metrics, equipment, equipment_result, capex, opex, revenue, financial):
    invalid = []

    def amount(value, path):
        if value is None:
            return None
        try:
            decimal = Decimal(str(value))
        except (InvalidOperation, ValueError):
            decimal = None
        if decimal is None or not decimal.is_finite():
            invalid.append(path)
            return None
        return str(decimal)

    def fields(row, keys, path):
        return {key: amount(row.get(key), f"{path}.{key}") for key in keys}

    return {
        "schema_version": 1,
        "invalid_numeric_fields": invalid,
        "metrics": fields(metrics, metrics, "metrics"),
        "equipment": [
            {"record_key": row["record_key"], **fields(
                row, ("cost", "installation_cost"), f"equipment.{row['record_key']}"
            )}
            for row in equipment
        ],
        "equipment_totals": fields(
            equipment_result,
            ("total", "equipment_cost_total", "installation_cost_total",
             "equipment_and_installation_cost_total"),
            "equipment_totals",
        ),
        "stage_status": {
            "equipment": equipment_result.get("status"),
            "capex": capex.get("status"),
            "opex": opex.get("status"),
            "revenue": revenue.get("status"),
            "financial": financial.get("status"),
        },
        "capex_subtotals": fields(
            capex,
            ("purchased_equipment", "direct_costs", "indirect_costs", "plant_cost",
             "fixed_capital", "startup_expenses", "working_capital", "total_capex"),
            "capex_subtotals",
        ),
        "capex_components": {
            row["id"]: amount(row.get("amount"), f"capex_components.{row['id']}")
            for row in capex.get("lines", [])
        },
        "opex_components": {
            row["id"]: amount(row.get("amount"), f"opex_components.{row['id']}")
            for row in opex.get("first_year_lines", [])
        },
        "annual_opex": {
            year: {
                "status": row.get("status"),
                **fields(row, ("annual_cash_opex", "resolved_cash_subtotal", "cash_fixed",
                               "cash_variable", "depreciation"), f"annual_opex.{year}"),
            }
            for year, row in opex.get("years", {}).items()
        },
        "annual_revenue": {
            str(row["year"]): fields(row, ("sales_revenue", "separate_opex_charges"),
                                     f"annual_revenue.{row['year']}")
            for row in revenue.get("annual", [])
        },
        "cash_flow": [
            {"year": row["period"]["year"], **fields(
                row, ("fcff", "revenue", "capex", "known_cash_opex_subtotal"),
                f"cash_flow.{row['period']['year']}"
            )}
            for row in financial.get("ledger", [])
        ],
    }
