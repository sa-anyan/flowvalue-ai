'use client';
import { list, obj, percent, strings, text, words, type Row } from '@/lib/guided-flow';
import { api, post, type AssessmentHook } from './use-assessment';
import { EvidenceNote } from './evidence-note';
import { AICitations } from './ai-citations';

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
  const questions = strings(record.questions);
  const ready = view === 'ready' || view === 'updating';
  const content = <>
      <div className="gf-analyst-head">
        <span className="gf-analyst-mark" aria-hidden="true">✦</span>
        <div className="gf-analyst-heading"><strong>Analysis insights</strong>
          <small>{view === 'researching' ? 'Reviewing your data…' : view === 'updating' ? 'Updating insights…' : view === 'failed' ? 'Analysis unavailable' : record.pending_application === true ? 'AI research finished · applies after the current calculation' : points.length + ' findings · open any to explore'}</small>
        </div>
        <details className="gf-analyst-full"><summary>Full analysis ↗</summary>
          <div className="gf-analyst-full-body">
            {headline && <strong>{headline}</strong>}
            <p>{text(record.summary) || 'No summary is available yet.'}</p><AICitations citations={list(record.citations).filter(c=>strings(record.summary_source_ids).includes(text(c.id)))}/>
            {factors.length > 0 && <details><summary>Factor reasoning ({factors.length})</summary>
              <ul>{factors.map((f, i) => <li key={text(f.id) || i}><strong>{words(text(f.id))} · {percent(f.fraction)}</strong> ({text(f.position)} of range{record.pending_application === true ? ', awaiting application' : strings(record.applied).includes(text(f.id)) ? ', applied' : ', not applied'}) {strings(f.reasoning).join(' ')}<AICitations citations={list(f.citations)} basis={f.basis}/></li>)}</ul>
            </details>}
            {questions.length > 0 && <details><summary>Questions to confirm ({questions.length})</summary><ul>{questions.map((q, i) => <li key={i}>{q}</li>)}</ul></details>}
          </div>
        </details>
      </div>
      {list(record.citations).length > 0 && <details className="gf-analyst-source-list"><summary>AI retrieved sources ({list(record.citations).filter(c=>['retrieved','document_retrieved'].includes(text(c.status))).length})</summary><AICitations citations={list(record.citations)}/>{list(record.citations).map((c,i)=><p key={text(c.id)||i}><strong>{text(c.title)}</strong><br/>{text(c.claim)}<br/><small>{text(c.locator)} · {text(c.access_limitation)} · {text(c.limitation)}{c.retrieved_at ? ` · Retrieved ${text(c.retrieved_at)}` : ''}</small></p>)}</details>}
      {list(record.assumptions).length>0 && <details className="gf-analyst-assumptions"><summary>Assumptions &amp; their evidence ({list(record.assumptions).length})</summary>{list(record.assumptions).map((a,i)=><details key={text(a.id)||i}><summary>{text(a.subject)} · {text(a.value)} {text(a.unit)}</summary><p>{text(a.rationale)}</p><AICitations citations={list(a.citations)} basis={a.basis}/></details>)}</details>}
      {view === 'researching' && <div className="gf-analyst-skeleton" aria-hidden="true"><span /><span /></div>}
      {view === 'failed' && <div className="gf-analyst-failure"><span>Existing calculations remain available.</span><button type="button" className="gf-link" onClick={() => void hook.action(async () => { await api('assessments/' + hook.id + '/analyst', post({})); hook.reload(); })}>Try again</button></div>}
      {ready && (
        <div className="gf-analyst-insight-grid">
          {points.slice(0, 3).map((p, i) => {
            const why = strings(p.why);
            const conditions = strings(p.would_change_if);
            const evidence = strings(p.evidence);
            return <details className="gf-analyst-insight" key={i}>
              <summary><span className="gf-analyst-insight-index">{String(i + 1).padStart(2, '0')}</span><span className="gf-analyst-insight-title">{text(p.title) || 'Finding'}</span><span className="gf-analyst-insight-chevron" aria-hidden="true">⌄</span></summary>
              <div className="gf-analyst-insight-body">
                <p>{text(p.text)}</p><AICitations citations={list(p.citations)} basis={p.basis}/>
                {why.length > 0 && <><strong>Why it matters</strong><ul>{why.map((w, j) => <li key={j}>{w}</li>)}</ul></>}
                {conditions.length > 0 && <><strong>What would change this?</strong><ul>{conditions.map((w, j) => <li key={j}>{w}</li>)}</ul></>}
                <EvidenceNote label="Trace this insight" evidence={evidence} source={p.source || p.sources} record={{ finding: p, analysis_finished: record.finished_at, model: record.model, stale: record.stale, pending_application: record.pending_application }} />
              </div>
            </details>;
          })}
          {points.length === 0 && <p className="gf-muted">No individual findings were returned. Open the full analysis to read the summary.</p>}
          {points.length > 3 && <details className="gf-analyst-insight gf-analyst-more"><summary>+{points.length - 3} more findings <span aria-hidden="true">⌄</span></summary><div className="gf-analyst-insight-body">{points.slice(3).map((p, i) => <details key={i}><summary>{text(p.title)}</summary><p>{text(p.text)}</p><AICitations citations={list(p.citations)} basis={p.basis}/>{strings(p.why).map((w, j) => <p key={j}>{w}</p>)}<EvidenceNote label="Trace this insight" evidence={strings(p.evidence)} source={p.source || p.sources} record={{ finding: p, analysis_finished: record.finished_at, stale: record.stale }} /></details>)}</div></details>}
        </div>
      )}
  </>;
  const brief = ['capex', 'opex', 'revenue'].includes(stage);
  return (
    <section className={"gf-analyst gf-analyst-" + view + " gf-analyst-compact"} aria-label="Analyst insights" aria-busy={view === 'researching'}>
      {brief ? <details className="gf-analyst-holder">
        <summary className="gf-analyst-head">
          <span className="gf-analyst-mark" aria-hidden="true">✦</span>
          <strong>Analyst briefing</strong>
          <small>{view === 'researching' ? 'Researching' : view === 'updating' ? 'Updating' : view === 'failed' ? 'Review unavailable' : record.pending_application === true ? 'Awaiting application' : `${points.length} findings`}</small>
          <span className="gf-analyst-chevron" aria-hidden="true">⌄</span>
        </summary>
        <div className="gf-analyst-holder-body">{content}</div>
      </details> : content}
    </section>
  );
}

/** True while any stage's analyst research is in flight (for slower polling). */
export function analystRunning(state: Row | null | undefined): boolean {
  return Object.values(obj(obj(state).analyst)).some((r) => obj(r).status === 'running' || obj(r).pending_application === true);
}
