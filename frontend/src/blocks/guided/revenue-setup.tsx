'use client';
import { useEffect, useMemo, useRef, useState } from 'react';
import { revenueDraftSignature } from '@/lib/unsaved-revenue';
import { compact, list, obj, studyReport, text, type Row } from '@/lib/guided-flow';
import { api, post } from './use-assessment';
import type { StageProps } from './flow';
import './revenue-studio.css';

/**
 * "How does this project earn money?" — chosen, not typed. The user picks the
 * M&E stream (and the component actually sold), the price and unit. Python
 * writes and approves the revenue inputs, so the Revenue stage is never
 * ambiguous; revenue then calculates in the background with CAPEX and OPEX.
 */
type Sale = { name: string; stream_key: string; component: string; unit_price: string; quantity_unit: string };
const UNITS = ['kg', 'tonne', 'lb', 'm3', 'L'];

const flowOf = (v: Row | undefined): number | null => {
  const n = v && typeof v.normalized_value === 'number' ? v.normalized_value : null;
  return n !== null && Number.isFinite(n) && n >= 0 ? n : null;
};

/** Streams that can be sold: only those with a usable mass flow (kg/h) in the workbook. */
export function streamsOf(report: Row) {
  return list(report.entities)
    .filter((e) => e.kind === 'material')
    .map((e) => {
      const values = list(e.values);
      const label = text(values.find((v) => ['name', 'description'].includes(text(v.property)))?.original_value);
      const total = flowOf(values.find((v) => text(v.property) === 'mass_flow' && !v.component));
      const components = values
        .filter((v) => text(v.property) === 'component_mass_flow' && v.component && flowOf(v) !== null && (flowOf(v) as number) > 0)
        .map((v) => ({ name: text(v.component), flow: flowOf(v) as number }));
      return { key: text(e.key), tag: text(e.identifier), label, total, components };
    })
    .filter((s) => (s.total !== null && s.total > 0) || s.components.length > 0);
}

const PER_KG: Record<string, number> = { kg: 1, tonne: 0.001, lb: 2.20462 };

/** Yearly revenue preview (Python calculates the real figure): kg/h × hours × price per unit. */
export function revenuePreview(flowKgPerHour: number | null, price: string, unit: string, days: string, hours: string): number | null {
  const p = Number(price),
    perKg = PER_KG[unit];
  if (flowKgPerHour === null || price === '' || !Number.isFinite(p) || perKg === undefined) return null;
  return flowKgPerHour * (Number(days) || 0) * (Number(hours) || 0) * perKg * p;
}

