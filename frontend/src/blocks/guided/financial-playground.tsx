'use client';
import {withCurrency} from '@/lib/display-currency';
import Link from 'next/link';
import { useEffect, useMemo, useRef, useState } from 'react';
import { ParameterMatrix } from '@/blocks/uncertainty/parameter-matrix';
import { canSample } from '@/blocks/uncertainty/variation-scope';
import { stableJson } from '@/lib/stable-json';
import { assessmentHref } from '@/lib/assessment-navigation';
import { type Job, type Settings } from '@/lib/monte-carlo';
import { strings,
  availablePercentiles,
  cashBands,
  compact,
  financialLevers,
  financialMetricKeys,
  list,
  money,
  metricMap,
  metricText,
  num,
  obj,
  percent,
  text,
  type Row,
} from '@/lib/guided-flow';
import { api, post, type Assessment } from './use-assessment';
import { BarChart, FanChart, LineChart } from './charts';
import { Issues, Panel, RunBar, StageHeading, type StageProps } from './flow';
import { AnalystCard } from './analyst-card';

type ChartId = 'cumulative' | 'fcff' | 'income' | 'mc-fan' | 'mc-npv';
const chartTitles: Record<ChartId, string> = {
  cumulative: 'Cumulative project cash',
  fcff: 'Annual project free cash flow',
  income: 'Revenue and operating costs',
  'mc-fan': 'Free cash flow uncertainty (Monte Carlo)',
  'mc-npv': 'NPV percentiles (Monte Carlo)',
};
const tabs = [
  ['results', 'Results'],
  ['scenario', 'Scenario & sensitivity'],
  ['monte', 'Monte Carlo'],
] as const;
type Tab = (typeof tabs)[number][0];

function readPins(): { pins: ChartId[]; side: boolean } {
  try {
    const v = JSON.parse(localStorage.getItem('flowvalue-pinned-charts') || '{}');
    return { pins: Array.isArray(v.pins) ? v.pins : ['cumulative'], side: v.side === true };
  } catch {
    return { pins: ['cumulative'], side: false };
  }
}

/**
 * Financial playground: NPV/IRR/payback from the Python ledger, pinned charts,
 * sliders on key financial levers, scenario copies saved as templates, and
 * Monte Carlo ranges. Every number shown is read from saved backend output.
 */
