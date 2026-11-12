'use client';
import { useEffect, useMemo, useState } from 'react';
import { obj, patchEquipment, text, userModelSelection, type Row } from '@/lib/guided-flow';

const strings = (v: unknown): string[] => (Array.isArray(v) ? v.map(String) : []);
import { api } from './use-assessment';
import { Panel, type StageProps } from './flow';

/**
 * Quick match: the deterministic first-pass matcher (no AI, milliseconds) runs as
 * soon as equipment is extracted. It proposes; you confirm. A confirmed model is
 * saved exactly like a choice in the model dropdown (origin "user"), so an AI rerun
 * never replaces it.
 */
export type QuickMatch = {
  equipment_key: string;
  tag: string;
  family: string | null;
  family_label: string | null;
  family_basis: string | null;
  status: 'auto' | 'choose' | 'prefix_only' | 'unmatched';
  reason: string;
  options: Row[];
  selected_model_id: string | null;
  suggested_model_id?: string;
  current_model_id: string | null;
  user_confirmed_model_id: string | null;
  design_basis: Row[];
};
type Result = { matches: QuickMatch[]; elapsed_ms: number; revision: number; version: string };

export function useQuickMatches(id: string | null | undefined, revision: unknown, ready: boolean) {
  const [result, setResult] = useState<Result | null>(null),
    [error, setError] = useState(''),
    [attempt, setAttempt] = useState(0);
  useEffect(() => {
    if (!id || !ready) {
      setResult(null);
      setError('');
      return;
    }
    let live = true;
    api<Result>(`assessments/${id}/equipment-matches`)
      .then((r) => {
        if (!live) return;
        setResult(r);
        setError('');
      })
      .catch((e: Error) => {
        if (!live) return;
        setResult(null);
        // "Extract engineering data first" is a normal state, not a failure.
        setError(/extract engineering data first/i.test(e.message) ? '' : e.message || 'Quick match is unavailable.');
      });
    return () => {
      live = false;
    };
  }, [id, revision, ready, attempt]);
  return { result, error, retry: () => setAttempt((n) => n + 1) };
}

export const pending = (m: QuickMatch) => !m.user_confirmed_model_id;

export const MATCH_LABEL: Record<QuickMatch['status'], string> = {
  auto: 'Match found',
  choose: 'Choose type',
  prefix_only: 'Confirm type',
  unmatched: 'No match',
};

export function matchChip(m: QuickMatch | undefined): { label: string; tone: string } | null {
  if (!m) return null;
  if (m.user_confirmed_model_id) return { label: 'Model confirmed', tone: 'user' };
  return { label: MATCH_LABEL[m.status], tone: m.status };
}

function optionLabel(o: Row) {
  const name = text(o.configuration) || text(o.equipment_name);
  return name.replace(/_/g, ' ');
}

function sizingText(o: Row) {
  const s = obj(o.sizing);
  const cells = strings(s.design_basis_cells);
  const cite = cells.length ? ` · from ${cells.join(', ')}` : '';
  const assumptions = strings(s.assumptions).map((a) => a.replace(/_/g, ' '));
  switch (s.status) {
    case 'direct':
      return `Sized straight from your data${cite}`;
    case 'derived':
      return `Sized via ${text(s.recipe_label) || text(s.recipe)}${cite}${assumptions.length ? ` · needs ${assumptions.join(', ')}` : ''}`;
    case 'needs_input':
      return `Needs a ${text(s.quantity).replace(/_/g, ' ')} you supply`;
    default:
      return 'Cannot be sized: catalogue coordinate unresolved';
  }
}

