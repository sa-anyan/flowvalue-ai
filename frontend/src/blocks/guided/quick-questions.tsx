'use client';
import { useEffect, useState } from 'react';
import { obj, text } from '@/lib/guided-flow';
import { api, post } from './use-assessment';
import type { StageProps } from './flow';

export const PROJECT_TYPES = [
  ['new_plant', 'New plant (greenfield)'],
  ['expansion', 'Expansion of an existing site'],
  ['retrofit', 'Retrofit of existing equipment'],
] as const;

/**
 * Two quick questions asked while the analyst researches in the background.
 * Each answer is saved as soon as it is given; only the stages that use it
 * (CAPEX, OPEX, Financial) are researched again.
 */
export function QuickQuestions({ props }: { props: StageProps }) {
  const { hook } = props;
  const saved = obj(obj(hook.state).project_context);
  const [location, setLocation] = useState(text(saved.location));
  const [kind, setKind] = useState(text(saved.project_type));
  const [note, setNote] = useState('');
  useEffect(() => {
    setLocation(text(saved.location));
    setKind(text(saved.project_type));
    // Reset only for another study.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hook.state?.id]);
  if (!hook.state) return null;

  async function save(next: { location: string; project_type: string }) {
    if (next.location === text(saved.location) && next.project_type === text(saved.project_type)) return;
    try {
      await api(`assessments/${hook.id}/project-context`, post({ location: next.location || null, project_type: next.project_type || null }));
      setNote('Saved — the analyst is using it.');
      hook.reload();
    } catch (e) {
      setNote((e as Error).message);
    }
  }

  return (
    <section className="gf-quick-questions" aria-labelledby="gf-qq-h">
      <span className="gf-kicker">TWO QUICK QUESTIONS</span>
      <h3 id="gf-qq-h">While the analyst reads your M&amp;E</h3>
      <div className="gf-grid-2">
        <label className="gf-field">
          <span>Where will the plant be?</span>
          <input
            value={location}
            maxLength={120}
            placeholder="e.g. Accra, Ghana"
            onChange={(e) => setLocation(e.target.value)}
            onBlur={() => void save({ location: location.trim(), project_type: kind })}
          />
        </label>
        <label className="gf-field">
          <span>What kind of project?</span>
          <select
            value={kind}
            onChange={(e) => {
              setKind(e.target.value);
              void save({ location: location.trim(), project_type: e.target.value });
            }}
          >
            <option value="">Choose…</option>
            {PROJECT_TYPES.map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
      </div>
      {note && <small className="gf-muted">{note}</small>}
    </section>
  );
}