export function RevenueSetup({ props }: { props: StageProps }) {
  const { hook } = props;
  const state = hook.state;
  const report = studyReport(state);
  const streams = useMemo(() => streamsOf(report), [report]);
  const config = obj(obj(state?.plan).operating_economics);
  const studyDate = text(obj(obj(state?.plan).cost_translation).target_period);
  const saved = list(config.sales);
  const [savedSignature, setSavedSignature] = useState<string | null>(null);
  const [sales, setSales] = useState<Sale[]>(() => saved.length
    ? saved.map(s => ({name:text(s.name),stream_key:text(s.stream_key),component:text(s.component),unit_price:text(s.unit_price),quantity_unit:text(s.quantity_unit)||'kg'}))
    : [{name:'',stream_key:'',component:'',unit_price:'',quantity_unit:'kg'}]),
    [currency, setCurrency] = useState('USD'),
    [days, setDays] = useState('330'),
    [hours, setHours] = useState('24'),
    [result, setResult] = useState<Row | null>(null);
  const signature = revenueDraftSignature(sales, currency, days, hours);
  const currentSignature = useRef(signature);
  currentSignature.current = signature;
  const notifyDirty = props.setRevenueDirty;
  const dirty = savedSignature !== null && signature !== savedSignature;
  useEffect(() => {
    notifyDirty?.(dirty);
  }, [dirty, notifyDirty]);
  useEffect(() => () => notifyDirty?.(false), [notifyDirty]);

  useEffect(() => {
    const initialSales = saved.length
        ? saved.map((s) => ({
            name: text(s.name),
            stream_key: text(s.stream_key),
            component: text(s.component),
            unit_price: text(s.unit_price),
            quantity_unit: text(s.quantity_unit) || 'kg',
          }))
        : [{ name: '', stream_key: '', component: '', unit_price: '', quantity_unit: 'kg' }];
    const initialCurrency = text(obj(config.price_basis).currency) || 'USD';
    const initialDays = text(obj(config.operating).days_per_year) || '330';
    const initialHours = text(obj(config.operating).hours_per_day) || '24';
    setSales(initialSales);
    setCurrency(initialCurrency);
    setDays(initialDays);
    setHours(initialHours);
    setSavedSignature(revenueDraftSignature(initialSales, initialCurrency, initialDays, initialHours));
    setResult(null);
    // Background work changes revision frequently. Never erase a revenue draft
    // while the user is typing; reset only when opening another study.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state?.id]);

  if (!state || !streams.length) return null;
  const approved = Boolean(state.revenue_approval);
  const change = (i: number, patch: Partial<Sale>) => setSales(sales.map((s, j) => (j === i ? { ...s, ...patch } : s)));
  const ready = sales.length > 0 && sales.every((s) => s.stream_key);

  async function save() {
    const submittedSignature = signature;
    await hook.action(async () => {
      const latest = await api<Row>('assessments/' + hook.id);
      const out = await api<Row>(
        `assessments/${hook.id}/revenue-setup`,
        post({
          revision: latest.revision,
          currency,
          price_period: studyDate || null,
          days_per_year: Number(days) || null,
          hours_per_day: Number(hours) || null,
          sales: sales.map((s) => {
            const stream = streams.find((x) => x.key === s.stream_key);
            return {
              name: s.name.trim() || s.component || stream?.label || stream?.tag || 'Product',
              stream_key: s.stream_key,
              component: s.component || null,
              unit_price: s.unit_price === '' ? null : Number(s.unit_price),
              quantity_unit: s.quantity_unit,
            };
          }),
        }),
      );
      setResult(out);
      // A validated queued save is accepted too. Failed requests never reach
      // here; changes typed while saving remain dirty against this snapshot.
      setSavedSignature(submittedSignature);
      if (currentSignature.current === submittedSignature) notifyDirty?.(false);
      hook.reload();
    });
  }

  return (
    <section className="gf-revenue-setup fv-revenue-simple" aria-labelledby="gf-rev-h">
      <header className="fv-revenue-head">
        <div><span className="fv-revenue-eyebrow">REVENUE SETUP</span><h2 id="gf-rev-h">Product Sales</h2><p>How the project makes money</p></div>
        <div className="fv-revenue-head-actions">
          <details className="fv-revenue-help"><summary aria-label="About product revenue">?</summary><p>Select a material stream from your workbook and enter its selling price. The backend calculates the official revenue after saving.</p></details>
          <button type="button" className="fv-revenue-secondary" onClick={() => props.go('revenue')}>Other revenue methods ↗</button>
        </div>
      </header>
      <div className="fv-revenue-content">
        <div className="fv-revenue-list">
          {sales.map((s,i)=>{
            const stream=streams.find(x=>x.key===s.stream_key);
            const flow=s.component?(stream?.components.find(x=>x.name===s.component)?.flow??null):(stream?.total??null);
            const preview=revenuePreview(flow,s.unit_price,s.quantity_unit,days,hours);
            return <div className="fv-revenue-product" key={i}>
              <div className="fv-revenue-product-head"><strong>Product {i+1}</strong>{sales.length>1&&<button type="button" className="fv-revenue-remove" onClick={()=>setSales(sales.filter((_,j)=>j!==i))} aria-label={`Remove product ${i+1}`}>Remove</button>}</div>
              <div className="fv-revenue-fields">
                <label className="fv-revenue-field fv-revenue-field-stream"><span>Select product stream <span className="fv-revenue-required">*</span></span><select value={s.stream_key} required onChange={e=>change(i,{stream_key:e.target.value,component:''})}>
                  <option value="">Choose a stream…</option>
                  {streams.map(x=><option value={x.key} key={x.key}>{x.tag}{x.label?` · ${x.label.slice(0,50)}`:''}{x.total!==null?` · ${compact(x.total)} kg/h`:''}</option>)}
                </select></label>
                <label className="fv-revenue-field fv-revenue-field-component"><span>What is sold?</span><select value={s.component} disabled={!stream} onChange={e=>change(i,{component:e.target.value})}>
                  {(!stream||stream.total!==null)&&<option value="">Whole stream</option>}
                  {(stream?.components||[]).map(x=><option value={x.name} key={x.name}>{x.name} · {compact(x.flow)} kg/h</option>)}
                </select></label>
                <label className="fv-revenue-field fv-revenue-field-name"><span>Product name <small>Optional</small></span><input value={s.name} placeholder={s.component||stream?.label||'Product name'} onChange={e=>change(i,{name:e.target.value})}/></label>
                <label className="fv-revenue-field fv-revenue-field-price"><span>Price per unit ({currency})</span><input type="number" min="0" step="any" inputMode="decimal" value={s.unit_price} placeholder="Enter price" onChange={e=>change(i,{unit_price:e.target.value})}/></label>
                <label className="fv-revenue-field fv-revenue-field-unit"><span>Unit</span><select value={s.quantity_unit} onChange={e=>change(i,{quantity_unit:e.target.value})}>{UNITS.map(u=><option key={u}>{u}</option>)}</select></label>
              </div>
              {preview!==null&&<p className="fv-revenue-preview">Estimated annual sales <strong>≈ {compact(preview)} {currency}/year</strong><span>Illustrative only</span></p>}
            </div>;
          })}
          <div className="fv-revenue-add"><button className="fv-revenue-add-button" type="button" onClick={()=>setSales([...sales,{name:'',stream_key:'',component:'',unit_price:'',quantity_unit:'kg'}])}>+ Add another product</button><span>{streams.length} eligible workbook streams</span></div>
        </div>
        <details className="fv-revenue-operating">
          <summary><span>Operating assumptions</span><span>{currency} · {days} days/year · {hours} hours/day <span aria-hidden="true">⌄</span></span></summary>
          <div className="fv-revenue-operating-fields">
            <label className="fv-revenue-field"><span>Currency</span><input maxLength={3} value={currency} onChange={e=>setCurrency(e.target.value.toUpperCase())}/></label>
            <label className="fv-revenue-field"><span>Operating days/year</span><input type="number" min="1" max="366" value={days} onChange={e=>setDays(e.target.value)}/></label>
            <label className="fv-revenue-field"><span>Hours/day</span><input type="number" min="1" max="24" value={hours} onChange={e=>setHours(e.target.value)}/></label>
          </div>
        </details>
        <div className="fv-revenue-footer">
          <span className={dirty?'fv-revenue-warning':approved?'fv-revenue-ready':'fv-revenue-muted'} role="status">{dirty?'Unsaved changes':approved?'✓ Revenue approved':saved.length?'Saved · awaiting approval':'Choose a stream to get started'}</span>
          <button type="button" className="fv-revenue-save" disabled={!ready||hook.busy} aria-busy={hook.busy} onClick={()=>void save()}>{hook.busy?'Saving…':'Save revenue'}</button>
        </div>
        {result&&text(result.message)&&<p role="status" className="fv-revenue-message">{text(result.message)}</p>}
        {result&&list(result.questions).length>0&&<details className="fv-revenue-questions"><summary>{list(result.questions).length} items to review</summary><ul>{list(result.questions).map((q,i)=><li key={i}>{String(q)}</li>)}</ul></details>}
      </div>
    </section>
  );
}
