'use client';

import {useState} from 'react';
import type {Row} from '@/lib/monte-carlo';

const object = (v: unknown): Row => v && typeof v === 'object' && !Array.isArray(v) ? v as Row : {};
const rows = (v: unknown): Row[] => Array.isArray(v) ? v.map(object) : [];
const label = (v: unknown) => String(v ?? '').replaceAll('_', ' ');
const value = (v: unknown) => v === null || v === undefined ? 'Not available' : Number.isFinite(Number(v)) ? new Intl.NumberFormat('en-GB', {maximumFractionDigits: 2}).format(Number(v)) : String(v);
const precise = (v: unknown) => v === null || v === undefined ? 'Not available' : new Intl.NumberFormat('en-GB', {maximumFractionDigits: 8}).format(Number(v));
const percent = (v: unknown) => v === null || v === undefined ? '—' : `${new Intl.NumberFormat('en-GB', {maximumFractionDigits: 4}).format(Number(v) * 100)}%`;

function Evidence({row}: {row: Row}) {
 const source = object(row.source);
 const notes = Array.isArray(row.notes) ? row.notes : Array.isArray(row.issues) ? row.issues : [];
 return <details><summary>Basis & source</summary>
  {Boolean(row.formula) && <p>{String(row.formula)}</p>}
  {Boolean(row.rationale) && <p>{String(row.rationale)}</p>}
  <p>{String(source.reference || row.source_title || (typeof row.source === 'string' ? row.source : '') || 'See saved configuration')}{source.printed_page ? ` · p. ${source.printed_page}` : ''}</p>
  {notes.length > 0 && <ul>{notes.map((note, i) => <li key={i}>{String(note)}</li>)}</ul>}
 </details>;
}
function Totals({items, currency}: {items: [string, unknown][]; currency: string}) {
 return <dl className="mc-cost-totals">{items.map(([name, amount]) => <div key={name}><dt>{name}</dt><dd>{value(amount)} {currency}</dd></div>)}</dl>;
}
function Equipment({data}: {data: Row}) {
 return <><p>Unit prices and quantity-extended costs from this variation. Source-defined system costs retain their scope; installation is handled in CAPEX.</p>
 <div className="mc-matrix-scroll mc-table-viewport"><table className="mc-matrix mc-cost-table"><thead><tr><th>Equipment / model</th><th>Size</th><th>Quantity</th><th>Unit estimate</th><th>Equipment cost</th></tr></thead><tbody>
 {rows(data.equipment).map((row, i) => {const estimate = object(row.unit_estimate);return <tr key={String(row.record_key || i)}><th>{String(row.equipment_tag)}<small>{String(estimate.variant || row.curve_id || 'No selected model')}</small><small>{label(row.cost_scope)} · {label(row.price_coverage)}</small><Evidence row={{...estimate, issues: row.issues}}/></th><td>{precise(estimate.size)} {String(estimate.size_unit || '')}</td><td>{value(row.quantity)} {String(row.quantity_unit || '')}</td><td>{value(estimate.amount)} {String(estimate.currency || '')}</td><td>{row.price_coverage === 'excluded' ? 'Excluded alias' : row.price_coverage === 'unpriced' ? 'Unpriced' : value(row.equipment_cost ?? row.amount)}</td></tr>;})}
 </tbody></table></div><p>The Equipment cost column is already extended for quantity. Do not multiply it again. Scope and currency adjustments are recorded in CAPEX.</p></>;
}
function Capex({data, currency}: {data: Row; currency: string}) {
 return <><p>{label(data.model_id)} method · {currency} {String(data.period || '')}. Each percentage applies to its stated base.</p>
 <div className="mc-matrix-scroll mc-table-viewport"><table className="mc-matrix mc-cost-table"><thead><tr><th>Cost line</th><th>Base</th><th>Factor</th><th>Amount</th></tr></thead><tbody>
 {rows(data.lines).map((row, i) => <tr key={String(row.id || i)}><th>{label(row.id)}<small>{label(row.status)}</small><Evidence row={row}/></th><td>{row.status === 'embedded' ? '—' : value(row.base_amount)}<small>{label(row.base)}</small></td><td>{percent(row.fraction)}</td><td>{row.status === 'embedded' || row.status === 'combined' ? 'Included elsewhere' : value(row.amount)}</td></tr>)}
 </tbody></table></div>
 <h4>CAPEX build-up</h4><p>These are successive subtotals, not additional charges to add together. Total CAPEX = fixed capital + startup expenses + working capital.</p>
 <Totals currency={currency} items={[
 ['Purchased equipment', data.purchased_equipment], ['Direct costs', data.direct_costs], ['Indirect costs', data.indirect_costs],
 ['Plant cost', data.plant_cost], ['Fixed capital', data.fixed_capital], ['Startup expenses', data.startup_expenses],
 ['Working capital', data.working_capital], ['Total CAPEX', data.total_capex],
 ]}/>
 <details><summary>Category coverage and included costs</summary>{rows(data.breakdown).map((row, i) => <div key={String(row.category || i)}><strong>{String(row.label)} · {value(row.amount)}</strong><p>{label(row.status)} · {row.counted ? 'Counted by the engine' : 'Not an additional charge'}. {String(row.basis || '')} {String(row.note || '')}</p></div>)}</details></>;
}
function Opex({data, currency}: {data: Row; currency: string}) {
 return <><p>Operating year {String(data.year || 1)} · {value(data.annual_hours)} operating hours. Noncash and excluded costs stay visible and are labelled separately.</p>
 <div className="mc-matrix-scroll mc-table-viewport"><table className="mc-matrix mc-cost-table"><thead><tr><th>Expense</th><th>Calculation</th><th>Annual amount</th></tr></thead><tbody>
 {rows(data.first_year_lines).map((row, i) => <tr key={String(row.id || i)}><th>{label(row.id)}<small>{label(row.category)} · {label(row.behavior)} · {label(row.accounting)} · {label(row.scope)}</small><Evidence row={{...row, formula: row.engineering_formula}}/></th><td>{row.method === 'percentage' ? <>{percent(row.rate)} × {value(row.base_amount)}<small>{label(row.calculation_base)}</small></> : row.quantity != null && row.rate != null ? <>{value(row.quantity)} {String(row.quantity_unit || '')} × {precise(row.rate)} {currency}/{String(row.rate_unit || 'unit')}</> : <>{label(row.method)}<small>{label(row.calculation_base)}</small></>}</td><td>{value(row.amount)}</td></tr>)}
 </tbody></table></div>
 <Totals currency={currency} items={[
 ['Fixed cash OPEX', data.first_year_fixed_opex], ['Variable cash OPEX', data.first_year_variable_opex],
 ['Known cash subtotal', data.known_cash_opex_subtotal], ['Annual cash OPEX', data.first_year_cash_opex],
 ['Depreciation (noncash; excluded from cash OPEX)', data.depreciation],
 ]}/></>;
}
function Revenue({data, currency}: {data: Row; currency: string}) {
 const annual = rows(data.annual)[0] || {};
 return <><p>Operating year 1 revenue used in this variation’s economics. Any saved financial ramp belongs to this configuration.</p>
 <div className="mc-matrix-scroll mc-table-viewport"><table className="mc-matrix mc-cost-table"><thead><tr><th>Income line</th><th>Quantity / rate</th><th>Price</th><th>Annual revenue</th></tr></thead><tbody>
 {rows(data.products).map((row, i) => <tr key={String(row.product_id || i)}><th>{label(row.product_id)}<small>Stream: {String(row.stream_id)}</small><details><summary>Quantity build-up</summary><p>{value(row.normalized_flow_per_hour)} {String(row.quantity_unit)}/hour → {value(row.produced_quantity)} produced → {value(row.saleable_quantity)} saleable → {value(row.quantity_sold)} sold.</p><p>Quoted price {precise(row.quoted_price)} + premium {value(row.premium_per_unit)} − deductions {value(row.deduction_per_unit)} = {precise(row.net_selling_price)} {currency}/{String(row.quantity_unit)}.</p></details></th><td>{value(row.quantity_sold)} {String(row.quantity_unit)}</td><td>{precise(row.net_selling_price)} {currency}/{String(row.quantity_unit)}</td><td>{value(row.net_sales_revenue)}</td></tr>)}
 {rows(data.commercial).map((row, i) => <tr key={String(row.line_id || i)}><th>{label(row.line_id)}<small>{label(row.category)} · {label(row.status)}</small></th><td>{value(row.quantity)} {String(row.quantity_unit)}</td><td>{precise(row.rate)}<small>+ fixed payment {value(row.fixed_payment)}</small></td><td>{value(row.revenue)}</td></tr>)}
 </tbody></table></div><Totals currency={currency} items={ [['Annual sales revenue', annual.sales_revenue], ['Separate OPEX charges (handled in OPEX)', annual.separate_opex_charges]]}/></>;
}
export function CalculationBreakdown({run}: {run: Row}) {
 const [section, setSection] = useState('CAPEX');
 const trace = object(run.calculation_trace), verification = object(run.trace_verification);
 const capex = object(trace.capex), currency = String(capex.currency || run.currency || '');
 return <section aria-label="Calculation breakdown"><h3>What built these totals?</h3><p>{String(verification.status === 'replayed' ? 'Verified reconstruction from this run’s frozen inputs. Costs and cash flow match the saved variation exactly.' : verification.notice || 'Calculation rows saved with this variation.')}</p>
 {Object.keys(trace).length > 0 ? <><div className="mc-view-switch" role="group" aria-label="Cost breakdown section">{['Equipment', 'CAPEX', 'OPEX', 'Revenue'].map(name => <button key={name} aria-pressed={section === name} onClick={() => setSection(name)}>{name}</button>)}</div>
 <div role="region" aria-label={`${section} calculation breakdown`}>
 {section === 'Equipment' && <Equipment data={object(trace.equipment)}/>}
 {section === 'CAPEX' && <Capex data={capex} currency={currency}/>}
 {section === 'OPEX' && <Opex data={object(trace.opex)} currency={String(object(trace.opex).currency || currency)}/>}
 {section === 'Revenue' && <Revenue data={object(trace.revenue)} currency={String(object(object(trace.revenue).basis).currency || currency)}/>}
 </div></> : <p>Saved inputs and totals are available below. No unverified breakdown is substituted.</p>}
 </section>;
}