export function QuickMatchPanel({
  result,
  props,
  onClose,
  onInspect,
}: {
  result: Result;
  props: StageProps;
  onClose: () => void;
  onInspect: (equipmentKey: string) => void;
}) {
  const { hook, equipment } = props;
  const open = useMemo(() => result.matches.filter(pending), [result]);
  const [picks, setPicks] = useState<Record<string, string>>(() => {
    const start: Record<string, string> = {};
    for (const m of open) {
      // The model already in use stays preselected; otherwise the best-ranked option is suggested.
      const inUse = m.options.find((o) => o.current);
      const initial = inUse ? text(inUse.model_id) : m.status === 'auto' ? m.selected_model_id : m.options.length ? text(m.options[0].model_id) : null;
      if (initial) start[m.equipment_key] = initial;
    }
    return start;
  });
  const chosen = Object.entries(picks).filter(([, id]) => Boolean(id));
  const counts = {
    auto: open.filter((m) => m.status === 'auto').length,
    choose: open.filter((m) => m.status === 'choose' || m.status === 'prefix_only').length,
    unmatched: open.filter((m) => m.status === 'unmatched').length,
  };
  const bestId = (m: QuickMatch) => (m.options.length ? text(m.options[0].model_id) : '');

  async function apply() {
    let rows: Row[] = Array.isArray(equipment.value) ? equipment.value : [];
    for (const [key, modelId] of chosen) {
      const match = open.find((m) => m.equipment_key === key);
      const option = match?.options.find((o) => text(o.model_id) === modelId);
      if (!match || !option) continue;
      const row = rows.find((r) => r.equipment_key === key) || {};
      const changed = text(row.curve_id) !== modelId;
      rows = patchEquipment(rows, key, {
        ...userModelSelection(modelId),
        source: text(option.source) || 'garrett',
        rationale: `Confirmed in quick match: ${match.family_label} · ${optionLabel(option)}`,
        quick_match: { version: result.version, status: match.status, family: match.family, basis: match.family_basis },
        // A new model needs new sizing: clear the old inputs so the sizing step proposes them.
        ...(changed ? { size: null, sizing: null, unit_conversion: null } : {}),
      });
    }
    const ok = await hook.action(() => hook.saveSection('equipment', rows, `User confirmed ${chosen.length} quick-match model(s)`).then(() => undefined));
    if (ok) onClose();
  }

  return (
    <Panel
      wide
      kicker={`QUICK MATCH · ${result.elapsed_ms} ms · NO AI`}
      title="Match equipment to cost models"
      onClose={onClose}
      footer={
        <>
          <span className="gf-muted">{chosen.length} of {open.length} chosen</span>
          <button type="button" className="gf-secondary" onClick={onClose}>
            Not now
          </button>
          <button type="button" className="gf-primary" disabled={!chosen.length || hook.busy} onClick={() => void apply()}>
            Confirm {chosen.length} model{chosen.length === 1 ? '' : 's'}
          </button>
        </>
      }
    >
      <p className="gf-qm-summary">
        {counts.auto > 0 && <span className="gf-qm-tag gf-qm-auto">{counts.auto} clear match{counts.auto === 1 ? '' : 'es'}</span>}
        {counts.choose > 0 && <span className="gf-qm-tag gf-qm-choose">{counts.choose} best guess{counts.choose === 1 ? '' : 'es'} to check</span>}
        {counts.unmatched > 0 && <span className="gf-qm-tag gf-qm-unmatched">{counts.unmatched} not matched</span>}
        <span className="gf-muted">
          Read from each item&apos;s own name. The best match is selected for every item; your workbook rarely states the configuration (e.g. which tank or exchanger type), so check the guesses and change any you disagree with. Nothing is saved until you confirm.
        </span>
      </p>
      {!open.length && <p>Every item already has a model you confirmed.</p>}
      <ol className="gf-qm-list">
        {open.map((m) => (
          <li key={m.equipment_key} className={`gf-qm-item gf-qm-${m.status}`}>
            <div className="gf-qm-head">
              <strong>{m.tag}</strong>
              <span>{m.family_label || 'Function not recognised'}</span>
              <span className={`gf-qm-tag gf-qm-${m.status}`}>{MATCH_LABEL[m.status]}</span>
            </div>
            <small className="gf-muted">{m.reason}</small>
            {m.options.length > 0 && (
              <fieldset className="gf-qm-options">
                <legend className="gf-sr-only">Cost model for {m.tag}</legend>
                {m.options.map((o) => {
                  const id = text(o.model_id);
                  const variants = Number(o.variants) || 1;
                  const sizeable = Number(obj(o.sizing).tier) <= 1;
                  return (
                    <label key={id} className={`gf-qm-option ${picks[m.equipment_key] === id ? 'gf-qm-picked' : ''}`}>
                      <input
                        type="radio"
                        name={`qm-${m.equipment_key}`}
                        checked={picks[m.equipment_key] === id}
                        onChange={() => setPicks({ ...picks, [m.equipment_key]: id })}
                      />
                      <span className="gf-qm-option-body">
                        <b>{optionLabel(o)}</b>
                        <small>
                          {o.current ? 'in use now · ' : id === bestId(m) ? (m.status === 'auto' ? 'best match · ' : 'best guess · ') : ''}
                          {text(o.source)}
                          {variants > 1 ? ` · ${variants} variants (best shown)` : ''}
                          {strings(o.matched_words).length ? ` · matches “${strings(o.matched_words).join(' ')}”` : ''}
                        </small>
                        <small className={sizeable ? 'gf-qm-sizeable' : 'gf-qm-unsizeable'}>{sizingText(o)}</small>
                      </span>
                    </label>
                  );
                })}
                {picks[m.equipment_key] && (
                  <button type="button" className="gf-link" onClick={() => setPicks(Object.fromEntries(Object.entries(picks).filter(([k]) => k !== m.equipment_key)))}>
                    Leave {m.tag} undecided
                  </button>
                )}
              </fieldset>
            )}
            <button type="button" className="gf-link" onClick={() => onInspect(m.equipment_key)}>
              {m.options.length ? 'Other models and details…' : 'Open item to choose a model or price…'}
            </button>
          </li>
        ))}
      </ol>
    </Panel>
  );
}
