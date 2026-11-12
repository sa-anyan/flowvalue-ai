'use client';
import { useEffect, useMemo, useState } from 'react';
import { strings, capexLines, compact, list, money, num, obj, percent, text, words, type CapexLine, type Row } from '@/lib/guided-flow';
import { api, post } from './use-assessment';
import { Issues, OriginChip, Panel, RunBar, StageHeading, type StageProps } from './flow';

const basisFields = [
  { key: 'model_id', label: 'Method', options: [['garrett', 'Garrett factorial'], ['nottingham', 'Nottingham detailed']] },
  { key: 'process_type', label: 'Process class', options: [['solids', 'Solids'], ['mixed', 'Mixed solids / fluids'], ['fluids', 'Fluids']] },
  { key: 'delivery_basis', label: 'Equipment delivery', options: [['delivered', 'Delivered'], ['ex_works', 'Ex works']] },
  { key: 'factor_selection', label: 'Default factor choice', options: [['minimum', 'Range minimum'], ['midpoint', 'Range midpoint'], ['maximum', 'Range maximum'], ['selected', 'Individually selected']] },
] as const;

/**
 * CAPEX playground: each factor line shows where its value came from, and can
 * be kept ("Use"), tuned within its published range, overridden with an
 * evidenced amount, removed with a reason, or added back. Python recalculates.
 */
