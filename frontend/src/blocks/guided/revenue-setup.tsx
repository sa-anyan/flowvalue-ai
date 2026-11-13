'use client';
import { useEffect, useMemo, useState } from 'react';
import { compact, list, obj, text, type Row } from '@/lib/guided-flow';
import { api, post } from './use-assessment';
import type { StageProps } from './flow';

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
  const report = obj(state?.scoped_report || state?.effective_report || obj(state?.parsed).report);
  const streams = useMemo(() => streamsOf(report), [report]);
  const config = obj(obj(state?.plan).operating_economics);
  const studyDate = text(obj(obj(state?.plan).cost_translation).target_period);
  const saved = list(config.sales);
  const [sales, setSales] = useState<Sale[]>([]),
    [currency, setCurrency] = useState('USD'),
    [days, setDays] = useState('330'),
    [hours, setHours] = useState('24'),
    [result, setResult] = useState<Row | null>(null);

  useEffect(() => {
    setSales(
      saved.length
        ? saved.map((s) => ({
            name: text(s.name),
            stream_key: text(s.stream_key),
            component: text(s.component),
            unit_price: text(s.unit_price),
            quantity_unit: text(s.quantity_unit) || 'kg',
          }))
        : [{ name: '', stream_key: '', component: '', unit_price: '', quantity_unit: 'kg' }],
    );
    setCurrency(text(obj(config.price_basis).currency) || 'USD');
    setDays(text(obj(config.operating).days_per_year) || '330');
    setHours(text(obj(config.operating).hours_per_day) || '24');
    setResult(null);
    // Reset only when another study or a new saved revision arrives.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state?.id, state?.revision]);

  if (!state || !streams.length) return null;
  const approved = Boolean(state.revenue_approval);
  const change = (i: number, patch: Partial<Sale>) => setSales(sales.map((s, j) => (j === i ? { ...s, ...patch } : s)));
  const ready = sales.length > 0 && sales.every((s) => s.stream_key);

  async function save() {
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
      hook.reload();
    });
  }

  return (
    <section className="gf-revenue-setup" aria-labelledby="gf-rev-h">
      <span className="gf-kicker">HOW DOES THIS PROJECT EARN MONEY?</span>
      <h3 id="gf-rev-h">Product sales</h3>
      <p className="gf-muted">
        Choose what is sold from your M&amp;E streams. Python calculates quantity × price × operating hours; revenue then runs in the background with CAPEX and OPEX.
      </p>
      {sales.map((s, i) => {
        const stream = streams.find((x) => x.key === s.stream_key);
        return (
          <div key={i} className="gf-rev-row">
            <label className="gf-field">
              <span>Sold stream</span>
              <select value={s.stream_key} onChange={(e) => change(i, { stream_key: e.target.value, component: '' })}>
                <option value="">Choose a stream…</option>
                {streams.map((x) => (
                  <option key={x.key} value={x.key}>
                    {x.tag}
                    {x.label ? ` · ${x.label.slice(0, 50)}` : ''}
                    {x.total !== null ? ` · ${compact(x.total)} kg/h` : ''}
                  </option>
                ))}
              </select>
            </label>
            <label className="gf-field">
              <span>What is sold</span>
              <select value={s.component} onChange={(e) => change(i, { component: e.target.value })} disabled={!stream}>
                {(!stream || stream.total !== null) && <option value="">Whole stream</option>}
                {(stream?.components || []).map((c) => (
                  <option key={c.name} value={c.name}>
                    {c.name} · {compact(c.flow)} kg/h
                  </option>
                ))}
              </select>
            </label>
            <label className="gf-field">
              <span>Product name</span>
              <input value={s.name} placeholder={s.component || 'e.g. Protein'} onChange={(e) => change(i, { name: e.target.value })} />
            </label>
            <label className="gf-field">
              <span>Price per unit ({currency})</span>
              <input type="number" min="0" step="any" inputMode="decimal" value={s.unit_price} placeholder="e.g. 17" onChange={(e) => change(i, { unit_price: e.target.value })} />
            </label>
            <label className="gf-field">
              <span>Unit</span>
              <select value={s.quantity_unit} onChange={(e) => change(i, { quantity_unit: e.target.value })}>
                {UNITS.map((u) => (
                  <option key={u}>{u}</option>
                ))}
              </select>
            </label>
            {(() => {
              const flow = s.component ? (stream?.components.find((c) => c.name === s.component)?.flow ?? null) : (stream?.total ?? null);
              const year = revenuePreview(flow, s.unit_price, s.quantity_unit, days, hours);
              return year === null ? null : (
                <small className="gf-muted gf-rev-preview">
                  ≈ {compact(year)} {currency}/year ({compact(flow)} kg/h × {Number(days) * Number(hours)} h × {s.unit_price} per {s.quantity_unit})
                </small>
              );
            })()}
            {sales.length > 1 && (
              <button type="button" className="gf-link" onClick={() => setSales(sales.filter((_, j) => j !== i))}>
                Remove
              </button>
            )}
          </div>
        );
      })}
      <button
        type="button"
        className="gf-link"
        onClick={() => setSales([...sales, { name: '', stream_key: '', component: '', unit_price: '', quantity_unit: 'kg' }])}
      >
        + Add another product
      </button>
      <div className="gf-grid-3">
        <label className="gf-field">
          <span>Currency</span>
          <input maxLength={3} value={currency} onChange={(e) => setCurrency(e.target.value.toUpperCase())} />
        </label>
        <label className="gf-field">
          <span>Operating days / year</span>
          <input type="number" min="1" max="366" value={days} onChange={(e) => setDays(e.target.value)} />
        </label>
        <label className="gf-field">
          <span>Hours / day</span>
          <input type="number" min="1" max="24" value={hours} onChange={(e) => setHours(e.target.value)} />
        </label>
      </div>
      <div className="gf-inline-actions">
        <span className={approved ? 'gf-ok' : 'gf-muted'}>
          {approved ? '✓ Revenue set and approved' : saved.length ? 'Not approved yet' : 'Prices dated at the study cost date'}
        </span>
        <button type="button" className="gf-primary" disabled={!ready || hook.busy || Boolean(state.running)} onClick={() => void save()}>
          Save revenue
        </button>
      </div>
      {result && list(result.questions).length > 0 && (
        <ul className="gf-issue-list">
          {(result.questions as unknown[]).map((q, i) => (
            <li key={i}>{String(q)}</li>
          ))}
        </ul>
      )}
    </section>
  );
}
