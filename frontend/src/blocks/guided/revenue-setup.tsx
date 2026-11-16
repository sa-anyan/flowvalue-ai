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
  const [expanded, setExpanded] = useState(0);
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
    setExpanded(0);
    // Background work changes revision frequently. Never erase a revenue draft
    // while the user is typing; reset only when opening another study.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state?.id]);

  if (!state || !streams.length) return null;
  const approved = Boolean(state.revenue_approval);
  const change = (i: number, patch: Partial<Sale>) => setSales((current) => current.map((s, j) => (j === i ? { ...s, ...patch } : s)));
  const ready = sales.length > 0 && sales.every((s) => { const stream = streams.find((x) => x.key === s.stream_key); return Boolean(stream && (stream.total !== null || s.component)); });

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

  const configured = sales.filter((s) => s.stream_key).length;
  const priced = sales.filter((s) => s.stream_key && s.unit_price !== '' && Number.isFinite(Number(s.unit_price))).length;

  return (
    <section className="fv-entry-sales" aria-labelledby="fv-entry-sales-title">
      <div className="fv-sales-intro">
        <div>
          <span className="fv-sales-kicker">ENTRY · PRODUCT SALES</span>
          <h2 id="fv-entry-sales-title">What will this project sell?</h2>
          <p>Pick a material stream, enter a price and save. You can refine the details later.</p>
        </div>
        <button type="button" className="fv-sales-text-button" onClick={() => props.go('revenue')}>
          Other revenue methods <span aria-hidden="true">↗</span>
        </button>
      </div>

      <div className="fv-sales-toolbar" role="region" aria-label="Product sales actions">
        <div className="fv-sales-toolbar-status" role="status">
          <strong>{configured} of {sales.length} streams selected</strong>
          <span aria-hidden="true">·</span>
          <span>{dirty ? 'Unsaved changes' : approved ? 'Revenue approved' : saved.length ? 'Saved, awaiting approval' : priced ? 'Ready to save' : 'Set up your first product'}</span>
        </div>
        <button type="button" className="fv-sales-save" disabled={!ready || hook.busy} aria-busy={hook.busy} onClick={() => void save()}>
          {hook.busy ? 'Saving…' : 'Save revenue'}
        </button>
      </div>

      <div className="fv-sales-products">
        {sales.map((s, i) => {
          const stream = streams.find((x) => x.key === s.stream_key);
          const chosenFlow = s.component ? (stream?.components.find((x) => x.name === s.component)?.flow ?? null) : (stream?.total ?? null);
          const preview = revenuePreview(chosenFlow, s.unit_price, s.quantity_unit, days, hours);
          const isOpen = expanded === i;
          const productName = s.name.trim() || s.component || stream?.label || stream?.tag || 'Choose a product';
          return (
            <article className="fv-sales-product" key={i} aria-label={'Product ' + (i + 1)}>
              <div className="fv-sales-product-head">
                <button type="button" aria-expanded={isOpen} aria-controls={'fv-sales-product-' + i} onClick={() => setExpanded(isOpen ? -1 : i)}>
                  <span className="fv-sales-index">{i + 1}</span>
                  <span className="fv-sales-product-title">
                    <strong>{productName}</strong>
                    <small>{!stream ? 'Choose a stream to begin' : preview === null ? 'Price or supported flow pending' : 'Annual sales preview available'}</small>
                  </span>
                  <span className="fv-sales-chevron" aria-hidden="true">{isOpen ? '⌃' : '⌄'}</span>
                </button>
                {sales.length > 1 && (
                  <button type="button" className="fv-sales-remove" aria-label={'Remove product ' + (i + 1)} onClick={() => {
                    setSales((current) => current.filter((_, j) => j !== i));
                    setExpanded(0);
                  }}>Remove</button>
                )}
              </div>

              {isOpen && <div className="fv-sales-product-body" id={'fv-sales-product-' + i}>
                <div className="fv-sales-field-grid">
                  <label className="fv-sales-field">
                    <span>Material stream</span>
                    <select value={s.stream_key} onChange={(e) => {
                      const next = streams.find((x) => x.key === e.target.value);
                      change(i, { stream_key: e.target.value, component: next?.total === null ? (next.components[0]?.name || '') : '' });
                    }}>
                      <option value="">Select a stream…</option>
                      {streams.map((x) => (
                        <option key={x.key} value={x.key}>
                          {x.tag}{x.label ? ' · ' + x.label.slice(0, 65) : ''}{x.total !== null ? ' · ' + compact(x.total) + ' kg/h' : ''}
                        </option>
                      ))}
                    </select>
                  </label>
                  {stream && <label className="fv-sales-field">
                    <span>What is being sold?</span>
                    <select value={s.component} onChange={(e) => change(i, { component: e.target.value })}>
                      {stream.total !== null && <option value="">Whole stream</option>}
                      {stream.components.map((c) => <option key={c.name} value={c.name}>{c.name} · {compact(c.flow)} kg/h</option>)}
                    </select>
                  </label>}
                </div>

                <div className="fv-sales-price-grid">
                  <label className="fv-sales-field">
                    <span>Price per unit <small>({currency})</small></span>
                    <input type="number" min="0" step="any" inputMode="decimal" value={s.unit_price} placeholder="Enter selling price" onChange={(e) => change(i, { unit_price: e.target.value })} />
                  </label>
                  <label className="fv-sales-field">
                    <span>Unit</span>
                    <select value={s.quantity_unit} onChange={(e) => change(i, { quantity_unit: e.target.value })}>
                      {UNITS.map((u) => <option key={u} value={u}>{u}</option>)}
                    </select>
                  </label>
                </div>

                <div className="fv-sales-preview" aria-live="polite">
                  <span>Estimated annual sales</span>
                  <strong>{preview === null ? 'Not available yet' : '≈ ' + compact(preview) + ' ' + currency + '/year'}</strong>
                  <small>{preview === null ? 'Enter a price and a supported mass-based unit for a preview.' : 'Indicative only. The saved Python model produces the authoritative result.'}</small>
                </div>

                <details className="fv-sales-extra">
                  <summary>Optional product name</summary>
                  <label className="fv-sales-field">
                    <span>Name in the report</span>
                    <input value={s.name} placeholder={s.component || stream?.label || 'e.g. Bio-methanol'} onChange={(e) => change(i, { name: e.target.value })} />
                  </label>
                </details>
              </div>}
            </article>
          );
        })}
      </div>

      <button type="button" className="fv-sales-add" onClick={() => {
        setExpanded(sales.length);
        setSales((current) => [...current, { name: '', stream_key: '', component: '', unit_price: '', quantity_unit: 'kg' }]);
      }}>
        <span aria-hidden="true">＋</span> Add another product
      </button>

      <details className="fv-sales-basis">
        <summary><span>Operating basis</span><small>{currency} · {days} days/year · {hours} hours/day</small></summary>
        <div className="fv-sales-basis-fields">
          <label className="fv-sales-field"><span>Currency</span><input maxLength={3} value={currency} onChange={(e) => setCurrency(e.target.value.toUpperCase())} /></label>
          <label className="fv-sales-field"><span>Days per year</span><input type="number" min="1" max="366" value={days} onChange={(e) => setDays(e.target.value)} /></label>
          <label className="fv-sales-field"><span>Hours per day</span><input type="number" min="1" max="24" value={hours} onChange={(e) => setHours(e.target.value)} /></label>
        </div>
        <p>Operating time affects annual revenue. Change these only if your project's basis differs.</p>
      </details>

      {result && text(result.message) && <p className="fv-sales-result" role="status">{text(result.message)}</p>}
      {result && list(result.questions).length > 0 && <details className="fv-sales-review">
        <summary>{list(result.questions).length} revenue questions to review</summary>
        <ul>{list(result.questions).map((q, i) => <li key={i}>{String(q)}</li>)}</ul>
      </details>}
    </section>
  );
}
