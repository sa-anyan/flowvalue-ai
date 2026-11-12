'use client';
import Link from 'next/link';
import { useEffect, useState } from 'react';
import { assessmentHref } from '@/lib/assessment-navigation';
import { strings, compact, list, money, num, obj, text, words, type Row } from '@/lib/guided-flow';
import { api, post, type Assessment } from './use-assessment';
import { Issues, OriginChip, Panel, RunBar, StageHeading, type StageProps } from './flow';

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
  const [box, setBox] = useState(''),
    [answers, setAnswers] = useState<Record<string, string>>({}),
    [adding, setAdding] = useState(false),
    [research, setResearch] = useState<Row | null>(null);
  useEffect(() => setBox(text(state?.revenue_description)), [state?.id, state?.revenue_description]);
  // An approval prompt is not a clarification: only real questions block approval.
  const questions = (state?.revenue_questions || []).map(String).filter((q) => !/^\s*(data required:\s*)?review and approve/i.test(q));
  const lines: Row[] = [...list(config.sales), ...list(config.commercial_lines)];
  const products = list(result.products);
  const firstYear = list(result.annual)[0];
  const receipt = obj(obj(state?.stage_runs).revenue);
  // A saved approval goes stale when prices, quantities or the schedule change; the stage receipt says so.
  const approvedAt = text(obj(state?.revenue_approval).approved_at);
  const approved =
    Boolean(state?.revenue_approval) &&
    !questions.length &&
    (!/approve/i.test(`${text(receipt.message)} ${strings(stage.issues).join(' ')}`) || (approvedAt !== '' && approvedAt > text(receipt.completed_at)));
  const boxDirty = box !== text(state?.revenue_description);
  const productFor = (id: string) => products.find((p) => text(p.product_id) === id);
  return (
    <div className="gf-play">
      <StageHeading kicker="STAGE 05 · REVENUE" title="Revenue playground">
        Income comes only from your Revenue Box and the explicit revenue worksheet. Prices you give are your assumptions; unpriced income stays unpriced.
      </StageHeading>
      <div className="gf-kpis">
        <div className="gf-kpi-hero">
          <small>Sales revenue · operating year 1</small>
          <strong>{num(obj(firstYear).sales_revenue) === null ? 'Not calculated' : compact(obj(firstYear).sales_revenue)}</strong>
          <span>
            {text(obj(result.basis).currency)} {text(obj(result.basis).price_period)}
          </span>
        </div>
        <div>
          <small>Revenue lines</small>
          <strong>{lines.length}</strong>
          <span>{lines.filter((l) => num(l.unit_price ?? l.price ?? l.rate) === null).length} unpriced</span>
        </div>
        <div>
          <small>Approval</small>
          <strong>{approved ? 'Approved' : 'Pending'}</strong>
          <span>{questions.length ? `${questions.length} open questions` : 'Required before financial results'}</span>
        </div>
      </div>
      <Issues items={[...strings(stage.issues), ...strings(result.issues)]} />

      <section className="gf-card-block" aria-labelledby="gf-box">
        <h2 id="gf-box">Revenue Box</h2>
        <label className="gf-field">
          <span>How does this project earn income?</span>
          <textarea value={box} maxLength={6000} onChange={(e) => setBox(e.target.value)} />
        </label>
        <div className="gf-line-actions">
          <button
            type="button"
            className="gf-secondary"
            disabled={!boxDirty || hook.busy || Boolean(state?.running)}
            onClick={() => void hook.action(async () => hook.setState(await api<Assessment>(`assessments/${hook.id}/revenue-authority`, post({ revision: state!.revision, revenue_description: box }))))}
          >
            Save Revenue Box
          </button>
          <button
            type="button"
            className="gf-primary"
            disabled={approved || boxDirty || questions.length > 0 || hook.busy || Boolean(state?.running)}
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
        {!lines.length && <p className="gf-muted">No revenue lines yet. Describe income in the Revenue Box or add a priced line.</p>}
        <ul className="gf-lines">
          {lines.map((line) => {
            const id = text(line.id),
              product = productFor(id),
              price = num(line.unit_price ?? line.price);
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
                    <strong>{product ? money(product.net_sales_revenue) : 'Not calculated'}</strong>
                    <small>{product ? `${text(product.quantity_sold)} ${text(product.quantity_unit)} sold in year ${text(product.year)}` : 'Recalculate to see income'}</small>
                  </div>
                </div>
                <div className="gf-line-actions">
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
      {adding && state && <AddLine state={state} onClose={() => setAdding(false)} props={props} />}
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

function AddLine({ state, onClose, props }: { state: Assessment; onClose: () => void; props: StageProps }) {
  const { hook } = props;
  const operating = obj(obj(state.plan?.operating_economics).operating);
  const [line, setLine] = useState({
    name: '',
    kind: 'service',
    category: 'processing_services',
    rate: '',
    rate_unit: 'm3/h',
    price: '',
    price_unit: 'm3',
    price_period: String(new Date().getFullYear()),
    sold_fraction: '1',
    rationale: '',
  });
  const [days, setDays] = useState(text(operating.days_per_year || '')),
    [hours, setHours] = useState(text(operating.hours_per_day || '')),
    [approve, setApprove] = useState(false);
  const valid = line.name.trim() && Number(line.price) >= 0 && line.price !== '' && Number(line.rate) >= 0 && line.rate !== '' && Number(days) > 0 && Number(hours) > 0;
  const set = (patch: Partial<typeof line>) => setLine({ ...line, ...patch });
  return (
    <Panel
      title="Add a priced revenue line"
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
                  hook.setState(
                    await api<Assessment>(
                      `assessments/${hook.id}/revenue-rates`,
                      post({
                        revision: state.revision,
                        days_per_year: Number(days),
                        hours_per_day: Number(hours),
                        approve,
                        lines: [
                          {
                            id: 'user-' + line.name.toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 60),
                            name: line.name.trim(),
                            kind: line.kind,
                            category: line.category,
                            rate: Number(line.rate),
                            rate_unit: line.rate_unit,
                            price: Number(line.price),
                            price_unit: line.price_unit,
                            price_period: line.price_period,
                            sold_fraction: Number(line.sold_fraction),
                            rationale: line.rationale.trim() || 'User assumption entered in the Revenue playground',
                          },
                        ],
                      }),
                    ),
                  );
                })
                .then((ok) => ok && onClose())
            }
          >
            Save line
          </button>
        </>
      }
    >
      <p className="gf-muted">Your price is recorded as a user assumption. Python annualises rate × price × operating time.</p>
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
          <span>Rate</span>
          <input type="number" min="0" step="any" value={line.rate} onChange={(e) => set({ rate: e.target.value })} />
        </label>
        <label className="gf-field">
          <span>Rate unit</span>
          <input value={line.rate_unit} onChange={(e) => set({ rate_unit: e.target.value })} />
        </label>
        <label className="gf-field">
          <span>Price</span>
          <input type="number" min="0" step="any" value={line.price} onChange={(e) => set({ price: e.target.value })} />
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
