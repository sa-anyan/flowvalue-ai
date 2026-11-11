'use client';
import { useEffect, useState } from 'react';
import { strings, compact, list, money, num, obj, percent, text, words, type Row } from '@/lib/guided-flow';
import { api, post } from './use-assessment';
import { Issues, OriginChip, Panel, RunBar, StageHeading, type StageProps } from './flow';

const groups = [
  ['materials', 'Raw materials', ['unit_price', 'annual_quantity_assumption']],
  ['energy', 'Energy & utilities', ['power_kw', 'load_fraction', 'efficiency', 'tariff_per_kwh']],
  ['labour', 'Labour', ['headcount_fte', 'annual_base_salary', 'allocation_fraction']],
  ['additional_expenses', 'Additional expenses', ['amount', 'annual_amount', 'unit_price', 'quantity']],
] as const;
const hidden = new Set(['id', 'stream_key', 'equipment_key', 'source_key', 'component', 'property', 'price_basis']);

/** Value origin for an OPEX input, read from its own recorded source/status fields. */
export function opexOrigin(item: Row): string {
  const s = `${text(item.status)} ${text(item.source)} ${text(item.origin)} ${text(item.uncertainty)}`.toLowerCase();
  if (/accepted by user|user/.test(`${s} ${text(item.rationale).toLowerCase()}`)) return 'Your input';
  if (/llm|ai |ai-|estimate|propos/.test(s)) return 'AI · provisional';
  if (/synthetic|test/.test(s)) return 'Test assumption';
  return 'Saved assumption';
}

/**
 * OPEX playground: the same pattern as CAPEX. Each operating cost shows its
 * Python amount and the inputs that drive it; edit, keep, remove or add items,
 * then recalculate.
 */