export function FinancialPlayground(props: StageProps) {
  const { hook } = props;
  const state = hook.state;
  const stage = obj(obj(obj(state?.results).stages).financial);
  const [tab, setTab] = useState<Tab>('results'),
    [pins, setPins] = useState<ChartId[]>(['cumulative']),
    [side, setSide] = useState(false),
    [job, setJob] = useState<Job | null>(null);
  const [scenarioBase, setScenarioBase] = useState<Row | null>(null);
  const [scenario, setScenario] = useState<Row | null>(null);
  const [overrides, setOverrides] = useState<Row>({});
  const [scenarioUpdating, setScenarioUpdating] = useState(false);
  const [scenarioBaseError, setScenarioBaseError] = useState('');
  const financialSnapshot = text(obj(stage.result).snapshot_id);
  useEffect(() => {
    setScenario(null); setOverrides({}); setScenarioBase(null); setScenarioBaseError('');
    if (!state?.id || !financialSnapshot) return;
    const controller = new AbortController();
    void api<Row>(`assessments/${state.id}/financial-sensitivity`, { signal: controller.signal })
      .then((value) => { if (!controller.signal.aborted) setScenarioBase(value); })
      .catch((error) => { if (!controller.signal.aborted) setScenarioBaseError(error.message); });
    return () => controller.abort();
  }, [state?.id, financialSnapshot]);
  const result = tab === 'scenario' ? obj(scenario?.result || scenarioBase?.result || stage.result) : obj(stage.result);
  const metrics = metricMap(result);
  const originalMetrics = metricMap(obj(scenarioBase?.result));
  const ledger = list(result.ledger);
  const currency = text(result.currency);
  const tabRefs = useRef<(HTMLButtonElement | null)[]>([]);
  useEffect(() => {
    const saved = readPins();
    setPins(saved.pins);
    setSide(saved.side);
  }, []);
  useEffect(() => {
    try {
      localStorage.setItem('flowvalue-pinned-charts', JSON.stringify({ pins, side }));
    } catch {
      /* per-viewer convenience only */
    }
  }, [pins, side]);
  const togglePin = (id: ChartId) => setPins((p) => (p.includes(id) ? p.filter((x) => x !== id) : [...p, id]));
  const labels = ledger.map((r) => 'Y' + text(obj(r.period).year));
  const summary = obj(job?.summary);
  const chart = (id: ChartId, height = 170) => {
    if (id === 'cumulative') return <LineChart title={chartTitles[id]} height={height} labels={labels} series={[{ label: 'Cumulative project cash', values: ledger.map((r) => num(r.cumulative_project_cash)), tone: 'a' }]} />;
    if (id === 'fcff') return <BarChart title={chartTitles[id]} height={height} labels={labels} values={ledger.map((r) => num(r.fcff))} />;
    if (id === 'income')
      return (
        <LineChart
          title={chartTitles[id]}
          height={height}
          labels={labels}
          series={[
            { label: 'Revenue', values: ledger.map((r) => num(r.revenue)), tone: 'a' },
            { label: 'Variable OPEX', values: ledger.map((r) => num(r.variable_opex)), tone: 'b' },
            { label: 'Fixed OPEX', values: ledger.map((r) => num(r.fixed_opex)), tone: 'c' },
          ]}
        />
      );
    if (id === 'mc-fan') return <FanChart title={chartTitles[id]} height={height} rows={cashBands(summary) as unknown as Row[]} />;
    return <PercentileStrip metric={obj(obj(summary.metrics).npv)} currency={text(summary.currency) || currency} />;
  };
  return (
    <div className={`gf-play gf-fin ${side && pins.length ? 'gf-fin-side' : ''}`}>
      <div className="gf-fin-layout">
        <div className="gf-fin-main gf-economics-split">
          <div className="gf-economics-results" role="region" aria-label="Financial visual analysis" tabIndex={0}>
      <StageHeading
        kicker="STAGE 06 · FINANCIAL"
        title="Financial playground"
        aside={
          <div className="gf-segment" role="group" aria-label="Pinned chart position">
            <button type="button" aria-pressed={!side} onClick={() => setSide(false)}>
              Pins on top
            </button>
            <button type="button" aria-pressed={side} onClick={() => setSide(true)}>
              Pins at side
            </button>
          </div>
        }
      >
        Investment performance from the Python financial ledger. Scenario calculations are saved separately and never replace your original project results.
      </StageHeading>
      <div className="gf-kpis gf-kpis-5">
            {financialMetricKeys.map(([label, key, kind]) => {
              const value = metricText(metrics.get(key), kind);
              return (
                <div key={key} className={key === 'project_npv' ? 'gf-kpi-hero' : undefined} data-negative={num(metrics.get(key)?.value)! < 0}>
                  <small>{label}</small>
                  <strong>{kind === 'money' ? withCurrency(value,currency) : value}</strong>
                  <span>
                    {kind === 'money' ? currency : text(metrics.get(key)?.unit)}
                    {tab === 'scenario' && Object.keys(overrides).length > 0 ? ` · original ${metricText(originalMetrics.get(key), kind)}` : ''}
                  </span>
                </div>
              );
            })}
          </div>
            <h2 className="gf-pane-heading">Visual analysis</h2>
            <div className="gf-fin-visuals">
        {pins.length > 0 && (
          <div className="gf-pins" role="complementary" aria-label="Pinned charts">
            {pins.map((id) => (
              <figure key={id} className="gf-pin">
                <div className="gf-pin-head">
                  <strong>{chartTitles[id]}</strong>
                  <button type="button" className="gf-icon" aria-label={`Unpin ${chartTitles[id]}`} onClick={() => togglePin(id)}>
                    ✕
                  </button>
                </div>
                {chart(id, 140)}
              </figure>
            ))}
          </div>
        )}
            <div className="gf-chart-grid">{(tab==='monte'?(['mc-fan','mc-npv'] as ChartId[]):(['cumulative','fcff','income'] as ChartId[])).map(id=><ChartCard key={id} title={chartTitles[id]} pinned={pins.includes(id)} onPin={()=>togglePin(id)}>{chart(id)}</ChartCard>)}</div>
            </div>
          </div>
          <div className="gf-economics-inputs" role="region" aria-label="Financial figures and scenarios" tabIndex={0}>
            <h2 className="gf-pane-heading">Figures &amp; scenarios</h2>
      <AnalystCard stage="financial" hook={props.hook} />
      {tab !== 'scenario' && <FinancialPlanningNote config={obj(obj(state?.plan).operating_economics)} />}

          {!stage.result && <p className="gf-note">The financial model has not been calculated yet. Complete CAPEX, OPEX and Revenue, then run Financial.</p>}
          {tab === 'scenario' && <p className="gf-note" role="status">{scenarioUpdating ? 'Updating scenario — displayed values are from the last completed calculation.' : scenario ? 'Independent scenario results · original CAPEX, OPEX and Revenue unchanged.' : 'Original calculated financial results.'}</p>}
          <Issues items={tab === 'scenario' ? strings(result.issues) : [...strings(stage.issues), ...strings(result.issues)]} />
          <div className="gf-tabs" role="tablist" aria-label="Financial views">
            {tabs.map(([id, label], i) => (
              <button
                key={id}
                ref={(n) => {
                  tabRefs.current[i] = n;
                }}
                type="button"
                role="tab"
                id={`gf-tab-${id}`}
                aria-selected={tab === id}
                aria-controls={`gf-tabpanel-${id}`}
                tabIndex={tab === id ? 0 : -1}
                onClick={() => setTab(id)}
                onKeyDown={(e) => {
                  const next = e.key === 'ArrowRight' ? (i + 1) % tabs.length : e.key === 'ArrowLeft' ? (i + tabs.length - 1) % tabs.length : null;
                  if (next === null) return;
                  e.preventDefault();
                  setTab(tabs[next][0]);
                  tabRefs.current[next]?.focus();
                }}
              >
                {label}
              </button>
            ))}
          </div>
          <div role="tabpanel" id={`gf-tabpanel-${tab}`} aria-labelledby={`gf-tab-${tab}`} className="gf-tabpanel">
            {tab === 'results' && <div className="gf-table-wrap"><table className="gf-table"><caption>Saved financial ledger · {currency}</caption><thead><tr><th>Year</th><th>Project cash flow</th><th>Cumulative cash</th></tr></thead><tbody>{ledger.map((row,i)=><tr key={i}><th>{text(obj(row.period).year)}</th><td>{withCurrency(money(row.fcff),currency)}</td><td>{withCurrency(money(row.cumulative_project_cash),currency)}</td></tr>)}</tbody></table></div>}
            {tab === 'scenario' && <>
              <ScenarioTab props={props} base={scenarioBase} baseError={scenarioBaseError} overrides={overrides}
                setOverrides={setOverrides} onResult={setScenario} onUpdating={setScenarioUpdating} completedKey={scenario ? stableJson(scenario.overrides) : ""} />

            </>}
            {tab === 'monte' && (
              <MonteCarloTab props={props} job={job} setJob={setJob} pins={pins} onPin={togglePin} chart={chart} />
            )}
          </div>
        </div>
      </div>
      </div>
      <RunBar label="Recalculate financials" hideRun={tab === 'scenario'} busy={hook.busy} disabled={Boolean(state?.running)}
        back={{label:'Revenue',onClick:()=>props.go('revenue')}}
        status={<strong>{stage.result ? 'Financial model calculated by Python' : 'Financial model pending'}</strong>}
        note={tab === 'scenario' ? 'Scenario calculations are stored separately. Reset restores the original calculation.' : 'Reports and exports use the same saved assessment.'}
        onRun={()=>void hook.action(()=>hook.runStage('financial'))}>
        {Boolean(stage.result) && tab !== 'scenario' && <a className="gf-secondary gf-button-link" href={`/api/assessments/${hook.id}/report`} target="_blank" rel="noreferrer">Open TEA report ↗</a>}
      </RunBar>
    </div>
  );
}