export function CapexPlayground(props: StageProps) {
  const { hook, capex } = props;
  const state = hook.state;
  const stage = obj(obj(obj(state?.results).stages).capex);
  const result = obj(stage.result);
  const config = capex.value;
  const [factors, setFactors] = useState<Row[]>([]),
    [editing, setEditing] = useState(''),
    [removing, setRemoving] = useState<{ id: string; reason: string } | null>(null),
    [research, setResearch] = useState<CapexLine | null>(null),
    [before, setBefore] = useState<Record<string, string> | null>(null);
  const model = text(config.model_id || 'garrett'),
    process = text(config.process_type || 'mixed');
  useEffect(() => {
    let alive = true;
    void api<Row[]>(`catalogue/capex-factors?model_id=${encodeURIComponent(model)}&process_type=${encodeURIComponent(process)}`)
      .then((f) => alive && setFactors(Array.isArray(f) ? f : []))
      .catch(() => alive && setFactors([]));
    return () => {
      alive = false;
    };
  }, [model, process]);
  const lines = useMemo(() => capexLines(result, config, factors, list(state?.assumption_register)), [result, config, factors, state?.assumption_register]);
  const present = new Set(lines.map((l) => l.id));
  const addable = factors.filter((f) => f.additive !== false && (!present.has(text(f.id)) || text(f.id) in obj(config.exclusions)));
  const currency = text(result.currency),
    period = text(result.period);
  const set = (patch: Row) => capex.set({ ...config, ...patch });
  const without = (key: string, id: string) => Object.fromEntries(Object.entries(obj(config[key])).filter(([k]) => k !== id));
  function useLine(line: CapexLine) {
    if (line.fraction === null) return;
    set({ selected_factors: { ...obj(config.selected_factors), [line.id]: line.fraction }, overrides: without('overrides', line.id) });
  }
  function selectFraction(line: CapexLine, value: number) {
    set({ selected_factors: { ...obj(config.selected_factors), [line.id]: value }, overrides: without('overrides', line.id) });
  }
  function overrideAmount(line: CapexLine, amount: number | null, rationale: string) {
    if (amount === null) return set({ overrides: without('overrides', line.id) });
    set({
      overrides: { ...obj(config.overrides), [line.id]: { amount, rationale, source: 'user assumption', price_basis: { currency: currency || 'USD', price_period: period || String(new Date().getFullYear()) } } },
      selected_factors: without('selected_factors', line.id),
    });
  }
  function reset(line: CapexLine) {
    set({ overrides: without('overrides', line.id), selected_factors: without('selected_factors', line.id) });
  }
  async function recalculate() {
    setBefore({ total: compact(result.total_capex, 'Incomplete'), ...Object.fromEntries(lines.map((l) => [l.id, money(l.amount, '—')])) });
    await hook.action(async () => {
      await capex.save('User edited CAPEX lines in the CAPEX playground');
      await hook.runStage('capex');
    });
  }
  const missing = basisFields.filter((f) => !config[f.key]);
  const groups = [
    ['Direct costs', lines.filter((l) => obj(factors.find((f) => f.id === l.id)).stage === 'direct')],
    ['Indirect costs', lines.filter((l) => obj(factors.find((f) => f.id === l.id)).stage === 'indirect')],
    ['Plant-level & working capital', lines.filter((l) => !['direct', 'indirect'].includes(text(obj(factors.find((f) => f.id === l.id)).stage)))],
  ] as const;
  return (
    <div className="gf-play">
      <StageHeading kicker="STAGE 03 · CAPEX" title="CAPEX playground">
        Every capital line, where its value came from, and what you can change. Python recalculates the totals; nothing here is computed in your browser.
      </StageHeading>
      <section className="gf-card-block" aria-labelledby="gf-capex-basis">
        <h2 id="gf-capex-basis">Estimate basis</h2>
        <div className="gf-grid-4">
          {basisFields.map((f) => (
            <label key={f.key} className="gf-field">
              <span>
                {f.label} {!config[f.key] && <em className="gf-required">Required</em>}
              </span>
              <select value={text(config[f.key])} onChange={(e) => set({ [f.key]: e.target.value || undefined })}>
                <option value="">Not chosen</option>
                {f.options.map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
          ))}
        </div>
      </section>
      <div className="gf-kpis">
        <div className="gf-kpi-hero">
          <small>Total capital investment</small>
          <strong>{num(result.total_capex) === null ? 'Incomplete' : compact(result.total_capex)}</strong>
          <span>
            {currency} {period}
            {before && before.total !== compact(result.total_capex, 'Incomplete') ? ` · was ${before.total}` : ''}
          </span>
        </div>
        {[
          ['Purchased equipment', result.purchased_equipment],
          ['Fixed capital', result.fixed_capital],
          ['Start-up', result.startup_expenses],
          ['Working capital', result.working_capital],
        ].map(([label, v]) => (
          <div key={String(label)}>
            <small>{String(label)}</small>
            <strong>{num(v) === null ? 'Pending' : compact(v)}</strong>
            <span>{currency}</span>
          </div>
        ))}
      </div>
      {!stage.result && <p className="gf-note">CAPEX has not been calculated yet. Choose the basis above, then “Save & recalculate”.</p>}
      <Issues items={[...strings(stage.issues), ...strings(result.issues), ...missing.map((f) => `${f.label} is required before CAPEX can be calculated.`)]} />

      {groups.map(([title, group]) =>
        group.length ? (
          <section key={title} className="gf-card-block" aria-label={title}>
            <h2>{title}</h2>
            <ul className="gf-lines">
              {group.map((line) => (
                <li key={line.id} className={`gf-line ${line.excluded ? 'gf-line-removed' : ''}`}>
                  <div className="gf-line-main">
                    <div>
                      <strong>{line.label}</strong>
                      <OriginChip origin={line.origin} />
                      <small>{line.rationale}</small>
                    </div>
                    <div className="gf-line-value">
                      <strong>{line.excluded ? 'Removed' : line.amount === null ? (line.editable ? 'Pending' : 'Included elsewhere') : money(line.amount)}</strong>
                      <small>
                        {line.fraction !== null ? `${percent(line.fraction)} of ${line.base}` : line.base}
                        {before && before[line.id] !== undefined && before[line.id] !== money(line.amount, '—') ? ` · was ${before[line.id]}` : ''}
                      </small>
                    </div>
                  </div>
                  {line.editable && !line.excluded && (
                    <div className="gf-line-actions">
                      <button type="button" className="gf-secondary" disabled={line.fraction === null || line.origin.startsWith('Selected by you')} onClick={() => useLine(line)}>
                        {line.origin.startsWith('Selected by you') ? 'In use ✓' : 'Use'}
                      </button>
                      <button type="button" className="gf-secondary" onClick={() => setResearch(line)}>
                        Research with AI
                      </button>
                      <button type="button" className="gf-secondary" aria-expanded={editing === line.id} onClick={() => setEditing(editing === line.id ? '' : line.id)}>
                        Edit
                      </button>
                      <button type="button" className="gf-link" onClick={() => setRemoving({ id: line.id, reason: '' })}>
                        Remove
                      </button>
                    </div>
                  )}
                  {line.status === 'scope_review_required' && (
                    <label className="gf-field">
                      <span>Confirm what offsite facilities cover (not already in battery limits)</span>
                      <input value={text(config.offsite_scope_confirmation)} onChange={(e) => set({ offsite_scope_confirmation: e.target.value })} placeholder="e.g. shared cooling water and stores only" />
                    </label>
                  )}
                  {line.excluded && (
                    <div className="gf-line-actions">
                      <small>Reason: {text(obj(config.exclusions)[line.id])}</small>
                      <button type="button" className="gf-secondary" onClick={() => set({ exclusions: without('exclusions', line.id) })}>
                        Add back
                      </button>
                    </div>
                  )}
                  {editing === line.id && <LineEditor line={line} config={config} currency={currency} onFraction={(v) => selectFraction(line, v)} onAmount={(a, r) => overrideAmount(line, a, r)} onReset={() => reset(line)} />}
                </li>
              ))}
            </ul>
          </section>
        ) : null,
      )}

      <section className="gf-card-block" aria-labelledby="gf-capex-add">
        <h2 id="gf-capex-add">Add a line</h2>
        {addable.length ? (
          <div className="gf-chips">
            {addable.map((f) => (
              <button key={text(f.id)} type="button" className="gf-secondary" onClick={() => set({ exclusions: without('exclusions', text(f.id)) })}>
                + {words(f.id)}
              </button>
            ))}
          </div>
        ) : (
          <p className="gf-muted">Every category in this method&apos;s factor table is already included.</p>
        )}
        <small className="gf-muted">Custom lines outside the method&apos;s published categories are not supported by the CAPEX engine yet; use an evidenced amount override on the closest category.</small>
      </section>

      <div className="gf-inline-actions">
        <span className="gf-muted">{capex.dirty ? 'Unsaved CAPEX changes.' : 'Saved. Recalculate to refresh Python totals.'}</span>
        <button type="button" className="gf-secondary" disabled={!capex.dirty || hook.busy} onClick={() => capex.reset()}>
          Discard
        </button>
        <button type="button" className="gf-primary" disabled={hook.busy || Boolean(state?.running)} onClick={() => void recalculate()}>
          Save & recalculate
        </button>
      </div>
      <RunBar
        label="Run OPEX"
        busy={hook.busy}
        disabled={Boolean(state?.running)}
        back={{ label: 'Equipment', onClick: () => props.go('equipment') }}
        status={<strong>{capex.dirty ? 'Your CAPEX edits will be saved first' : 'CAPEX ready for operating costs'}</strong>}
        note="Runs CAPEX, Revenue and OPEX together with Python, then opens OPEX."
        onRun={() => void props.advance(() => capex.save('User reviewed CAPEX in the CAPEX playground'))}
      />

      {removing && (
        <Panel
          title={`Remove ${words(removing.id)}?`}
          kicker="CAPEX LINE"
          onClose={() => setRemoving(null)}
          footer={
            <>
              <button type="button" className="gf-secondary" onClick={() => setRemoving(null)}>
                Cancel
              </button>
              <button
                type="button"
                className="gf-primary"
                disabled={!removing.reason.trim()}
                onClick={() => {
                  set({ exclusions: { ...obj(config.exclusions), [removing.id]: removing.reason.trim() } });
                  setRemoving(null);
                }}
              >
                Remove line
              </button>
            </>
          }
        >
          <p>The engine records a removed line as an explicit exclusion with your reason. It is never silently treated as zero.</p>
          <label className="gf-field">
            <span>Reason (required)</span>
            <input autoFocus value={removing.reason} onChange={(e) => setRemoving({ ...removing, reason: e.target.value })} placeholder="e.g. land is already owned by the client" />
          </label>
        </Panel>
      )}
      {research && (
        <Panel title={`Research ${research.label} with AI`} kicker="AI · PROVISIONAL" onClose={() => setResearch(null)}>
          <p>
            Per-line AI research is not available from the backend yet. FlowValue can instead prepare <strong>all</strong> CAPEX factor selections with the AI analyst. A version
            is saved first, proposals are labelled provisional, and you review them here before recalculating.
          </p>
          {!hook.aiEnabled && <p className="gf-warn">AI is switched off on this server.</p>}
          <button
            type="button"
            className="gf-primary"
            disabled={!hook.aiEnabled || hook.busy || Boolean(state?.running) || capex.dirty}
            onClick={() => {
              setResearch(null);
              void hook.action(() => api(`assessments/${hook.id}/stages/capex/prepare`, post({})));
            }}
          >
            I agree — prepare CAPEX factors with AI (usage charges apply)
          </button>
          {capex.dirty && <small>Save or discard your CAPEX edits first.</small>}
        </Panel>
      )}
    </div>
  );
}

function LineEditor({
  line,
  config,
  currency,
  onFraction,
  onAmount,
  onReset,
}: {
  line: CapexLine;
  config: Row;
  currency: string;
  onFraction: (v: number) => void;
  onAmount: (amount: number | null, rationale: string) => void;
  onReset: () => void;
}) {
  const override = obj(obj(config.overrides)[line.id]);
  const selected = num(obj(config.selected_factors)[line.id]);
  const [amount, setAmount] = useState(text(override.amount)),
    [why, setWhy] = useState(text(override.rationale));
  const value = selected ?? line.fraction ?? line.min ?? 0;
  const hasRange = line.min !== null && line.max !== null;
  return (
    <div className="gf-line-editor">
      {hasRange ? (
        <div className="gf-slider">
          <label htmlFor={`gf-f-${line.id}`}>
            Factor within the published range ({percent(line.min)} – {percent(line.max)})
          </label>
          <div>
            <input
              id={`gf-f-${line.id}`}
              type="range"
              min={line.min!}
              max={line.max!}
              step={Math.max((line.max! - line.min!) / 100, 0.0005)}
              value={value}
              onChange={(e) => onFraction(Number(e.target.value))}
            />
            <input
              type="number"
              aria-label={`${line.label} factor, percent`}
              min={line.min! * 100}
              max={line.max! * 100}
              step="0.1"
              value={Number((value * 100).toFixed(2))}
              onChange={(e) => e.target.value !== '' && onFraction(Number(e.target.value) / 100)}
            />
            <span>%</span>
          </div>
        </div>
      ) : (
        <p className="gf-muted">This category has no published factor range; use an evidenced amount.</p>
      )}
      <div className="gf-grid-2">
        <label className="gf-field">
          <span>Or a fixed amount ({currency || 'project currency'})</span>
          <input type="number" min="0" step="any" value={amount} onChange={(e) => setAmount(e.target.value)} />
        </label>
        <label className="gf-field">
          <span>Evidence / rationale (required for an amount)</span>
          <input value={why} onChange={(e) => setWhy(e.target.value)} placeholder="Quote, comparable project or engineering basis" />
        </label>
      </div>
      <div className="gf-line-actions">
        <button type="button" className="gf-secondary" disabled={amount === '' || !why.trim() || !(Number(amount) >= 0)} onClick={() => onAmount(Number(amount), why.trim())}>
          Apply amount
        </button>
        <button type="button" className="gf-link" onClick={onReset}>
          Return to method default
        </button>
      </div>
    </div>
  );
}
