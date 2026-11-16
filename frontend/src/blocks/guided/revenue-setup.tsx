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

  const configured = sales.filter(s => s.stream_key).length;
  const priced = sales.filter(s => s.stream_key && s.unit_price !== '' && Number.isFinite(Number(s.unit_price))).length;
  return (
    <section className="fv-entry-sales" aria-labelledby="fv-entry-sales-title">
      <div className="fv-sales-hero">
        <div className="fv-sales-hero-copy">
          <span className="fv-sales-eyebrow"><span aria-hidden="true" className="fv-sales-pulse" /> COMMERCIAL SETUP <span className="fv-sales-separator">/</span> ENTRY</span>
          <h2 id="fv-entry-sales-title">Product <em>Sales</em><span className="fv-sales-hero-mark" aria-hidden="true">↗</span></h2>
          <p>How the project makes money</p>
          <div className="fv-sales-hero-actions">
            <a className="fv-sales-hero-jump" href="#fv-sales-configure">Configure streams <span aria-hidden="true">↘</span></a>
            <button type="button" className="fv-sales-hero-secondary" onClick={() => props.go('revenue')}>Other revenue methods <span aria-hidden="true">↗</span></button>
          </div>
        </div>
        <div className="fv-sales-hero-art" aria-hidden="true"><span className="fv-sales-orbit fv-sales-orbit-one"/><span className="fv-sales-orbit fv-sales-orbit-two"/><span className="fv-sales-orbit fv-sales-orbit-three"/><span className="fv-sales-art-core">FV<span>↗</span></span></div>
      </div>
      <div className="fv-sales-layout" id="fv-sales-configure">
        <div className="fv-sales-editor">
          <div className="fv-sales-section-heading">
            <div><span className="fv-sales-step">01 / REVENUE INPUTS</span><h3>Choose what you sell</h3></div>
            <details className="fv-sales-help"><summary aria-label="About product streams">?</summary><p>Choose a material stream extracted from your mass and energy balance. For a product within that stream, select its component. Only workbook streams with reported positive flows appear.</p></details>
          </div>
          <div className="fv-sales-items">
            {sales.map((s,i)=>{
              const stream = streams.find(x=>x.key===s.stream_key);
              const chosenFlow=s.component?(stream?.components.find(x=>x.name===s.component)?.flow??null):(stream?.total??null);
              const preview=revenuePreview(chosenFlow,s.unit_price,s.quantity_unit,days,hours);
              return <article className="fv-sales-product" key={i} aria-label={`Product ${i+1}`}>
                <div className="fv-sales-product-top">
                  <div className="fv-sales-product-ident"><span className="fv-sales-product-number">{String(i+1).padStart(2,'0')}</span><div><h4>{s.name.trim()||s.component||stream?.label||stream?.tag||'New product'}</h4><span>{stream?'Stream '+stream.tag:'Select a workbook stream'}</span></div></div>
                  {sales.length>1&&<button className="fv-sales-remove" type="button" aria-label={`Remove product ${i+1}`} onClick={()=>setSales(sales.filter((_,j)=>i!==j))}>×</button>}
                </div>
                <div className="fv-sales-label-row"><span>Select product stream</span><small>{streams.length} available</small></div>
                <div className="fv-sales-stream-grid" role="group" aria-label={`Select stream for product ${i+1}`}>
                  {streams.map(x=><button type="button" key={x.key} className="fv-sales-stream" aria-pressed={s.stream_key===x.key} onClick={()=>change(i,{stream_key:x.key,component:''})} title={x.label||x.tag}>
                    <span className="fv-sales-stream-icon" aria-hidden="true">⌁</span>
                    <span className="fv-sales-stream-content"><strong>{x.tag}</strong><small>{x.label||'Material stream'}</small></span>
                    <span className="fv-sales-stream-right"><small>{x.total!==null?`${compact(x.total)} kg/h`:x.components.length+' components'}</small><span aria-hidden="true" className="fv-sales-stream-check">{s.stream_key===x.key?'✓':'+'}</span></span>
                  </button>)}
                </div>
                {stream&&<div className="fv-sales-components"><div className="fv-sales-label-row"><span>What is sold?</span><details className="fv-sales-help fv-sales-help-small"><summary aria-label="About components">?</summary><p>Sell the whole stream when its total flow is available, or choose a reported component. No quantity is invented.</p></details></div><div className="fv-sales-choice-row">
                  {stream.total!==null&&<button type="button" aria-pressed={!s.component} onClick={()=>change(i,{component:''})}>Whole stream</button>}
                  {stream.components.map(x=><button key={x.name} type="button" aria-pressed={s.component===x.name} onClick={()=>change(i,{component:x.name})}>{x.name} <small>{compact(x.flow)} kg/h</small></button>)}
                </div></div>}
                <div className="fv-sales-price-row">
                  <label className="fv-sales-field fv-sales-name"><span>Product name <small>Optional</small></span><input value={s.name} placeholder={s.component||stream?.label||'Name your product'} onChange={e=>change(i,{name:e.target.value})}/></label>
                  <label className="fv-sales-field fv-sales-price"><span>Price <small>/ unit</small></span><div className="fv-sales-price-input"><span>{currency}</span><input type="number" min="0" step="any" inputMode="decimal" value={s.unit_price} placeholder="0.00" onChange={e=>change(i,{unit_price:e.target.value})}/></div></label>
                  <label className="fv-sales-field fv-sales-unit"><span>Unit</span><select value={s.quantity_unit} onChange={e=>change(i,{quantity_unit:e.target.value})}>{UNITS.map(u=><option key={u}>{u}</option>)}</select></label>
                </div>
                <div className="fv-sales-product-foot"><span className="fv-sales-preview-label">ESTIMATED ANNUAL SALES <details className="fv-sales-help fv-sales-help-small"><summary aria-label="About sales preview">?</summary><p>Illustrative quantity × price × operating time only. Python calculates the authoritative result after you save. A preview is unavailable for volume-based units without a supported conversion.</p></details></span><strong>{preview===null?'Awaiting supported inputs':`≈ ${compact(preview)} ${currency}/yr`}</strong></div>
              </article>;
            })}
          </div>
          <div className="fv-sales-add-row">
            <button type="button" className="fv-sales-add-product" onClick={()=>setSales([...sales,{name:'',stream_key:'',component:'',unit_price:'',quantity_unit:'kg'}])}><span className="fv-sales-add-icon" aria-hidden="true">+</span><span><strong>Add another product</strong><small>From an available M&amp;E stream</small></span><span aria-hidden="true">↗</span></button>
            <button type="button" className="fv-sales-more-methods" onClick={()=>props.go('revenue')}>Explore other revenue methods ↗</button>
          </div>
        </div>
        <aside className="fv-sales-side" aria-label="Revenue setup summary">
          <div className="fv-sales-side-top"><span>YOUR SETUP</span><span className="fv-sales-side-dot" aria-hidden="true"/></div>
          <h3>Revenue snapshot<span aria-hidden="true">↗</span></h3>
          <p className="fv-sales-side-sub">Your commercial model at a glance.</p>
          <div className="fv-sales-stat-grid"><div><strong>{configured}<span> / {sales.length}</span></strong><small>Streams selected</small></div><div><strong>{priced}</strong><small>Prices entered</small></div></div>
          <div className="fv-sales-progress" role="progressbar" aria-label="Products with selected streams" aria-valuemin={0} aria-valuemax={sales.length} aria-valuenow={configured}><span style={{width:`${sales.length?configured/sales.length*100:0}%`}}/></div>
          <div className="fv-sales-side-list"><span className="fv-sales-side-label">IN THIS MODEL</span>{sales.map((s,i)=>{const stream=streams.find(x=>x.key===s.stream_key);return <div className="fv-sales-side-item" key={i}><span className="fv-sales-side-index">{i+1}</span><span>{s.name||s.component||stream?.label||stream?.tag||'Unassigned product'}</span><span className={s.stream_key?'fv-sales-state-ready':'fv-sales-state-pending'}>{s.stream_key?'✓':'—'}</span></div>})}</div>
          <details className="fv-sales-settings"><summary><span>⚙ Operating basis</span><span className="fv-sales-settings-meta">{currency} · {days} d/yr <span aria-hidden="true">⌄</span></span></summary><div className="fv-sales-settings-fields">
            <label className="fv-sales-field"><span>Currency</span><input maxLength={3} value={currency} onChange={e=>setCurrency(e.target.value.toUpperCase())}/></label>
            <label className="fv-sales-field"><span>Days / year</span><input type="number" min="1" max="366" value={days} onChange={e=>setDays(e.target.value)}/></label>
            <label className="fv-sales-field"><span>Hours / day</span><input type="number" min="1" max="24" value={hours} onChange={e=>setHours(e.target.value)}/></label>
          </div></details>
          <div className="fv-sales-save-area"><span role="status" className={dirty?'fv-sales-save-status fv-sales-unsaved':approved?'fv-sales-save-status fv-sales-approved':'fv-sales-save-status'}>{dirty?'● Unsaved edits':approved?'✓ Revenue approved':saved.length?'Saved · not approved':'Ready to configure'}</span>
            <button type="button" className="fv-sales-save" disabled={!ready||hook.busy} aria-busy={hook.busy} onClick={()=>void save()}>{hook.busy?<><span className="fv-sales-spinner" aria-hidden="true"/> Saving…</>:'Save revenue'}<span aria-hidden="true">↗</span></button>
          </div>
          {result&&text(result.message)&&<p className="fv-sales-result" role="status">{text(result.message)}</p>}
          {result&&list(result.questions).length>0&&<details className="fv-sales-review"><summary>{list(result.questions).length} items need review</summary><ul>{list(result.questions).map((q,i)=><li key={i}>{String(q)}</li>)}</ul></details>}
        </aside>
      </div>
    </section>
  );
}
