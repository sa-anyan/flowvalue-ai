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
  const response = await fetch('/api/' + path, { ...options, cache: 'no-store' });
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
    [busy, setBusy] = useState(false),
    [catalogue, setCatalogue] = useState<Row[]>([]),
    [aiEnabled, setAiEnabled] = useState(false),
    [tick, setTick] = useState(0);
  const alive = useRef(true);
  useEffect(() => {
    alive.current = true;
    const selected = assessmentFromUrl(window.location.href, localStorage.getItem('flowvalue-assessment'));
    if (selected) localStorage.setItem('flowvalue-assessment', selected);
    setId(selected);
    void api<Row>('catalogue')
      .then((c) => setCatalogue(Array.isArray(c.equipment) ? (c.equipment as Row[]) : []))
      .catch(() => {});
    void api<Row>('health')
      .then((h) => setAiEnabled(h.ai_enabled === true))
      .catch(() => {});
    return () => {
      alive.current = false;
    };
  }, []);
  useEffect(() => {
    if (!id) {
      setState(null);
      return;
    }
    let disposed = false,
      timer: ReturnType<typeof setTimeout>;
    async function refresh() {
      try {
        const next = await api<Assessment>('assessments/' + id);
        if (disposed) return;
        setState(next);
        const auto = (next as Row).autopilot as Row | undefined;
        if (next.running || auto?.status === 'queued' || auto?.status === 'running') timer = setTimeout(refresh, 1200);
      } catch (e) {
        if (!disposed) setError((e as Error).message);
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
  const action = useCallback(async (work: () => Promise<unknown>) => {
    setError('');
    setBusy(true);
    try {
      await work();
      return true;
    } catch (e) {
      if (alive.current) setError((e as Error).message);
      return false;
    } finally {
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
      await api(`assessments/${id}/stages/${stage}/run`, post({ use_ai: false }));
    },
    [id],
  );
  return { id, state, setState, error, setError, busy, catalogue, aiEnabled, select, clear, reload, action, saveSection, runStage };
}
export type AssessmentHook = ReturnType<typeof useAssessment>;
