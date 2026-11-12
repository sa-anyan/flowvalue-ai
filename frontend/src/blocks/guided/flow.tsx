'use client';
import Link from 'next/link';
import { useCallback, useEffect, useRef, useState } from 'react';
import { assessmentHref } from '@/lib/assessment-navigation';
import { stableJson } from '@/lib/stable-json';
import {
  direction,
  forwardRun,
  guidedStages,
  isStage,
  nextStage,
  obj,
  stageIndex,
  stageStatus,
  type Row,
  type StageId,
} from '@/lib/guided-flow';
import { api, post, useAssessment, type AssessmentHook } from './use-assessment';
import { EntryBoard } from './entry-board';
import { EquipmentPlayground } from './equipment-playground';
import { CapexPlayground } from './capex-playground';
import { OpexPlayground } from './opex-playground';
import { RevenuePlayground } from './revenue-playground';
import { FinancialPlayground } from './financial-playground';
import './guided.css';

/** One saved plan section with local, unsaved edits. Python owns every calculated value. */
export type Draft<T = unknown> = {
  value: T;
  set: (next: T) => void;
  dirty: boolean;
  reset: () => void;
  save: (rationale: string) => Promise<void>;
};
function useDraft<T>(hook: AssessmentHook, section: string, fallback: T): Draft<T> {
  const saved = (hook.state?.plan?.[section] ?? fallback) as T;
  const [value, setValue] = useState<T>(saved);
  useEffect(() => {
    setValue(saved);
    // Reset only when a new saved revision arrives.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hook.state?.id, hook.state?.revision]);
  const dirty = stableJson(value) !== stableJson(saved);
  return {
    value,
    set: setValue,
    dirty,
    reset: () => setValue(saved),
    save: async (rationale: string) => {
      if (dirty) await hook.saveSection(section, value, rationale);
    },
  };
}

export type StageProps = {
  hook: AssessmentHook;
  equipment: Draft<Row[]>;
  capex: Draft<Row>;
  operating: Draft<Row>;
  /**
   * Saves (via `prepare`), optionally recalculates stale upstream stages first
   * (`upstream`, waiting for Python to finish), runs the next backend stage, then moves forward.
   */
  advance: (prepare?: () => Promise<void>, upstream?: string[]) => Promise<void>;
  go: (stage: StageId) => void;
  /** Let the AI propose missing sizing inputs when equipment runs (provisional, reviewable). */
  aiSizing: boolean;
  setAiSizing: (on: boolean) => void;
};

export function GuidedFlow() {
  const hook = useAssessment();
  const equipment = useDraft<Row[]>(hook, 'equipment', []);
  const capex = useDraft<Row>(hook, 'capex', {});
  const operating = useDraft<Row>(hook, 'operating_economics', {});
  const [aiSizing, setAiSizing] = useState(true);
  const [stage, setStage] = useState<StageId>('entry'),
    [dir, setDir] = useState<'forward' | 'back'>('forward'),
    [dark, setDark] = useState(false),
    [moved, setMoved] = useState(false);
  const title = useRef<HTMLDivElement>(null);
  const stageRef = useRef<StageId>('entry');
  stageRef.current = stage;
  useEffect(() => {
    const requested = new URL(window.location.href).searchParams.get('stage');
    if (isStage(requested)) setStage(requested);
    setDark(localStorage.getItem('flowvalue-theme') === 'dark');
    const back = () => {
      const next = new URL(window.location.href).searchParams.get('stage');
      const target = isStage(next) ? next : 'entry';
      setDir(direction(stageRef.current, target));
      setStage(target);
      setMoved(true);
    };
    window.addEventListener('popstate', back);
    return () => window.removeEventListener('popstate', back);
  }, []);
  useEffect(() => {
    // Move keyboard and screen-reader focus to the new stage after a user-driven transition.
    if (moved) title.current?.focus({ preventScroll: true });
  }, [stage, moved]);
  const go = useCallback((target: StageId) => {
    const current = stageRef.current;
    if (current === target) return;
    setDir(direction(current, target));
    setStage(target);
    const url = new URL(window.location.href);
    url.searchParams.set('stage', target);
    window.history.pushState({ stage: target }, '', url.pathname + url.search);
    setMoved(true);
    window.scrollTo({ top: 0, behavior: 'auto' });
  }, []);
  const advance = useCallback(
    async (prepare?: () => Promise<void>, upstream: string[] = []) => {
      const target = nextStage(stage),
        backend = forwardRun(stage);
      if (!target || !backend) return;
      const ok = await hook.action(async () => {
        if (prepare) await prepare();
        for (const name of upstream) {
          await api(`assessments/${hook.id}/stages/${name}/run`, post({ use_ai: false }));
          await waitUntilIdle(hook.id);
        }
        // Only the equipment run may use AI, and only to propose missing sizing inputs.
        const useAi = backend === 'equipment' && aiSizing && hook.aiEnabled;
        await api(`assessments/${hook.id}/stages/${backend}/run`, post({ use_ai: useAi }));
      });
      if (ok) go(target);
    },
    [stage, hook, go, aiSizing],
  );
  const state = hook.state,
    receipts = obj(state?.stage_runs),
    stages = obj(obj(state?.results).stages);
  const props: StageProps = { hook, equipment, capex, operating, advance, go, aiSizing, setAiSizing };
  const current = guidedStages[stageIndex(stage)];
  return (
    <div className={`gf ${dark ? 'dark' : ''}`} data-stage={stage}>
      <a className="skip-link" href="#gf-stage">
        Skip to {current.label}
      </a>
      <div className="gf-top">
        <Link className="gf-brand" href={assessmentHref('/flow', hook.id)}>
          ≋ flowvalue <small>AI</small>
        </Link>
        <nav className="gf-rail" aria-label="Assessment stages">
          <ol>
            {guidedStages.map((s, i) => {
              const status = s.id === 'entry' ? null : stageStatus(receipts[s.id], stages[s.id]);
              return (
                <li key={s.id}>
                  <button
                    type="button"
                    aria-current={stage === s.id ? 'step' : undefined}
                    disabled={!hook.id && s.id !== 'entry'}
                    onClick={() => go(s.id)}
                  >
                    <span className="gf-rail-n">{String(i + 1).padStart(2, '0')}</span>
                    <span>{s.label}</span>
                    {status && <i className={`gf-dot gf-${status.tone}`} title={status.label} aria-label={status.label} />}
                  </button>
                </li>
              );
            })}
          </ol>
        </nav>
        <div className="gf-top-actions">
          {state && <span className="gf-project" title={state.filename}>{state.filename}</span>}
          <Link className="gf-ghost" href={assessmentHref('/data/equipment', hook.id)}>
            Advanced workspace ↗
          </Link>
          <button
            type="button"
            className="gf-icon"
            aria-label={dark ? 'Switch to light mode' : 'Switch to dark mode'}
            onClick={() => {
              setDark(!dark);
              localStorage.setItem('flowvalue-theme', !dark ? 'dark' : 'light');
            }}
          >
            {dark ? '☀' : '☾'}
          </button>
        </div>
      </div>
      {state?.running && <RunProgress id={hook.id} fallback={String(state.status || 'Python is calculating')} />}
      {state?.parent_version && (
        <p className="gf-banner" role="note">
          You are editing a <strong>scenario copy</strong>. The baseline assessment is unchanged.
        </p>
      )}
      {hook.error && (
        <p className="gf-error" role="alert">
          {hook.error}
          <button type="button" className="gf-link" onClick={() => hook.setError('')}>
            Dismiss
          </button>
        </p>
      )}
      <main id="gf-stage" key={stage} className={`gf-stage gf-enter-${dir}`} aria-labelledby="gf-stage-title">
        <div ref={title} id="gf-stage-title" tabIndex={-1} className="gf-sr-only">
          {current.title}
        </div>
        {stage === 'entry' && <EntryBoard {...props} />}
        {stage === 'equipment' && <EquipmentPlayground {...props} />}
        {stage === 'capex' && <CapexPlayground {...props} />}
        {stage === 'opex' && <OpexPlayground {...props} />}
        {stage === 'revenue' && <RevenuePlayground {...props} />}
        {stage === 'financial' && <FinancialPlayground {...props} />}
      </main>
    </div>
  );
}

const STAGE_LABEL: Record<string, string> = {
  engineering_data: 'Reading engineering data',
  equipment_preparation: 'Preparing equipment',
  equipment: 'Pricing equipment',
  capex: 'Calculating CAPEX',
  opex: 'Calculating OPEX',
  revenue: 'Calculating revenue',
  financial: 'Calculating cash flow',
};

/** Live progress of the running stage: step, count and elapsed time (polled from memory, about once a second). */
export function RunProgress({ id, fallback }: { id: string; fallback: string }) {
  const [live, setLive] = useState<Row | null>(null);
  useEffect(() => {
    let disposed = false,
      timer: ReturnType<typeof setTimeout>;
    async function poll() {
      try {
        const next = await api<Row>(`assessments/${id}/progress`);
        if (!disposed) setLive(next);
      } catch {
        /* keep the last known step */
      }
      if (!disposed) timer = setTimeout(poll, 1000);
    }
    void poll();
    return () => {
      disposed = true;
      clearTimeout(timer);
    };
  }, [id]);
  const done = typeof live?.done === 'number' ? live.done : null,
    total = typeof live?.total === 'number' && live.total > 0 ? live.total : null;
  const share = done !== null && total ? Math.min(1, done / total) : null;
  const seconds = typeof live?.elapsed_seconds === 'number' ? Math.round(live.elapsed_seconds) : null;
  const elapsed = seconds === null ? '' : `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`;
  const stage = STAGE_LABEL[String(live?.stage)] || '';
  return (
    <div className="gf-running" role="status" aria-live="polite">
      <i aria-hidden="true" />
      <span className="gf-progress-text">
        <b>{live?.running ? stage || fallback : fallback}</b>
        {live?.running && live.step ? <span> · {String(live.step)}{total ? ` · ${done} of ${total}` : ''}</span> : null}
      </span>
      <span
        className={`gf-progress ${share === null ? 'gf-progress-busy' : ''}`}
        role="progressbar"
        aria-label="Calculation progress"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={share === null ? undefined : Math.round(share * 100)}
      >
        <span style={share === null ? undefined : { width: `${Math.max(4, share * 100)}%` }} />
      </span>
      {elapsed && <span className="gf-progress-time">{elapsed}</span>}
    </div>
  );
}

/** Polls until the backend reports no running stage (Python owns the work; the browser only waits). */
async function waitUntilIdle(id: string, timeoutMs = 180000) {
  const started = Date.now();
  for (;;) {
    const state = await api<Row>('assessments/' + id);
    if (!state.running) return state;
    if (Date.now() - started > timeoutMs) throw new Error('Python is still calculating; try again when it finishes.');
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }
}

/** Sticky bottom bar with the forward run button every stage shares. */
export function RunBar({
  status,
  label,
  note,
  disabled,
  busy,
  onRun,
  back,
  children,
}: {
  status?: React.ReactNode;
  label: string;
  note?: string;
  disabled?: boolean;
  busy?: boolean;
  onRun: () => void;
  back?: { label: string; onClick: () => void };
  children?: React.ReactNode;
}) {
  return (
    <div className="gf-runbar" role="region" aria-label="Stage actions">
      {back && (
        <button type="button" className="gf-ghost" onClick={back.onClick}>
          ← {back.label}
        </button>
      )}
      <div className="gf-runbar-status">
        {status}
        {note && <small>{note}</small>}
      </div>
      {children}
      <button type="button" className="gf-primary gf-run" disabled={disabled || busy} onClick={onRun}>
        {busy ? 'Working…' : label} <span aria-hidden="true">→</span>
      </button>
    </div>
  );
}

/** Accessible modal panel used by inspectors and confirmations. */
export function Panel({
  title,
  kicker,
  onClose,
  children,
  footer,
  wide,
}: {
  title: string;
  kicker?: string;
  onClose: () => void;
  children: React.ReactNode;
  footer?: React.ReactNode;
  wide?: boolean;
}) {
  const dialog = useRef<HTMLDivElement>(null),
    close = useRef<HTMLButtonElement>(null),
    closeHandler = useRef(onClose);
  closeHandler.current = onClose;
  // Runs once per opening, so typing inside the panel never moves focus.
  useEffect(() => {
    const before = document.activeElement as HTMLElement | null,
      overflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    close.current?.focus();
    const key = (e: KeyboardEvent) => {
      if (e.key === 'Escape') closeHandler.current();
      if (e.key !== 'Tab') return;
      const nodes = Array.from(
        dialog.current?.querySelectorAll<HTMLElement>('button,a[href],input,select,textarea,summary,[tabindex="0"]') || [],
      ).filter((n) => !n.hasAttribute('disabled') && n.getClientRects().length);
      if (!nodes.length) return;
      const first = nodes[0],
        last = nodes[nodes.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };
    window.addEventListener('keydown', key);
    return () => {
      window.removeEventListener('keydown', key);
      document.body.style.overflow = overflow;
      before?.focus();
    };
  }, []);
  return (
    <div
      className="gf-backdrop"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div ref={dialog} className={`gf-panel ${wide ? 'gf-panel-wide' : ''}`} role="dialog" aria-modal="true" aria-label={title}>
        <div className="gf-panel-head">
          <div>
            {kicker && <span className="gf-kicker">{kicker}</span>}
            <h2>{title}</h2>
          </div>
          <button ref={close} type="button" className="gf-icon" aria-label="Close" onClick={onClose}>
            ✕
          </button>
        </div>
        <div className="gf-panel-body">{children}</div>
        {footer && <div className="gf-panel-foot">{footer}</div>}
      </div>
    </div>
  );
}

export function OriginChip({ origin }: { origin: string }) {
  const tone = /ai|provisional/i.test(origin) ? 'ai' : /you|user/i.test(origin) ? 'user' : /m&e|balance|source/i.test(origin) ? 'source' : 'neutral';
  return <span className={`gf-chip gf-chip-${tone}`}>{origin}</span>;
}

export function StageHeading({ kicker, title, children, aside }: { kicker: string; title: string; children?: React.ReactNode; aside?: React.ReactNode }) {
  return (
    <div className="gf-heading">
      <div>
        <span className="gf-kicker">{kicker}</span>
        <h1>{title}</h1>
        {children && <p>{children}</p>}
      </div>
      {aside}
    </div>
  );
}

export function Issues({ items, title = 'Needs your input' }: { items: unknown; title?: string }) {
  const list = (Array.isArray(items) ? items : []).map(String).filter(Boolean);
  if (!list.length) return null;
  return (
    <div className="gf-issues" role="status">
      <strong>{title}</strong>
      <ul>
        {list.slice(0, 12).map((issue, i) => (
          <li key={i}>{issue}</li>
        ))}
      </ul>
      {list.length > 12 && <small>{list.length - 12} more in the advanced workspace.</small>}
    </div>
  );
}
