'use client';
import { list, obj, percent, strings, text, words, type Row } from '@/lib/guided-flow';
import { api, post, type AssessmentHook } from './use-assessment';

/** What the analyst slot shows for one stage (pure; tested without React). */
export function analystView(record: unknown, aiEnabled: boolean): 'off' | 'researching' | 'ready' | 'updating' | 'failed' {
  const r = obj(record);
  if (!aiEnabled && !r.summary) return 'off';
  if (r.status === 'running') return r.summary ? 'updating' : 'researching';
  if (r.status === 'failed') return 'failed';
  if (r.summary) return 'ready';
  return 'researching';
}

/**
 * The analyst's briefing for one stage, in a slot reserved from the start so the
 * page never jumps: a quiet placeholder while the background research runs,
 * then the summary, filled in place. Python's figure (`headline`) leads; the AI
 * explains the reasoning and never states calculated totals.
 */
export function AnalystCard({ stage, hook, headline }: { stage: string; hook: AssessmentHook; headline?: string }) {
  const record = obj(obj(obj(hook.state).analyst)[stage]);
  const view = analystView(record, hook.aiEnabled);
  if (view === 'off') return null;
  const points = list(record.points);
  const factors = list(record.factors);
  return (
    <section className={`gf-analyst gf-analyst-${view}`} aria-live="polite" aria-busy={view === 'researching'} aria-label="Analyst summary">
      <div className="gf-analyst-head">
        <span className="gf-kicker">ANALYST</span>
        {view === 'updating' && <small className="gf-muted">Updating for your latest inputs…</small>}
        {view === 'ready' && record.cached !== true && text(record.finished_at) && <small className="gf-muted">Researched in the background</small>}
      </div>
      {view === 'researching' && (
        <div className="gf-analyst-skeleton" aria-hidden="true">
          <span />
          <span />
          <span />
        </div>
      )}
      {view === 'researching' && <p className="gf-sr-only">The analyst is researching this stage in the background.</p>}
      {view === 'failed' && (
        <p className="gf-muted">
          The analyst could not finish this stage; the figures below use the reference defaults.{' '}
          <button type="button" className="gf-link" onClick={() => void hook.action(async () => { await api(`assessments/${hook.id}/analyst`, post({})); hook.reload(); })}>
            Try again
          </button>
        </p>
      )}
      {(view === 'ready' || view === 'updating') && (
        <>
          <p className="gf-analyst-summary">
            {headline && <strong>{headline} </strong>}
            {text(record.summary)}
          </p>
          {points.length > 0 && (
            <ul className="gf-analyst-points">
              {points.slice(0, 3).map((p, i) => (
                <li key={i}>
                  <strong>{text(p.title)}:</strong> {text(p.text)}
                  {(strings(p.why).length > 0 || strings(p.would_change_if).length > 0) && (
                    <details>
                      <summary>Why</summary>
                      <ul>
                        {strings(p.why).map((w) => (
                          <li key={w}>{w}</li>
                        ))}
                      </ul>
                      {strings(p.would_change_if).length > 0 && (
                        <>
                          <small className="gf-muted">Would change if</small>
                          <ul>
                            {strings(p.would_change_if).map((w) => (
                              <li key={w}>{w}</li>
                            ))}
                          </ul>
                        </>
                      )}
                      {strings(p.evidence).length > 0 && <small className="gf-muted">From: {strings(p.evidence).join(', ')}</small>}
                    </details>
                  )}
                </li>
              ))}
            </ul>
          )}
          {points.length > 3 && (
            <details className="gf-analyst-factors">
              <summary>More ({points.length - 3})</summary>
              <ul>
                {points.slice(3).map((p, i) => (
                  <li key={i}>
                    <strong>{text(p.title)}:</strong> {text(p.text)}
                  </li>
                ))}
              </ul>
            </details>
          )}
          {factors.length > 0 && (
            <details className="gf-analyst-factors">
              <summary>Why these factor positions ({factors.length})</summary>
              <ul>
                {factors.map((f) => (
                  <li key={text(f.id)}>
                    <strong>
                      {words(text(f.id))} · {percent(f.fraction)}
                    </strong>{' '}
                    <span className="gf-muted">({text(f.position)} of range{strings(record.applied).includes(text(f.id)) ? ', applied' : ', not applied: your value stays'})</span>
                    {strings(f.reasoning).length > 0 && <span> — {strings(f.reasoning).join(' ')}</span>}
                  </li>
                ))}
              </ul>
            </details>
          )}
          {strings(record.questions).length > 0 && (
            <p className="gf-muted gf-analyst-questions">Worth confirming: {strings(record.questions).join(' · ')}</p>
          )}
        </>
      )}
    </section>
  );
}

/** True while any stage's analyst research is in flight (for slower polling). */
export function analystRunning(state: Row | null | undefined): boolean {
  return Object.values(obj(obj(state).analyst)).some((r) => obj(r).status === 'running');
}
