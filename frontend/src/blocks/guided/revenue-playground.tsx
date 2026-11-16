'use client';
import Link from 'next/link';
import { useState } from 'react';
import { assessmentHref } from '@/lib/assessment-navigation';
import { strings, compact, list, money, num, obj, text, words, type Row } from '@/lib/guided-flow';
import { api, post, type Assessment } from './use-assessment';
import { Issues, OriginChip, Panel, RunBar, StageHeading, type StageProps } from './flow';
import { AnalystCard } from './analyst-card';
import { revenueLines, revenueRateSources, requiresTerms } from '@/blocks/revenue/rate-lines';

const categories = [
  ['processing_services', 'Processing / treatment service'],
  ['product_sales', 'Product sales'],
  ['capacity_availability', 'Capacity or availability payment'],
  ['infrastructure_usage', 'Infrastructure usage'],
  ['environmental_attributes', 'Environmental attributes'],
  ['other_contractual_income', 'Other contractual income'],
] as const;

/**
 * Revenue playground. Income only ever comes from the Revenue Box and the
 * explicit revenue worksheet; an unpriced line is shown as unpriced, not zero.
 */
export function RevenuePlayground(props: StageProps) {
  const { hook } = props;
  const state = hook.state;
  const stage = obj(obj(obj(state?.results).stages).revenue);
  const result = obj(stage.result);
  const config = obj(state?.plan?.operating_economics);
  const [answers, setAnswers] = useState<Record<string, string>>({}),
    [adding, setAdding] = useState(false),
    [editing, setEditing] = useState<Row | null>(null),
    [research, setResearch] = useState<Row | null>(null);
  // An approval prompt is not a clarification: only real questions block approval.
  const questions = (state?.revenue_questions || []).map(String).filter((q) => !/^\s*(data required:\s*)?review and approve/i.test(q));
  const lines: Row[] = [...list(config.sales), ...list(config.commercial_lines)];
  const drafts = revenueLines(config);
  const fullOperation = obj(result.full_operation);
  const products = list(fullOperation.products);
  const commercial = list(fullOperation.commercial);
  const fullAnnual = list(fullOperation.annual)[0];
  const receipt = obj(obj(state?.stage_runs).revenue);
  // A saved approval goes stale when prices, quantities or the schedule change; the stage receipt says so.
  const approvedAt = text(obj(state?.revenue_approval).approved_at);
  const approved =
    Boolean(state?.revenue_approval) &&
    !questions.length &&
    (!/approve/i.test(`${text(receipt.message)} ${strings(stage.issues).join(' ')}`) || (approvedAt !== '' && approvedAt > text(receipt.completed_at)));
  const productFor = (id: string) => products.find((p) => text(p.product_id) === id) || commercial.find((p) => text(p.line_id) === id);
  const linePrice = (line: Row) => num(line.unit_price ?? line.price ?? line.rate ?? list(line.years)[0]?.rate);
  return (
    <div className="gf-play">
      <StageHeading kicker="STAGE 05 · REVENUE" title="Revenue playground">
        Income comes only from what you set on the Entry board and the explicit revenue worksheet. Prices you give are your assumptions; unpriced income stays unpriced.
      </StageHeading>
      <AnalystCard stage="revenue" hook={props.hook} />
      <p className="gf-note gf-rev-effects" role="note">
        Revenue is shown at 100% scheduled operation using your saved rates and prices. Year-by-year realization is a separate financial scenario you control.
        Approved revenue edits automatically recalculate dependent operating costs.
      </p>
      <div className="gf-kpis">
        <div className="gf-kpi-hero">
          <small>100% annual revenue</small>
          <strong>{num(obj(fullAnnual).sales_revenue) === null ? 'Not calculated' : compact(obj(fullAnnual).sales_revenue)}</strong>
          <span>
            {text(obj(result.basis).currency)} {text(obj(result.basis).price_period)}
            {' · At 100% scheduled operation, not a year-one forecast'}
          </span>
        </div>
        <div>
          <small>Revenue lines</small>
          <strong>{lines.length}</strong>
          <span>{lines.filter((l) => linePrice(l) === null).length} unpriced</span>
        </div>
        <div>
          <small>Approval</small>
          <strong>{approved ? 'Approved' : 'Pending'}</strong>
          <span>{questions.length ? `${questions.length} open questions` : 'Required before financial results'}</span>
        </div>
      </div>
      <Issues items={[...strings(stage.issues), ...strings(result.issues)]} />

      <section className="gf-card-block" aria-labelledby="gf-box">
        <h2 id="gf-box">Revenue assumptions</h2>
        <p className="gf-muted">Income sources come from your process description. <Link href={assessmentHref('/flow?stage=entry', hook.id)}>Edit the project brief</Link>.</p>
        <div className="gf-line-actions">
          <button
            type="button"
            className="gf-primary"
            disabled={approved || questions.length > 0 || hook.busy || Boolean(state?.running)}
            onClick={() => void hook.action(async () => hook.setState(await api<Assessment>(`assessments/${hook.id}/revenue-authority`, post({ revision: state!.revision, approve: true }))))}
          >
            {approved ? 'Revenue approved ✓' : 'Approve revenue assumptions'}
          </button>
        </div>
        {questions.length > 0 && (
          <div className="gf-questions">
            <strong>FlowValue needs these answers before income can be calculated</strong>
            {questions.map((q) => (
              <label key={q} className="gf-field">
                <span>{q}</span>
                <input value={answers[q] || ''} onChange={(e) => setAnswers({ ...answers, [q]: e.target.value })} />
              </label>
            ))}
            <div className="gf-line-actions">
              <button
                type="button"
                className="gf-secondary"
                disabled={!hook.aiEnabled || hook.busy || Boolean(state?.running) || !Object.values(answers).some((a) => a.trim())}
                onClick={() =>
                  void hook.action(() =>
                    api(
                      `assessments/${hook.id}/revenue-authority`,
                      post({
                        revision: state!.revision,
                        reinterpret: true,
                        clarifications: Object.entries(answers)
                          .filter(([, a]) => a.trim())
                          .map(([question, answer]) => ({ question, answer })),
                      }),
                    ),
                  )
                }
              >
                Interpret answers with AI (provisional)
              </button>
              <button type="button" className="gf-secondary" onClick={() => setAdding(true)}>
                Enter prices & rates directly
              </button>
            </div>
            {!hook.aiEnabled && <small>AI is switched off on this server, so enter the revenue lines directly.</small>}
          </div>
        )}
      </section>

      <section className="gf-card-block" aria-labelledby="gf-rev-lines">
        <div className="gf-block-head">
          <h2 id="gf-rev-lines">Revenue lines</h2>
          <button type="button" className="gf-secondary" onClick={() => setAdding(true)}>
            + Add priced line
          </button>
        </div>
        {!lines.length && <p className="gf-muted">No revenue lines yet. State how the project earns income in the process description, then review its revenue assumptions.</p>}
        <ul className="gf-lines">
          {lines.map((line) => {
            const id = text(line.id),
              product = productFor(id),
              price = linePrice(line),
              draft = drafts.find((d) => d.id === id),
              simple = draft && !draft.advanced && !draft.component && !requiresTerms(draft);
            return (
              <li key={id} className="gf-line">
                <div className="gf-line-main">
                  <div>
                    <strong>{text(line.name) || words(id)}</strong>
                    <OriginChip origin={/ai|llm|propos/i.test(`${text(line.origin)} ${text(line.price_mode)}`) ? 'AI · provisional' : 'Your assumption'} />
                    <small>
                      {words(line.category || line.role)} · {price === null ? <em className="gf-missing">Unpriced — not counted as zero</em> : `${price} ${text(config.price_basis && obj(config.price_basis).currency)} per ${text(line.quantity_unit || line.price_unit)}`}
                    </small>
                  </div>
                  <div className="gf-line-value">
                    <strong>{product ? money(product.net_sales_revenue ?? product.revenue) : 'Not calculated'}</strong>
                    <small>{product ? `${text(product.quantity_sold ?? product.quantity)} ${text(product.quantity_unit)} per year at 100% scheduled operation` : 'Recalculate to see income at 100% operation'}</small>
                  </div>
                </div>
                <div className="gf-line-actions">
                  {simple ? <button type="button" className="gf-secondary" disabled={hook.busy || Boolean(state?.running)} onClick={() => setEditing(line)}>Edit</button>
                    : <Link className="gf-secondary" href={assessmentHref('/revenue', hook.id)}>Edit terms</Link>}
                  <button type="button" className="gf-secondary" onClick={() => setResearch(line)}>
                    Research price with AI
                  </button>
                </div>
              </li>
            );
          })}
        </ul>
        <Link className="gf-link" href={assessmentHref('/revenue', hook.id)}>
          Open the full revenue worksheet ↗
        </Link>
      </section>

      <RunBar
        label="Run Financial"
        busy={hook.busy}
        disabled={Boolean(state?.running)}
        back={{ label: 'OPEX', onClick: () => props.go('opex') }}
        status={<strong>{approved ? 'Revenue approved' : 'Approve revenue to complete the financial model'}</strong>}
        note="Recalculates stale economics first, then runs the financial model with Python."
        onRun={() => {
          const fresh = obj(obj(state?.stage_runs).revenue).status === 'ready' && stage.result_is_stale !== true;
          void props.advance(undefined, fresh ? [] : ['revenue']);
        }}
      />
      {(adding || editing) && state && <RevenueLineEditor key={editing ? text(editing.id) : 'new'} state={state} existing={editing || undefined} onClose={() => { setAdding(false); setEditing(null); }} props={props} />}
      {research && state && (
        <Panel title={`Research a price for ${text(research.name)}`} kicker="AI · PROVISIONAL" onClose={() => setResearch(null)}>
          <p>
            FlowValue will ask the AI analyst for dated comparable prices and buyer requirements, with citations. Public listings are not contracts; results are a provisional
            draft for you to review in the revenue worksheet and are never applied automatically.
          </p>
          {!hook.aiEnabled && <p className="gf-warn">AI is switched off on this server.</p>}
          <button
            type="button"
            className="gf-primary"
            disabled={!hook.aiEnabled || hook.busy || Boolean(state.running)}
            onClick={() => {
              const target = text(research.id);
              setResearch(null);
              void hook.action(() => api(`assessments/${hook.id}/research`, post({ revision: state.revision, kind: 'market', target_id: target, consent: true, recommend_price: true })));
            }}
          >
            I agree — research with AI (usage charges apply)
          </button>
        </Panel>
      )}
    </div>
  );
}