function ChartCard({ title, pinned, onPin, children }: { title: string; pinned: boolean; onPin: () => void; children: React.ReactNode }) {
  return (
    <section className="gf-card-block gf-chart-card" aria-label={title}>
      <div className="gf-block-head">
        <h2>{title}</h2>
        <button type="button" className="gf-secondary" aria-pressed={pinned} onClick={onPin}>
          {pinned ? 'Pinned ✓' : 'Pin'}
        </button>
      </div>
      {children}
    </section>
  );
}

function PercentileStrip({ metric, currency }: { metric: Row; currency: string }) {
  const keys = availablePercentiles(metric);
  if (!keys.length) return <p className="gf-muted">Run a Monte Carlo study to see NPV percentiles.</p>;
  return (
    <dl className="gf-percentiles">
      {keys.map((k) => (
        <div key={k}>
          <dt>{k.toUpperCase()}</dt>
          <dd>
            {withCurrency(compact(metric[k]),currency)} <small>{currency}</small>
          </dd>
        </div>
      ))}
    </dl>
  );
}

/* --------------------------------------------------------------- scenario */

export function ScenarioTab({ props, base, baseError, overrides, setOverrides, onResult, onUpdating, completedKey = "" }: {
  props: StageProps; base: Row | null; baseError: string; overrides: Row; completedKey?: string;
  setOverrides: (value: Row) => void; onResult: (value: Row | null) => void; onUpdating: (value: boolean) => void;
}) {
  const { hook } = props;
  const state = hook.state!;
  const policy = { ...obj(base?.policy), ...overrides };
  const [error, setError] = useState('');
  const [updating, setUpdating] = useState(false);
  const overrideKey = stableJson(overrides);
  const snapshotId = text(base?.baseline_snapshot_id);
  useEffect(() => {
    setError('');
    if (!snapshotId || !Object.keys(overrides).length || overrideKey === completedKey) { onUpdating(false); setUpdating(false); return; }
    let disposed = false;
    const controller = new AbortController();
    setUpdating(true); onUpdating(true);
    const timer = setTimeout(() => {
      void api<Row>(`assessments/${state.id}/financial-sensitivity`, { ...post({ baseline_snapshot_id: snapshotId, overrides }), signal: controller.signal })
        .then((value) => {
          if (disposed) return;
          onResult(value);
          void api<Row[]>(`assessments/${state.id}/versions`).then(setTemplates).catch(() => {});
        })
        .catch((failure) => { if (!disposed) setError(failure.message); })
        .finally(() => { if (!disposed) { setUpdating(false); onUpdating(false); } });
    }, 400);
    return () => { disposed = true; clearTimeout(timer); controller.abort(); onUpdating(false); };
    // Canonical signature keeps the effect independent of object identity.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [overrideKey, snapshotId, state.id, completedKey]);
  const [templates, setTemplates] = useState<Row[]>([]),
    [name, setName] = useState(''),
    [comparison, setComparison] = useState<Row | null>(null),
    [baselineId, setBaselineId] = useState(''),
    [addTag, setAddTag] = useState(''),
    [confirmRemove, setConfirmRemove] = useState<Row | null>(null);
  const isCopy = Boolean(state.parent_version);
  useEffect(() => {
    void api<Row[]>(`assessments/${state.id}/versions`)
      .then((v) => setTemplates(Array.isArray(v) ? v : []))
      .catch(() => setTemplates([]));
    if (state.parent_version)
      void api<Row[]>('versions')
        .then((all) => setBaselineId(text((Array.isArray(all) ? all : []).find((v) => v.id === state.parent_version)?.assessment_id)))
        .catch(() => {});
  }, [state.id, state.revision, state.parent_version]);
  const setLever = (key: string, value: number) => setOverrides({ ...overrides, [key]: value });
  const report = obj(state.scoped_report || state.effective_report || obj(state.parsed).report);
  const equipment = list(report.entities).filter((e) => e.kind === 'equipment');
  async function register(edit: Row) {
    await hook.action(async () => hook.setState(await api<Assessment>(`assessments/${state.id}/equipment-register`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ revision: state.revision, ...edit }) })));
  }
  return (
    <div className="gf-scenario">
      <section className="gf-card-block" aria-labelledby="gf-levers">
        <div className="gf-block-head">
          <h2 id="gf-levers">Key parameters</h2>
          <span className="gf-muted">{updating ? 'Calculating scenario…' : Object.keys(overrides).length ? 'Independent scenario' : 'Original calculated values'}</span>
        </div>
        <div className="gf-levers">
          {financialLevers.map((lever) => {
            const value = num(policy[lever.key]);
            return (
              <div key={lever.key} className="gf-slider">
                <label htmlFor={`gf-l-${lever.key}`}>
                  {lever.label} {value === null && <em className="gf-required">Not set</em>}
                </label>
                <div>
                  <input id={`gf-l-${lever.key}`} type="range" disabled={!base} min={lever.min} max={lever.max} step={lever.step} value={value ?? lever.min} onChange={(e) => setLever(lever.key, Number(e.target.value))} />
                  <input
                    type="number"
                    disabled={!base}
                    aria-label={`${lever.label}${lever.percent ? ', percent' : ''}`}
                    step={lever.percent ? 0.1 : lever.step}
                    value={value === null ? '' : lever.percent ? Number((value * 100).toFixed(2)) : value}
                    onChange={(e) => e.target.value !== '' && setLever(lever.key, lever.percent ? Number(e.target.value) / 100 : Number(e.target.value))}
                  />
                  <span>{lever.percent ? '%' : 'unit' in lever ? lever.unit : ''}</span>
                </div>
              </div>
            );
          })}
        </div>
        <label className="gf-field">
          <span>Closure allowance ({text(obj(obj(state.plan.operating_economics).price_basis).currency) || 'project currency'})</span>
          <input type="number" disabled={!base} min="0" step="any" value={num(policy.closure_allowance) ?? ''}
            onChange={(event) => event.target.value !== '' && setLever('closure_allowance', Number(event.target.value))} />
          <small>One-time end-of-project allowance. A zero is a planning assumption, not a confirmed free closure.</small>
        </label>
        <div className="gf-line-actions">
          <button type="button" className="gf-secondary" disabled={!Object.keys(overrides).length}
            onClick={() => { setOverrides({}); onResult(null); setError(''); onUpdating(false); }}>
            Reset to original
          </button>
        </div>
        {(error || baseError) && <p className="gf-error" role="alert">{error || baseError}</p>}
        {!base && !baseError && <p className="gf-muted">Loading the original calculated financial inputs…</p>}
        <small className="gf-muted">Changes calculate automatically in Python after a short pause and are saved as separate versions. Original inputs and upstream results stay unchanged.</small>
      </section>

      <section className="gf-card-block" aria-labelledby="gf-templates">
        <h2 id="gf-templates">Templates & comparisons</h2>
        <div className="gf-line-actions">
          <input aria-label="Template name" placeholder="e.g. Base case, 8% discount" value={name} maxLength={120} onChange={(e) => setName(e.target.value)} />
          <button
            type="button"
            className="gf-primary"
            disabled={!name.trim() || hook.busy || Boolean(state.running)}
            onClick={() =>
              void hook.action(async () => {
                if (Object.keys(overrides).length) await api(`assessments/${state.id}/financial-sensitivity`, post({ baseline_snapshot_id: snapshotId, overrides, name: name.trim() }));
                else await api(`assessments/${state.id}/versions`, post({ name: name.trim() }));
                setName('');
                setTemplates(await api<Row[]>(`assessments/${state.id}/versions`));
              })
            }
          >
            Save as template
          </button>
        </div>
        <TemplateList items={templates.filter((t) => !/^Before /.test(text(t.name)))} empty="No templates saved for this assessment yet." busy={hook.busy} onOpen={(t) => void hook.action(async () => hook.select(text((await api<Row>(`versions/${text(t.id)}/open`, post({}))).id)))} />
        {templates.some((t) => /^Before /.test(text(t.name))) && (
          <details className="gf-details">
            <summary>Automatic snapshots ({templates.filter((t) => /^Before /.test(text(t.name))).length})</summary>
            <TemplateList items={templates.filter((t) => /^Before /.test(text(t.name)))} empty="" busy={hook.busy} onOpen={(t) => void hook.action(async () => hook.select(text((await api<Row>(`versions/${text(t.id)}/open`, post({}))).id)))} />
          </details>
        )}
        {isCopy && baselineId && (
          <div className="gf-line-actions">
            <button type="button" className="gf-secondary" onClick={() => void hook.action(async () => setComparison(await api<Row>(`assessments/${state.id}/compare/${baselineId}`)))}>
              Compare with baseline
            </button>
            <button type="button" className="gf-link" onClick={() => hook.select(baselineId)}>
              Back to baseline
            </button>
          </div>
        )}
        {comparison && <Comparison value={comparison} />}
      </section>

      <section className="gf-card-block" aria-labelledby="gf-scn-eq">
        <h2 id="gf-scn-eq">Add or remove equipment</h2>
        {!isCopy ? (
          <p className="gf-muted">Open a template as a scenario copy first, so equipment changes never alter your baseline register.</p>
        ) : (
          <>
            <ul className="gf-templates">
              {equipment.map((e) => (
                <li key={text(e.key)}>
                  <span>{text(e.identifier)}</span>
                  <button type="button" className="gf-link" disabled={hook.busy || Boolean(state.running)} onClick={() => setConfirmRemove(e)}>
                    Remove from scenario
                  </button>
                </li>
              ))}
            </ul>
            <div className="gf-line-actions">
              <input aria-label="New equipment tag" placeholder="New equipment tag, e.g. P-901" value={addTag} maxLength={128} onChange={(e) => setAddTag(e.target.value)} />
              <button
                type="button"
                className="gf-secondary"
                disabled={!addTag.trim() || hook.busy || Boolean(state.running)}
                onClick={() => {
                  void register({ action: 'add', tag: addTag.trim(), name: addTag.trim() });
                  setAddTag('');
                }}
              >
                Add equipment
              </button>
            </div>
            <small className="gf-muted">After changing equipment, rerun Equipment → CAPEX → OPEX → Revenue → Financial from the stage rail.</small>
          </>
        )}
      </section>
      {confirmRemove && (
        <Panel
          title={`Remove ${text(confirmRemove.identifier)} from this scenario?`}
          kicker="SCENARIO COPY"
          onClose={() => setConfirmRemove(null)}
          footer={
            <>
              <button type="button" className="gf-secondary" onClick={() => setConfirmRemove(null)}>
                Cancel
              </button>
              <button
                type="button"
                className="gf-primary"
                onClick={() => {
                  void register({ action: 'remove', equipment_key: text(confirmRemove.key) });
                  setConfirmRemove(null);
                }}
              >
                Remove
              </button>
            </>
          }
        >
          <p>This edits only the scenario copy. The baseline assessment and its saved templates are unchanged.</p>
        </Panel>
      )}
    </div>
  );
}

