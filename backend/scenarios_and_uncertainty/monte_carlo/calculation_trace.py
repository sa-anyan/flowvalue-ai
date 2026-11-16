"""Compact evidence copied from canonical outputs; no independent costing math."""


def project(equipment, capex, opex, revenue, records):
    coverage = {r["record_key"]: r["price_coverage"] for r in records}
    items = []
    for row in equipment.get('equipment', []):
        calculation = row.get('calculation') or {}
        estimate = calculation.get('estimate') or {}
        source = row.get('parsed_source') or {}
        items.append({
            **{k: row.get(k) for k in ('equipment_tag', 'curve_id', 'quantity', 'quantity_unit',
               'cost_scope', 'status', 'equipment_cost', 'amount', 'installation_cost', 'issues')},
            'record_key': source.get('equipment_key'),
            'price_coverage': coverage.get(source.get('equipment_key')),
            'unit_estimate': estimate,
        })
    first = next(iter(opex.get('years', {}).values()), {})
    return {
        'equipment': {**{k: v for k, v in equipment.items() if k in (
            'equipment_cost_total', 'installation_cost_total', 'total', 'pricing_coverage', 'subtotals')}, 'equipment': items},
        'capex': {k: v for k, v in capex.items() if k in (
            'model_id', 'currency', 'period', 'purchased_equipment', 'direct_costs', 'indirect_costs',
            'plant_cost', 'fixed_capital', 'startup_expenses', 'working_capital', 'total_capex',
            'lines', 'breakdown', 'inclusion_records', 'scope_subtotals', 'issues')},
        'opex': {**{k: v for k, v in opex.items() if k in (
            'currency', 'price_period', 'first_year_cash_opex', 'first_year_fixed_opex',
            'first_year_variable_opex', 'known_cash_opex_subtotal', 'first_year_lines')},
            'year': next(iter(opex.get('years', {})), '1'),
            'depreciation': first.get('depreciation'),
            'known_cash_opex_subtotal': opex.get('known_cash_opex_subtotal', first.get('resolved_cash_subtotal')),
            'annual_hours': (opex.get('operating_detail') or {}).get('annual_hours')},
        'revenue': {k: ([r for r in v if r.get('year') == 1] if k in {'products', 'commercial', 'annual'} else v)
                    for k, v in revenue.items() if k in ('basis', 'products', 'commercial', 'annual', 'issues')},
    }