export function RevenueLineEditor({ state, existing, onClose, props }: { state: Assessment; existing?: Row; onClose: () => void; props: StageProps }) {
  const { hook } = props;
  const [openingRevision] = useState(state.revision);
  const [saveError, setSaveError] = useState('');
  const operating = obj(obj(state.plan?.operating_economics).operating);
  const report = obj(state.scoped_report || state.effective_report || obj(state.parsed).report || obj(obj(state.stage_outputs).engineering_data).report);
  const sources = revenueRateSources(report);
  const initial = existing ? revenueLines(obj(state.plan?.operating_economics)).find((r) => r.id === text(existing.id)) : undefined;
  const initialSource = initial?.stream_key ? sources.find((s) => s.streamKey === initial.stream_key &&
    (['m3', 'L'].includes(initial.price_unit) === ['m3', 'L'].includes(s.priceUnit))) : undefined;
  const [rateSource, setRateSource] = useState(initialSource?.id || (initial && !initial.stream_key ? '__manual__' : ''));
  const selectedSource = sources.find((s) => s.id === rateSource);
  const manualRate = rateSource === '__manual__';
  const [line, setLine] = useState({
    name: initial?.name || '',
    kind: initial?.kind || 'service',
    category: initial?.category || 'processing_services',
    rate: text(initial?.rate),
    rate_unit: initial?.rate_unit || 'm3/h',
    price: text(initial?.price),
    price_unit: initial?.price_unit || 'm3',
    price_period: initial?.price_period || String(new Date().getFullYear()),
    sold_fraction: text(initial?.sold_fraction ?? 1),
    rationale: initial?.rationale || '',
  });
  const [days, setDays] = useState(text(operating.days_per_year || '')),
    [hours, setHours] = useState(text(operating.hours_per_day || '')),
    [approve, setApprove] = useState(Boolean(existing && state.revenue_approval));
  const valid = line.name.trim() && Number.isFinite(Number(line.price)) && Number(line.price) >= 0 && line.price !== '' && (selectedSource || (manualRate && Number.isFinite(Number(line.rate)) && Number(line.rate) >= 0 && line.rate !== '')) && Number(days) > 0 && Number(hours) > 0;
  const set = (patch: Partial<typeof line>) => setLine({ ...line, ...patch });
  return (
    <Panel
      title={existing ? `Edit ${text(existing.name) || 'revenue line'}` : 'Add a priced revenue line'}
      kicker="REVENUE WORKSHEET"
      onClose={onClose}
      footer={
        <>
          <button type="button" className="gf-secondary" onClick={onClose}>
            Cancel
          </button>
          <button
            type="button"
            className="gf-primary"
            disabled={!valid || hook.busy || Boolean(state.running)}
            onClick={() =>
              void hook
                .action(async () => {
                  setSaveError('');
                  try {
                  hook.setState(
                    await api<Assessment>(
                      `assessments/${hook.id}/revenue-rates`,
                      post({
                        revision: openingRevision,
                        days_per_year: Number(days),
                        hours_per_day: Number(hours),
                        approve,
                        lines: [
                          {
                            id: existing ? text(existing.id) : 'user-' + crypto.randomUUID(),
                            name: line.name.trim(),
                            kind: line.kind,
                            category: line.category,
                            role: initial?.role || 'main_product',
                            component: initial?.component || null,
                            stream_key: selectedSource?.streamKey || null,
                            rate: selectedSource ? null : Number(line.rate),
                            rate_unit: line.rate_unit,
                            price: Number(line.price),
                            price_unit: line.price_unit,
                            price_period: line.price_period,
                            sold_fraction: Number(line.sold_fraction),
                            saleable_fraction: initial?.saleable_fraction ?? 1,
                            allocation_fraction: initial?.allocation_fraction ?? 1,
                            rationale: line.rationale.trim() || 'User assumption entered in the Revenue playground',
                          },
                        ],
                      }),
                    ),
                  );
                  } catch (error) {
                    setSaveError(error instanceof Error ? error.message : 'Could not save. Your edits are retained.');
                    throw error;
                  }
                })
                .then((ok) => ok && onClose())
            }
          >
            {existing ? approve ? 'Save & recalculate' : 'Save draft' : 'Save line'}
          </button>
        </>
      }
    >
      <p className="gf-muted">{existing ? 'Update this existing line. Saving approved changes recalculates revenue and linked operating costs; the previous version is retained.' : 'Your price is recorded as a user assumption. Python annualises rate × price × operating time.'}</p>
      {saveError && <p className="gf-note" role="alert">{saveError} Your draft is still open.</p>}
      <div className="gf-grid-2">
        <label className="gf-field">
          <span>Name</span>
          <input value={line.name} onChange={(e) => set({ name: e.target.value })} placeholder="e.g. Water treatment fee" />
        </label>
        <label className="gf-field">
          <span>Income type</span>
          <select value={line.category} onChange={(e) => set({ category: e.target.value, kind: e.target.value === 'product_sales' ? 'product' : 'service' })}>
            {categories.map(([v, l]) => (
              <option key={v} value={v}>
                {l}
              </option>
            ))}
          </select>
        </label>
        <label className="gf-field">
          <span>Rate source</span>
          <select value={rateSource} onChange={(e) => {
            const source = sources.find((s) => s.id === e.target.value);
            setRateSource(e.target.value);
            if (source) set({ rate_unit: source.unit, price_unit: source.priceUnit, ...(line.price_unit !== source.priceUnit ? { price: '' } : {}) });
          }}>
            <option value="" disabled>Select a stream…</option>
            {sources.map((source) => <option key={source.id} value={source.id}>{source.name} — {source.rate} {source.unit}</option>)}
            <option value="__manual__">Enter manually…</option>
          </select>
        </label>
        {selectedSource && <div className="gf-field"><span>M&amp;E rate</span><output>{selectedSource.rate} {selectedSource.unit}</output><small>Linked to the selected stream. Python uses its saved rate when calculating revenue.</small></div>}
        {manualRate && <label className="gf-field">
          <span>Rate</span>
          <input type="number" min="0" step="any" value={line.rate} onChange={(e) => set({ rate: e.target.value })} />
        </label>}
        {manualRate && <label className="gf-field">
          <span>Rate unit</span>
          <input value={line.rate_unit} onChange={(e) => set({ rate_unit: e.target.value })} />
        </label>}
        <label className="gf-field">
          <span>Price</span>
          <input type="number" min="0" step="any" value={line.price} onChange={(e) => set({ price: e.target.value })} />
          {initial && <small>Previous price: {text(initial.price)} {text(obj(existing?.price_basis).currency || obj(obj(state.plan?.operating_economics).price_basis).currency)} per {initial.price_unit}</small>}
        </label>
        <label className="gf-field">
          <span>Per unit</span>
          <input value={line.price_unit} onChange={(e) => set({ price_unit: e.target.value })} />
        </label>
        <label className="gf-field">
          <span>Price year</span>
          <input value={line.price_period} onChange={(e) => set({ price_period: e.target.value })} />
        </label>
        <label className="gf-field">
          <span>Share sold (0–1)</span>
          <input type="number" min="0" max="1" step="0.05" value={line.sold_fraction} onChange={(e) => set({ sold_fraction: e.target.value })} />
        </label>
        <label className="gf-field">
          <span>Operating days / year</span>
          <input type="number" min="1" max="366" value={days} onChange={(e) => setDays(e.target.value)} />
        </label>
        <label className="gf-field">
          <span>Hours / day</span>
          <input type="number" min="0.1" max="24" step="any" value={hours} onChange={(e) => setHours(e.target.value)} />
        </label>
      </div>
      <label className="gf-field">
        <span>Basis / evidence</span>
        <input value={line.rationale} onChange={(e) => set({ rationale: e.target.value })} placeholder="Contract term, quote or your assumption" />
      </label>
      <label className="gf-check">
        <input type="checkbox" checked={approve} onChange={(e) => setApprove(e.target.checked)} />
        <span>I approve these revenue assumptions for calculation.</span>
      </label>
    </Panel>
  );
}
