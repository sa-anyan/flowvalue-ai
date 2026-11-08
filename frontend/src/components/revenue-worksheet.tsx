'use client';

import {useState} from 'react';
import {assessmentHref} from '../lib/assessment-navigation';
import './revenue-worksheet.css';

type Row = Record<string, unknown>;
const row = (value: unknown): Row => value && typeof value === 'object' && !Array.isArray(value) ? value as Row : {};
const rows = (value: unknown): Row[] => Array.isArray(value) ? value.map(row) : [];
const number = (value: unknown) => typeof value === 'number' || (typeof value === 'string' && value.trim() !== '')
  ? Number.isFinite(Number(value)) ? Number(value) : null
  : null;
const fmt = (value: unknown) => number(value)?.toLocaleString('en-GB', {maximumFractionDigits: 2}) ?? '—';
const money = (value: unknown, currency: string) => number(value) === null ? '—' : `${currency} ${fmt(value)}`;

const fields = [
  ['flow', 'Production rate / hour', 0, undefined, 'e.g. 100'],
  ['hours', 'Hours / day', 0, 24, 'e.g. 24'],
  ['days', 'Days / year', 0, 366, 'e.g. 314'],
  ['ramp', 'Throughput (%)', 0, 100, 'e.g. 100'],
  ['saleable', 'Saleable (%)', 0, 100, 'e.g. 100'],
  ['sold', 'Sold of saleable (%)', 0, 100, 'e.g. 100'],
  ['price', 'Net selling price / unit', 0, undefined, 'Enter price'],
  ['opex', 'Allocated annual cash OPEX (optional)', 0, undefined, 'Enter annual cost'],
] as const;
type Field = typeof fields[number][0];
type Draft = {id: string; name: string; unit: string; included: boolean; values: Partial<Record<Field, string>>};
const blank = (id: string): Draft => ({id, name: '', unit: '', included: false, values: {}});

export function draftProduct(values: Draft['values']) {
  const numbers = Object.fromEntries(fields.map(([key, , min, max]) => {
    const value = number(values[key]);
    return [key, value !== null && value >= min && (max === undefined || value <= max) ? value : null];
  })) as Record<Field, number | null>;
  const {flow, hours, days, ramp, saleable, sold, price, opex} = numbers;
  const produced = flow === null || hours === null || days === null || ramp === null ? null : flow * hours * days * ramp / 100;
  const quantity = produced === null || saleable === null || sold === null ? null : produced * saleable * sold / 10000;
  return {produced, quantity, annual: quantity === null || price === null ? null : quantity * price,
    unitCost: produced !== null && produced > 0 && opex !== null ? opex / produced : null};
}

export function cumulativeSaved(records: Row[], field: string, through: number) {
  const values = new Map(records.map(record => [number(record.year), number(record[field])]));
  let total = 0;
  for (let year = 1; year <= through; year++) {
    const value = values.get(year);
    if (value == null) return null;
    total += value;
  }
  return total;
}