function FinancialPlanningNote({ config }: { config: Row }) {
  const provenance = obj(config.financial_input_provenance);
  const policy = obj(config.financial);
  const entries = Object.entries(provenance);
  if (!entries.length) return null;
  return <details className="gf-notes">
    <summary>Financial planning assumptions · review</summary>
    <p>These are editable planning assumptions, not verified tax rules or forecasts. Change them under Scenario &amp; sensitivity.</p>
    <ul>{entries.map(([key, raw]) => {
      const item = obj(raw), lever = financialLevers.find((row) => row.key === key);
      const changed = item.origin === 'user' || num(item.value) !== num(policy[key]);
      const value = lever?.percent ? percent(policy[key]) : text(policy[key]);
      return <li key={key}><strong>{lever?.label || 'Closure allowance'}: {value}{key === 'closure_allowance' ? ` ${text(obj(config.price_basis).currency)}` : ''}</strong>
        {' · '}{changed ? 'User changed' : 'AI proposed'} — {text(item.rationale)}</li>;
    })}</ul>
  </details>;
}

function TemplateList({ items, empty, busy, onOpen }: { items: Row[]; empty: string; busy: boolean; onOpen: (t: Row) => void }) {
  return (
    <ul className="gf-templates">
      {items.map((t) => (
        <li key={text(t.id)}>
          <span>{text(t.name)}</span>
          <button type="button" className="gf-secondary" disabled={busy} onClick={() => onOpen(t)}>
            Open as scenario copy
          </button>
        </li>
      ))}
      {!items.length && empty && <li className="gf-muted">{empty}</li>}
    </ul>
  );
}

