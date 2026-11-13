'use client';
import { list, money, num, obj, text, type Row, type StageId } from '@/lib/guided-flow';
import { api, post } from './use-assessment';
import type { StageProps } from './flow';

/**
 * Autopilot: one button from extracted data to a full provisional analysis.
 * Results come first; every decision made on the user's behalf is listed for
 * review, and the options stay out of sight until the user opens them.
 */
export function AutopilotCard({ props }: { props: StageProps }) {
  const { hook } = props;
  const state = hook.state;
  const auto = obj(state?.autopilot);
  const status = text(auto.status);
  const busy = hook.busy || Boolean(state?.running) || status === 'queued' || status === 'running';

  async function start() {
    if (!hook.id) return;
    await hook.action(async () => {
      await api(`assessments/${hook.id}/autopilot`, post({ use_ai: hook.aiEnabled && props.aiSizing }));
      hook.reload();
    });
  }

  if (status === 'finished') return <AutopilotResults props={props} onRerun={() => void start()} busy={busy} />;

  return (
    <section className="gf-autopilot" aria-labelledby="gf-ap-h">
      <div>
        <span className="gf-kicker">FASTEST ROUTE</span>
        <h2 id="gf-ap-h">Autopilot: price everything for me</h2>
        <p>
          FlowValue approves the extracted data for a provisional run, picks a cost model for every item, fills missing sizing, CAPEX and OPEX inputs
          {hook.aiEnabled && props.aiSizing ? ' with AI (usage charges apply)' : ' with stated defaults'}, and runs every stage. Python does all the arithmetic.
          You get the results first; everything decided for you is listed to review. Nothing is final, and a restore point is saved first.
        </p>
        {status === 'failed' && <p className="gf-warn">Last Autopilot run stopped: {text(auto.error) || 'unknown error'}</p>}
      </div>
      <button type="button" className="gf-primary gf-autopilot-go" disabled={busy || !hook.id} onClick={() => void start()}>
        {busy && (status === 'queued' || status === 'running') ? 'Autopilot running…' : '⚡ Run Autopilot'}
      </button>
    </section>
  );
}

const STAGE_FOR: Record<string, StageId> = { entry: 'entry', equipment: 'equipment', capex: 'capex', opex: 'opex', revenue: 'revenue', financial: 'financial' };

function AutopilotResults({ props, onRerun, busy }: { props: StageProps; onRerun: () => void; busy: boolean }) {
  const auto = obj(props.hook.state?.autopilot);
  const head = obj(auto.headline);
  const currency = text(head.currency) || 'USD';
  const irr = num(head.irr);
  const tiles: [string, string, string?][] = [
    ['Equipment (purchased)', head.equipment_purchased == null ? 'Incomplete' : `${money(head.equipment_purchased)} ${currency}`,
      `${text(head.equipment_priced ?? '—')} priced · ${text(head.equipment_unpriced ?? 0)} unpriced`],
    ['Total CAPEX', head.total_capex == null ? 'Not calculated' : `${money(head.total_capex)} ${currency}`],
    ['OPEX per year (known)', head.annual_opex == null ? 'Not calculated' : `${money(head.annual_opex)} ${currency}`],
    ['NPV', head.npv == null ? 'Needs revenue' : `${money(head.npv)} ${currency}`, irr === null ? undefined : `IRR ${(irr * 100).toFixed(1)}%`],
  ];
  const review = list(auto.review);
  return (
    <section className="gf-autopilot gf-autopilot-done" aria-labelledby="gf-apr-h">
      <div className="gf-autopilot-head">
        <div>
          <span className="gf-kicker">AUTOPILOT RESULTS · PROVISIONAL</span>
          <h2 id="gf-apr-h">Your analysis is ready to review</h2>
        </div>
        <button type="button" className="gf-secondary" disabled={busy} onClick={onRerun}>
          Run again
        </button>
      </div>
      <div className="gf-autopilot-tiles">
        {tiles.map(([label, value, note]) => (
          <div key={label} className="gf-autopilot-tile">
            <small>{label}</small>
            <strong>{value}</strong>
            {note && <small>{note}</small>}
          </div>
        ))}
      </div>
      {review.length > 0 && (
        <details className="gf-autopilot-review">
          <summary>
            {review.length} thing{review.length === 1 ? '' : 's'} decided for you · review when you want
          </summary>
          <ul>
            {review.map((item: Row, i: number) => (
              <li key={i} className={`gf-review-${text(item.kind)}`}>
                <span>{text(item.text)}</span>
                {list(item.items).length > 0 && <small>{(item.items as unknown[]).map(String).slice(0, 12).join(', ')}</small>}
                {STAGE_FOR[text(item.stage)] && (
                  <button type="button" className="gf-link" onClick={() => props.go(STAGE_FOR[text(item.stage)])}>
                    Review
                  </button>
                )}
              </li>
            ))}
          </ul>
        </details>
      )}
    </section>
  );
}