function Figures({items}: {items: [string, string][]}) {
  return <dl className="rv-worksheet-figures">{items.map(([label, value]) =>
    <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>;
}

export function RevenueWorksheet({id, year, config, result, opex, financial, schedule, disabled, onEdit}: {
  id: string; year: string; config: Row; result: Row; opex: unknown; financial: unknown;
  schedule?: unknown; disabled?: boolean; onEdit?: () => void;
}) {
  const [drafts, setDrafts] = useState<Draft[]>([blank('first')]);
  const [draftCurrency, setDraftCurrency] = useState('');
  const [horizon, setHorizon] = useState('');
  const draftYears = number(horizon);
  const validHorizon = draftYears !== null && Number.isInteger(draftYears) && draftYears >= 1 && draftYears <= 50 ? draftYears : null;
  const included = drafts.filter(draft => draft.included);
  const includedValues = included.map(draft => draftProduct(draft.values).annual);
  const draftTotal = includedValues.length && includedValues.every(value => value !== null)
    ? includedValues.reduce<number>((sum, value) => sum + (value ?? 0), 0) : null;
  const editDraft = (id: string, patch: Partial<Draft>) => setDrafts(current =>
    current.map(draft => draft.id === id ? {...draft, ...patch} : draft));

  const products = rows(result.products);
  const selected = products.filter(product => String(product.year) === year);
  const annual = rows(result.annual);
  const savedYear = number(year) ?? 1;
  const lastYear = Math.max(0, ...annual.map(record => number(record.year) ?? 0));
  const checkpoints = [...new Set([1, 2, 5, lastYear])].filter(point => point > 0 && point <= lastYear).sort((a,b) => a-b);
  const basis = row(result.basis);
  const currency = String(basis.currency ?? '');
  const hours = number(row(schedule).hours);
  const ramp = number(row(row(schedule).ramp)[year]);
  const operating = row(config.operating);
  const opexYear = row(row(row(opex).years)[year]);
  const sameBasis = row(opex).currency === basis.currency && row(opex).price_period === basis.price_period;
  const cashOpex = sameBasis ? number(opexYear.annual_cash_opex) : null;
  const charges = sameBasis ? rows(opexYear.lines).filter(line => line.calculation_base === 'annual_revenue') : [];
  const cashFlow = rows(row(financial).ledger);

  return <details className="rv-panel rv-worksheet" open={!annual.length || undefined}>
    <summary>Product sales worksheet <small>Calculation, cumulative revenue and editable estimates</small></summary>
    {selected.map(product => {
      const line = rows(config.sales).find(sale => sale.id === product.product_id);
      const history = products.filter(record => record.product_id === product.product_id);
      const unit = String(product.quantity_unit ?? '');
      const quantity = (value: unknown) => number(value) === null ? '—' : `${fmt(value)} ${unit}`;
      const price = (value: unknown) => number(value) === null ? '—' : `${money(value, currency)} / ${unit}`;
      const produced = number(product.produced_quantity);
      const unitCost = selected.length === 1 && !rows(result.commercial).some(line => String(line.year) === year)
        && cashOpex !== null && produced !== null && produced > 0 ? cashOpex / produced : null;
      return <details key={String(product.product_id)} className="rv-worksheet-line" open={selected.length === 1 || undefined}>
        <summary>{String(line?.name ?? product.product_id)} <small>Saved · operating year {year}</small></summary>
        <Figures items={[
          ['Source production rate', number(product.normalized_flow_per_hour) === null ? '—' : `${quantity(product.normalized_flow_per_hour)} / hour`],
          ['Operating schedule', hours === null ? '—' : `${fmt(hours)} h/year${number(operating.days_per_year) === null || number(operating.hours_per_day) === null ? '' : ` · ${fmt(operating.days_per_year)} days × ${fmt(operating.hours_per_day)} h/day`}`],
          ['Throughput ramp', ramp === null ? '—' : `${fmt(ramp * 100)}%`],
          ['Produced', quantity(produced)], ['Saleable', quantity(product.saleable_quantity)], ['Sold', quantity(product.quantity_sold)],
          ['Net selling price', price(product.net_selling_price)], ['Annual revenue', money(product.net_sales_revenue, currency)],
          ['Quantity sold through selected year', quantity(cumulativeSaved(history, 'quantity_sold', savedYear))],
          ['Revenue through selected year', money(cumulativeSaved(history, 'net_sales_revenue', savedYear), currency)],
          ['Cash production cost per unit produced', price(unitCost)],
        ]}/>
        <p className="rv-chart-note">Sold quantity × net selling price = annual product revenue. Unit cost uses matching annual cash OPEX when there is one product and no commercial income to allocate.</p>
        {onEdit && <button type="button" className="secondary" onClick={onEdit} disabled={disabled}>Edit saved assumptions</button>}
      </details>;
    })}
    {checkpoints.length > 0 && <div className="table-wrap"><table>
      <caption>Cumulative saved revenue by operating year · {currency}</caption>
      <thead><tr><th scope="col">Through year</th>{checkpoints.map(point => <th key={point} scope="col">{point}</th>)}</tr></thead>
      <tbody>
        {[...new Set(products.map(product => product.product_id))].map(id => {
          const history = products.filter(product => product.product_id === id);
          return <tr key={String(id)}><th scope="row">{String(rows(config.sales).find(sale => sale.id === id)?.name ?? id)}</th>
            {checkpoints.map(point => <td key={point}>{money(cumulativeSaved(history, 'net_sales_revenue', point), currency)}</td>)}</tr>;
        })}
        <tr><th scope="row">Total included income</th>{checkpoints.map(point =>
          <td key={point}>{money(cumulativeSaved(annual, 'sales_revenue', point), currency)}</td>)}</tr>
      </tbody>
    </table></div>}
    {(charges.length > 0 || cashFlow.length > 0) && <details className="rv-worksheet-line">
      <summary>OPEX and financial handoff</summary>
      {charges.length > 0 && <><p>Saved OPEX charges using annual revenue in operating year {year}.</p>
        <Figures items={charges.map(line => [String(line.id).replaceAll('_', ' '),
          `${fmt((number(line.rate) ?? 0) * 100)}% × ${money(line.base_amount, currency)} = ${money(line.amount, currency)}`])}/>
        <a href={assessmentHref('/opex', id)}>Open OPEX</a></>}
      {cashFlow.length > 0 && <><div className="table-wrap"><table>
        <caption>Saved financial ledger · project years · {String(row(financial).currency ?? currency)}</caption>
        <thead><tr><th scope="col">Project year</th><th scope="col">Revenue</th><th scope="col">Project cash flow</th></tr></thead>
        <tbody>{cashFlow.map(record => <tr key={String(row(record.period).year)}>
          <th scope="row">{fmt(row(record.period).year)}</th><td>{fmt(record.revenue)}</td><td>{fmt(record.fcff)}</td>
        </tr>)}</tbody>
      </table></div><a href={assessmentHref('/financial-modelling', id)}>Open Financial Modelling</a></>}
    </details>}
    <details className="rv-worksheet-line" open={!annual.length || undefined}>
      <summary>Editable estimates <small>Draft · independent of approved revenue</small></summary>
      <p className="rv-chart-note">Use the blank fields to model one operating case. Drafts stay on this page until you leave it. {onEdit ? 'To change the assessment, edit its Revenue lines and calculate the approved inputs.' : 'Open an assessment to use its saved Revenue lines.'}</p>
      <div className="rv-worksheet-inputs">
        <label className="field"><span>Currency</span><input placeholder="e.g. GBP" value={draftCurrency} onChange={event => setDraftCurrency(event.target.value)}/></label>
        <label className="field"><span>Operating horizon (years)</span><input type="number" min="1" max="50" placeholder="Enter years" value={horizon} onChange={event => setHorizon(event.target.value)}/></label>
      </div>
      {drafts.map((draft, index) => {
        const {produced, quantity, annual, unitCost} = draftProduct(draft.values);
        const qty = (value: number | null) => value === null ? '—' : `${fmt(value)} ${draft.unit}`;
        return <fieldset className="rv-worksheet-line" key={draft.id}>
          <legend>{draft.name || `Product ${index + 1}`}</legend>
          <div className="rv-worksheet-inputs">
            <label className="field"><span>Product name</span><input placeholder="Enter product or by-product" value={draft.name} onChange={event => editDraft(draft.id, {name: event.target.value})}/></label>
            <label className="field"><span>Quantity unit</span><input placeholder="e.g. kg or tonne" value={draft.unit} onChange={event => editDraft(draft.id, {unit: event.target.value})}/></label>
            {fields.map(([key, label, min, max, placeholder]) => <label className="field" key={key}>
              <span>{label}</span><input type="number" min={min} max={max} step="any" placeholder={placeholder}
                value={draft.values[key] ?? ''} onChange={event => editDraft(draft.id, {values: {...draft.values, [key]: event.target.value}})}/>
            </label>)}
          </div>
          <Figures items={[
            ['Annual production', qty(produced)], ['Annual quantity sold', qty(quantity)],
            ['Annual revenue forecast', money(annual, draftCurrency.trim().toUpperCase())],
            ['Cumulative quantity sold', quantity === null || validHorizon === null ? '—' : qty(quantity * validHorizon)],
            ['Cumulative revenue at constant annual sales', annual === null || validHorizon === null ? '—' : money(annual * validHorizon, draftCurrency.trim().toUpperCase())],
            ['Cash cost / unit produced', unitCost === null ? '—' : `${money(unitCost, draftCurrency.trim().toUpperCase())} / ${draft.unit || 'unit'}`],
          ]}/>
          <label className="check"><input type="checkbox" checked={draft.included} onChange={event => editDraft(draft.id, {included: event.target.checked})}/> Include in draft total</label>
          {drafts.length > 1 && <button type="button" className="secondary" onClick={() => setDrafts(current => current.filter(line => line.id !== draft.id))}>Remove draft product</button>}
        </fieldset>;
      })}
      <Figures items={[
        ['Included annual draft revenue', money(draftTotal, draftCurrency.trim().toUpperCase())],
        ['Included cumulative draft revenue', draftTotal === null || validHorizon === null ? '—' : money(draftTotal * validHorizon, draftCurrency.trim().toUpperCase())],
      ]}/>
      <button type="button" className="secondary" onClick={() => setDrafts(current => [...current, blank(crypto.randomUUID())])}>Add draft product</button>
      {onEdit && <button type="button" className="secondary" onClick={onEdit} disabled={disabled}>Open Revenue workspace</button>}
    </details>
  </details>;
}