function Comparison({ value }: { value: Row }) {
  const left = metricMap(obj(obj(value.left).financial)),
    right = metricMap(obj(obj(value.right).financial));
  return (
    <div className="gf-table-wrap">
      <table className="gf-table">
        <thead>
          <tr>
            <th scope="col">Metric</th>
            <th scope="col">This scenario</th>
            <th scope="col">Baseline</th>
          </tr>
        </thead>
        <tbody>
          {financialMetricKeys.map(([label, key, kind]) => (
            <tr key={key}>
              <th scope="row">{label}</th>
              <td>{kind === 'money' ? withCurrency(metricText(left.get(key), kind),obj(obj(value.left).financial).currency) : metricText(left.get(key), kind)}</td>
              <td>{kind === 'money' ? withCurrency(metricText(right.get(key), kind),obj(obj(value.right).financial).currency) : metricText(right.get(key), kind)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <small className="gf-muted">Changed inputs: {(Array.isArray(value.changed_sections) ? value.changed_sections : []).join(', ') || 'none'}</small>
    </div>
  );
}

/* ------------------------------------------------------------ Monte Carlo */

function MonteCarloTab({
  props,
  job,
  setJob,
  pins,
  onPin,
  chart,
}: {
  props: StageProps;
  job: Job | null;
  setJob: (j: Job | null) => void;
  pins: ChartId[];
  onPin: (id: ChartId) => void;
  chart: (id: ChartId) => React.ReactNode;
}) {
  const { hook } = props;
  const id = hook.id;
  const [settings, setSettings] = useState<Settings | null>(null),
    [query, setQuery] = useState(''),
    [preflight, setPreflight] = useState<Row | null>(null),
    [error, setError] = useState(''),
    [busy, setBusy] = useState(false);
  useEffect(() => {
    if (!id) return;
    void Promise.all([api<{ settings: Settings }>(`assessments/${id}/monte-carlo/discover`), api<Job[]>(`assessments/${id}/monte-carlo/jobs`)])
      .then(([d, jobs]) => {
        setSettings(d.settings);
        const list = jobs as Job[];
        const chosen = list.filter((j) => ['queued', 'running'].includes(j.status)).at(-1) || list.filter((j) => j.status === 'complete').at(-1) || list.at(-1) || null;
        if (chosen) void api<Job>(`assessments/${id}/monte-carlo/jobs/${chosen.id}`).then(setJob);
      })
      .catch((e) => setError((e as Error).message));
  }, [id, setJob]);
  useEffect(() => {
    if (!job || !['queued', 'running'].includes(job.status)) return;
    const timer = setInterval(() => {
      void api<Job>(`assessments/${id}/monte-carlo/jobs/${job.id}`)
        .then(setJob)
        .catch((e) => setError((e as Error).message));
    }, 1500);
    return () => clearInterval(timer);
  }, [id, job, setJob]);
  const enabled = settings?.parameters.filter((p) => p.enabled).length ?? 0;
  const shown = useMemo(() => (settings?.parameters || []).filter((p) => !query || `${p.label} ${p.kind}`.toLowerCase().includes(query.toLowerCase())).slice(0, 40), [settings, query]);
  async function run(fn: () => Promise<void>) {
    setBusy(true);
    setError('');
    try {
      await fn();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  const summary = obj(job?.summary),
    metrics = obj(summary.metrics);
  const active = Boolean(job && ['queued', 'running'].includes(job.status));
  return (
    <div className="gf-mc">
      {error && (
        <p className="gf-error" role="alert">
          {error}
        </p>
      )}
      <section className="gf-card-block" aria-labelledby="gf-mc-setup">
        <div className="gf-block-head">
          <h2 id="gf-mc-setup">Run Monte Carlo</h2>
          <Link className="gf-link" href={assessmentHref('/monte-carlo/setup', id)}>
            Full parameter setup ↗
          </Link>
        </div>
        {!settings ? (
          <p className="gf-muted">Loading uncertainty drivers…</p>
        ) : (
          <>
            <div className="gf-grid-4">
              <label className="gf-field">
                <span>Study name</span>
                <input value={settings.label} onChange={(e) => setSettings({ ...settings, label: e.target.value })} />
              </label>
              <label className="gf-field">
                <span>Variations · fixed at 200</span>
                <select value={settings.iterations} onChange={(e) => setSettings({ ...settings, iterations: Number(e.target.value) })}>
                  {[200].map((n) => (
                    <option key={n} value={n}>
                      {n.toLocaleString('en-GB')}
                    </option>
                  ))}
                </select>
              </label>
              <label className="gf-field">
                <span>Random seed</span>
                <input type="number" min="0" value={settings.seed} onChange={(e) => setSettings({ ...settings, seed: Number(e.target.value) })} />
              </label>
              <div className="gf-field">
                <span>Uncertainty drivers</span>
                <strong>
                  {enabled} of {settings.parameters.length} enabled
                </strong>
              </div>
            </div>
            <ParameterMatrix parameters={settings.parameters} disabled={busy || active} onChange={(key, patch) => {
              setPreflight(null);
              setSettings({ ...settings, parameters: settings.parameters.map((parameter) => parameter.id === key ? { ...parameter, ...patch } : parameter) });
            }} />
            <div className="gf-line-actions">
              <button type="button" className="gf-secondary" disabled={busy || active} onClick={() => void run(async () => setPreflight(await api<Row>(`assessments/${id}/monte-carlo/preflight`, post(settings))))}>
                Check setup
              </button>
              <button type="button" className="gf-primary" disabled={busy || active || hook.busy || !enabled || settings.parameters.some(p => p.enabled && !canSample(p))} onClick={() => void run(async () => setJob(await api<Job>(`assessments/${id}/monte-carlo/run`, post(settings))))}>
                Run Monte Carlo
              </button>
              {active && job && (
                <button type="button" className="gf-link" onClick={() => void run(async () => setJob(await api<Job>(`assessments/${id}/monte-carlo/jobs/${job.id}/cancel`, post({}))))}>
                  Cancel after current batch
                </button>
              )}
            </div>
            {preflight && (
              <p className="gf-note" role="status">
                Priced records {text(obj(preflight.coverage).priced)} / {text(obj(preflight.coverage).total)}.{' '}
                {Array.isArray(preflight.issues) && preflight.issues.length ? preflight.issues.map(String).join(' ') : 'No blocking issues.'}
              </p>
            )}
          </>
        )}
        {job && (
          <div className="gf-mc-progress" aria-live="polite">
            <span>
              {job.settings?.label || 'Simulation'} · {job.status} · {job.completed.toLocaleString('en-GB')} / {job.total.toLocaleString('en-GB')} iterations
            </span>
            <progress value={job.completed} max={job.total} />
            {job.error && <p className="gf-error">{job.error}</p>}
          </div>
        )}
      </section>
      {job?.summary && (
        <>
          <div className="gf-kpis">
            {[
              ['NPV', metrics.npv, false],
              ['IRR', metrics.irr, true],
              ['CAPEX', metrics.capex, false],
            ].map(([label, m, pct]) => (
              <div key={String(label)}>
                <small>{String(label)} · P10 / P50 / P90</small>
                <strong>
                  {pct ? percent(obj(m).p50) : withCurrency(compact(obj(m).p50),summary.currency)}
                </strong>
                <span>
                  {pct ? `${percent(obj(m).p10)} – ${percent(obj(m).p90)}` : `${withCurrency(compact(obj(m).p10),summary.currency)} – ${withCurrency(compact(obj(m).p90),summary.currency)}`} {pct ? '' : text(summary.currency)}
                </span>
              </div>
            ))}
            <div>
              <small>Probability NPV &lt; 0</small>
              <strong>{percent(summary.probability_negative_npv)}</strong>
              <span>Complete-scope runs only</span>
            </div>
          </div>

          <Link className="gf-link" href={assessmentHref('/monte-carlo/overview', id) + `&job=${job.id}`}>Explore all variations, sensitivities and full configurations ↗</Link>
          <p className="gf-muted">
            {text(summary.percentile_convention)} The backend currently reports P10/P50/P90, so the 80% band is shown. 50% (P25–P75) and 90% (P5–P95) bands appear automatically once
            those percentiles are reported.
          </p>
        </>
      )}
    </div>
  );
}