export function OpexPlayground(props: StageProps) {
  const { hook, operating } = props;
  const state = hook.state;
  const stage = obj(obj(obj(state?.results).stages).opex);
  const result = obj(stage.result);
  const config = operating.value;
  const [factors, setFactors] = useState<Row[]>([]),
    [research, setResearch] = useState(''),
    [before, setBefore] = useState<Record<string, string> | null>(null);
  useEffect(() => {
    void api<Row[]>(`catalogue/opex-factors?model_id=${encodeURIComponent(text(config.methodology || 'garrett'))}`)
      .then((f) => setFactors(Array.isArray(f) ? f : []))
      .catch(() => setFactors([]));
  }, [config.methodology]);
  const lines = list(result.first_year_lines);
  const lineFor = (id: string) => lines.find((l) => text(l.id).split(':').slice(1).join(':') === id || text(l.id) === id);
  const firstYear = Object.keys(obj(obj(result.operating_detail).years))[0];
  const pending = list(obj(obj(obj(result.operating_detail).years)[firstYear]).pending_items).map((p) => text(p.reason || p.message || p.id || JSON.stringify(p)));
  const basis = obj(config.price_basis),
    schedule = obj(config.operating);
  const set = (patch: Row) => operating.set({ ...config, ...patch });
  const setItem = (root: string, index: number, patch: Row) => set({ [root]: list(config[root]).map((item, i) => (i === index ? { ...item, ...patch } : item)) });
  async function recalculate() {
    setBefore({ total: compact(result.first_year_cash_opex ?? result.known_cash_opex_subtotal), ...Object.fromEntries(lines.map((l) => [text(l.id), money(l.amount, '—')])) });
    await hook.action(async () => {
      await operating.save('User edited operating costs in the OPEX playground');
      await hook.runStage('opex');
    });
  }
  const shift = (id: string, amount: unknown) => (before && before[id] !== undefined && before[id] !== money(amount, '—') ? ` · was ${before[id]}` : '');
  return (
    <div className="gf-play">
      <StageHeading kicker="STAGE 04 · OPEX" title="OPEX playground">
        Operating costs with the inputs behind each one. Your edits are saved with a rationale and Python recalculates. Missing inputs stay missing, never zero.
      </StageHeading>
      <section className="gf-card-block" aria-labelledby="gf-opex-basis">
        <h2 id="gf-opex-basis">Shared operating basis</h2>
        <div className="gf-grid-4">
          <label className="gf-field">
            <span>Price currency {!basis.currency && <em className="gf-required">Required</em>}</span>
            <input value={text(basis.currency)} maxLength={3} onChange={(e) => set({ price_basis: { ...basis, currency: e.target.value.toUpperCase() } })} />
          </label>
          <label className="gf-field">
            <span>Price period {!basis.price_period && <em className="gf-required">Required</em>}</span>
            <input value={text(basis.price_period)} placeholder="e.g. 2026" onChange={(e) => set({ price_basis: { ...basis, price_period: e.target.value } })} />
          </label>
          <label className="gf-field">
            <span>Operating days / year {!schedule.days_per_year && <em className="gf-required">Required</em>}</span>
            <input type="number" min="1" max="366" value={text(schedule.days_per_year)} onChange={(e) => set({ operating: { ...schedule, days_per_year: e.target.value === '' ? null : Number(e.target.value) } })} />
          </label>
          <label className="gf-field">
            <span>Hours / day {!schedule.hours_per_day && <em className="gf-required">Required</em>}</span>
            <input type="number" min="0.1" max="24" step="any" value={text(schedule.hours_per_day)} onChange={(e) => set({ operating: { ...schedule, hours_per_day: e.target.value === '' ? null : Number(e.target.value) } })} />
          </label>
        </div>
        <small className="gf-muted">Revenue uses the same calendar, so one change applies to both.</small>
      </section>
      <div className="gf-kpis">
        <div className="gf-kpi-hero">
          <small>{result.complete === false ? 'Known cash OPEX subtotal · year 1' : 'Annual cash OPEX · year 1'}</small>
          <strong>{num(result.first_year_cash_opex ?? result.known_cash_opex_subtotal) === null ? 'Pending' : compact(result.first_year_cash_opex ?? result.known_cash_opex_subtotal)}</strong>
          <span>
            {text(result.currency)} {text(result.price_period)}
            {before && before.total !== compact(result.first_year_cash_opex ?? result.known_cash_opex_subtotal) ? ` · was ${before.total}` : ''}
          </span>
        </div>
        <div>
          <small>Fixed cash costs</small>
          <strong>{compact(result.first_year_fixed_opex, 'Pending')}</strong>
          <span>{text(result.currency)}</span>
        </div>
        <div>
          <small>Variable cash costs</small>
          <strong>{compact(result.first_year_variable_opex, 'Pending')}</strong>
          <span>{text(result.currency)}</span>
        </div>
      </div>
      {!stage.result && <p className="gf-note">OPEX has not been calculated yet.</p>}
      <Issues items={[...strings(stage.issues), ...strings(obj(obj(result.years)[firstYear]).issues), ...pending]} />

      {groups.map(([root, title, preferred]) => {
        const items = list(config[root]);
        return (
          <section key={root} className="gf-card-block" aria-label={title}>
            <div className="gf-block-head">
              <h2>{title}</h2>
              <button
                type="button"
                className="gf-secondary"
                disabled={!items.length}
                title={items.length ? undefined : 'Add the first item in the advanced workspace'}
                onClick={() => set({ [root]: [...items, blank(items[0])] })}
              >
                + Add item
              </button>
            </div>
            {!items.length && <p className="gf-muted">No {title.toLowerCase()} recorded.</p>}
            <ul className="gf-lines">
              {items.map((item, index) => {
                const line = lineFor(text(item.id));
                const origin = opexOrigin(item);
                const fields = Object.entries(item).filter(([k, v]) => !hidden.has(k) && (typeof v === 'number' || (v === null && (preferred as readonly string[]).includes(k))));
                return (
                  <li key={text(item.id) || index} className="gf-line">
                    <div className="gf-line-main">
                      <div>
                        <input className="gf-inline-name" aria-label={`${title} item name`} value={text(item.name || item.role || item.id)} onChange={(e) => setItem(root, index, { [item.role !== undefined ? 'role' : 'name']: e.target.value })} />
                        <OriginChip origin={origin} />
                        <small>{text(item.rationale)}</small>
                      </div>
                      <div className="gf-line-value">
                        <strong>{line ? money(line.amount) : 'Not calculated'}</strong>
                        <small>
                          {line ? `${text(line.quantity) ? `${text(line.quantity)} ${text(line.quantity_unit)} × ${text(line.rate)}/${text(line.rate_unit)}` : words(line.method)}` : 'Recalculate to see its amount'}
                          {line ? shift(text(line.id), line.amount) : ''}
                        </small>
                      </div>
                    </div>
                    <div className="gf-fields">
                      {fields.map(([k, v]) => (
                        <label key={k} className="gf-field gf-field-sm">
                          <span>{words(k)}</span>
                          <input type="number" step="any" value={v === null ? '' : String(v)} onChange={(e) => setItem(root, index, { [k]: e.target.value === '' ? null : Number(e.target.value) })} />
                        </label>
                      ))}
                    </div>
                    <div className="gf-line-actions">
                      <button
                        type="button"
                        className="gf-secondary"
                        disabled={origin === 'Your input'}
                        onClick={() => setItem(root, index, { rationale: `Accepted by user: ${text(item.rationale)}`.slice(0, 2000) })}
                      >
                        {origin === 'Your input' ? 'In use ✓' : 'Use'}
                      </button>
                      <button type="button" className="gf-secondary" onClick={() => setResearch(title)}>
                        Research with AI
                      </button>
                      <button type="button" className="gf-link" onClick={() => set({ [root]: items.filter((_, i) => i !== index) })}>
                        Remove
                      </button>
                    </div>
                  </li>
                );
              })}
            </ul>
          </section>
        );
      })}

      <section className="gf-card-block" aria-labelledby="gf-opex-factors">
        <h2 id="gf-opex-factors">Factor-based costs</h2>
        <ul className="gf-lines">
          {Object.entries(obj(config.garrett_factors)).map(([id, raw]) => {
            const entry = obj(raw),
              factor = factors.find((f) => f.id === id) || {},
              line = lineFor(id),
              min = num(factor.minimum),
              max = num(factor.maximum),
              value = num(entry.fraction);
            return (
              <li key={id} className="gf-line">
                <div className="gf-line-main">
                  <div>
                    <strong>{words(id)}</strong>
                    <OriginChip origin={opexOrigin(entry)} />
                    <small>{text(entry.rationale || factor.applicability)}</small>
                  </div>
                  <div className="gf-line-value">
                    <strong>{line ? money(line.amount) : 'Not calculated'}</strong>
                    <small>
                      {value === null ? 'No factor' : `${percent(value)} of ${words(line?.calculation_base || factor.base || 'base')}`}
                      {line ? shift(text(line.id), line.amount) : ''}
                    </small>
                  </div>
                </div>
                {value !== null && min !== null && max !== null && (value < min || value > max) && (
                  <p className="gf-warn">
                    Saved factor {percent(value)} is outside the published range ({percent(min)} – {percent(max)}). Moving the slider replaces it with an in-range value.
                  </p>
                )}
                {min !== null && max !== null && max > min ? (
                  <div className="gf-slider">
                    <label htmlFor={`gf-o-${id}`}>
                      Factor within the published range ({percent(min)} – {percent(max)})
                    </label>
                    <div>
                      <input
                        id={`gf-o-${id}`}
                        type="range"
                        min={min}
                        max={max}
                        step={Math.max((max - min) / 100, 0.0005)}
                        value={value ?? min}
                        onChange={(e) => set({ garrett_factors: { ...obj(config.garrett_factors), [id]: { ...entry, fraction: e.target.value, rationale: 'User-selected factor within the published range' } } })}
                      />
                      <span>{percent(value)}</span>
                    </div>
                  </div>
                ) : null}
              </li>
            );
          })}
        </ul>
        {!Object.keys(obj(config.garrett_factors)).length && <p className="gf-muted">No factor-based costs selected.</p>}
      </section>

      <div className="gf-inline-actions">
        <span className="gf-muted">{operating.dirty ? 'Unsaved OPEX changes.' : 'Saved.'}</span>
        <button type="button" className="gf-secondary" disabled={!operating.dirty || hook.busy} onClick={() => operating.reset()}>
          Discard
        </button>
        <button type="button" className="gf-primary" disabled={hook.busy || Boolean(state?.running)} onClick={() => void recalculate()}>
          Save & recalculate
        </button>
      </div>
      <RunBar
        label="Run Revenue"
        busy={hook.busy}
        disabled={Boolean(state?.running)}
        back={{ label: 'CAPEX', onClick: () => props.go('capex') }}
        status={<strong>{operating.dirty ? 'Your OPEX edits will be saved first' : 'Operating costs ready'}</strong>}
        note="Runs CAPEX, Revenue and OPEX together with Python, then opens Revenue."
        onRun={() => void props.advance(() => operating.save('User reviewed operating costs in the OPEX playground'))}
      />
      {research && (
        <Panel title={`Research ${research.toLowerCase()} with AI`} kicker="AI · PROVISIONAL" onClose={() => setResearch('')}>
          <p>
            Per-item OPEX research is not available from the backend yet. FlowValue can prepare <strong>all</strong> OPEX assumptions with the AI analyst. A version is saved
            first, proposals are labelled provisional, and inputs you have saved are not replaced.
          </p>
          {!hook.aiEnabled && <p className="gf-warn">AI is switched off on this server.</p>}
          <button
            type="button"
            className="gf-primary"
            disabled={!hook.aiEnabled || hook.busy || Boolean(state?.running) || operating.dirty}
            onClick={() => {
              setResearch('');
              void hook.action(() => api(`assessments/${hook.id}/stages/opex/prepare`, post({})));
            }}
          >
            I agree — prepare OPEX with AI (usage charges apply)
          </button>
        </Panel>
      )}
    </div>
  );
}

/** A new item with the same shape as an existing one: numbers cleared, never guessed. */
function blank(template: Row | undefined): Row {
  const id = 'user-' + (typeof crypto !== 'undefined' && 'randomUUID' in crypto ? crypto.randomUUID().slice(0, 8) : String(Date.now()));
  return Object.fromEntries(
    Object.entries(template || {}).map(([k, v]) => [
      k,
      k === 'id' ? id : k === 'name' || k === 'role' ? 'New item' : k === 'rationale' ? 'User-added item in the OPEX playground' : typeof v === 'number' ? null : k.endsWith('_key') ? null : v,
    ]),
  );
}
