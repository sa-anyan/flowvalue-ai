'use client';
import { useCallback, useEffect, useRef, useState } from 'react';
import { assessmentFromUrl, assessmentHref } from '@/lib/assessment-navigation';
import { obj, type Row } from '@/lib/guided-flow';

export type Assessment = Row & {
  id: string;
  revision: number;
  filename: string;
  running: boolean;
  plan: Row;
  results?: Row | null;
  stage_runs?: Record<string, Row>;
  engineering_data_approved?: boolean;
  assumption_register?: Row[];
  research_drafts?: Row[];
  research_job?: Row;
  revenue_description?: string;
  revenue_questions?: string[];
  parent_version?: string;
  error?: string;
  status?: string;
};

export async function api<T = Row>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch('/api/' + path, { ...options, cache: 'no-store', signal: options?.signal ?? AbortSignal.timeout(20000) });
  const value = await response.json().catch(() => ({ detail: response.ok ? undefined : `The server returned an error (HTTP ${response.status}). Nothing was changed.` }));
  if (response.status === 401 && typeof window !== 'undefined') window.location.assign('/login');
  if (!response.ok) {
    const detail = (value as Row).detail;
    throw new Error(
      typeof detail === 'string'
        ? detail
        : Array.isArray(detail)
          ? detail.map((d) => `${(obj(d).loc as unknown[] | undefined)?.join(' › ') ?? ''} ${String(obj(d).msg ?? '')}`.trim()).join('; ')
          : 'Request failed',
    );
  }
  return value as T;
}
export const post = (value: unknown): RequestInit => ({ method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(value) });
export const patch = (value: unknown): RequestInit => ({ method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(value) });

/** Loads one assessment and keeps polling while a Python stage is running. */
export function useAssessment() {
  const [id, setId] = useState(''),
    [state, setState] = useState<Assessment | null>(null),
    [error, setError] = useState(''),
    [loading, setLoading] = useState(true),
    [busy, setBusy] = useState(false),
    [catalogue, setCatalogue] = useState<Row[]>([]),
    [aiStatus, setAiStatus] = useState<'checking' | 'enabled' | 'disabled' | 'unavailable'>('checking'),
    [tick, setTick] = useState(0);
  const alive = useRef(true);
  const aiEnabled = aiStatus === 'enabled';
  useEffect(() => {
    alive.current = true;
    const selected = assessmentFromUrl(window.location.href, localStorage.getItem('flowvalue-assessment'));
    if (selected) localStorage.setItem('flowvalue-assessment', selected);
    setId(selected);
    setLoading(Boolean(selected));
    void api<Row>('catalogue')
      .then((c) => setCatalogue(Array.isArray(c.equipment) ? (c.equipment as Row[]) : []))
      .catch(() => {});
    return () => {
      alive.current = false;
    };
  }, []);
  useEffect(() => {
    let disposed = false;
    let timer: ReturnType<typeof setTimeout>;
    let checking = false;
    async function checkAI() {
      if (checking || disposed) return;
      checking = true;
      clearTimeout(timer);
      let delay = 30000;
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 5000);
      try {
        const health = await api<Row>('health', { signal: controller.signal });
        if (typeof health.ai_enabled !== 'boolean') throw new Error('AI availability was not returned');
        if (!disposed) setAiStatus(health.ai_enabled ? 'enabled' : 'disabled');
      } catch {
        if (!disposed) setAiStatus('unavailable');
        delay = 3000;
      } finally {
        clearTimeout(timeout);
        checking = false;
        if (!disposed) timer = setTimeout(checkAI, delay);
      }
    }
    void checkAI();
    const onFocus = () => void checkAI();
    window.addEventListener('focus', onFocus);
    return () => { disposed = true; clearTimeout(timer); window.removeEventListener('focus', onFocus); };
  }, []);
  useEffect(() => {
    if (!id) {
      setState(null);
      return;
    }
    let disposed = false,
      timer: ReturnType<typeof setTimeout>;
    async function refresh() {
      setLoading(true);
      try {
        const next = await api<Assessment>('assessments/' + id);
        if (disposed) return;
        setState(next);
        const auto = (next as Row).autopilot as Row | undefined;
        const brainstorm = (next as Row).opex_brainstorm as Row | undefined;
        const launch = (next as Row).launch as Row | undefined;
        if (next.running || auto?.status === 'queued' || auto?.status === 'running') timer = setTimeout(refresh, 1200);
        // Save & go: follow the background run quietly until it finishes.
        else if (launch?.status === 'queued' || launch?.status === 'running' || (next as Row).launch_running) timer = setTimeout(refresh, 2000);
        // Background AI research: check back slowly until its proposals are saved.
        else if (brainstorm?.status === 'running' || brainstorm?.pending_application === true || Object.values(((next as Row).analyst as Row) || {}).some((r) => (r as Row)?.status === 'running' || (r as Row)?.pending_application === true))
          timer = setTimeout(refresh, 4000);
      } catch (e) {
        if (!disposed) setError((e as Error).name === 'TimeoutError' ? 'Loading the saved project timed out. Please retry.' : (e as Error).message);
      } finally {
        if (!disposed) setLoading(false);
      }
    }
    void refresh();
    return () => {
      disposed = true;
      clearTimeout(timer);
    };
  }, [id, tick]);
  const select = useCallback((key: string) => {
    window.history.replaceState(window.history.state, '', assessmentHref(window.location.pathname + window.location.search, key));
    localStorage.setItem('flowvalue-assessment', key);
    setError('');
    setId(key);
  }, []);
  /** Leaves the current study for a blank board: clears the URL, the remembered study and the loaded data. */
  const clear = useCallback(() => {
    const url = new URL(window.location.href);
    url.searchParams.delete('assessment');
    window.history.replaceState(window.history.state, '', url.pathname + url.search + url.hash);
    localStorage.removeItem('flowvalue-assessment');
    setError('');
    setState(null);
    setId('');
  }, []);
  /** Re-reads the assessment (and restarts polling if a stage was queued). */
  const reload = useCallback(() => setTick((t) => t + 1), []);
  const actionPending = useRef(false);
  const action = useCallback(async (work: () => Promise<unknown>) => {
    if (actionPending.current) return false;
    actionPending.current = true;
    setError('');
    setBusy(true);
    try {
      await work();
      return true;
    } catch (e) {
      if (alive.current) setError((e as Error).message);
      return false;
    } finally {
      actionPending.current = false;
      if (alive.current) setBusy(false);
      setTick((t) => t + 1);
    }
  }, []);
  /** Saves one plan section with an explicit rationale (Python validates it). */
  const saveSection = useCallback(
    async (section: string, value: unknown, rationale: string) => {
      if (!state) throw new Error('Open an assessment first.');
      const next = await api<Assessment>('assessments/' + state.id, patch({ revision: state.revision, section, value, rationale }));
      setState(next);
      return next;
    },
    [state],
  );
  const runStage = useCallback(
    async (stage: string) => {
      if (!id) throw new Error('Open an assessment first.');
      // Financial may fill absent planning assumptions; complete saved policies
      // recalculate deterministically without another AI request.
      await api(`assessments/${id}/stages/${stage}/run`, post({ use_ai: stage === 'financial' && aiEnabled }));
    },
    [id, aiEnabled],
  );
  return { id, state, setState, loading, error, setError, busy, catalogue, aiEnabled, aiStatus, select, clear, reload, action, saveSection, runStage };
}
export type AssessmentHook = ReturnType<typeof useAssessment>;
