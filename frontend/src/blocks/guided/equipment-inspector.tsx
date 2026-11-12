'use client';
import { useState } from 'react';
import { UnitConversionAssumptions } from '@/blocks/equipment/unit-conversion';
import {
  equipmentMapping,
  list,
  obj,
  originLabel,
  patchEquipment,
  text,
  userModelSelection,
  words,
  type EquipmentCardModel,
  type Row,
} from '@/lib/guided-flow';
import { api, post } from './use-assessment';
import { OriginChip, Panel, type StageProps } from './flow';

type Model = { id: string; equipment: string; configuration: string; source?: string; availability?: string; size_unit?: string };

/**
 * Click-through inspector for one equipment card: matched model, required
 * inputs and assumptions, with opt-in AI research or manual editing.
 * Edits stay in the shared equipment draft until the user saves.
 */
export function EquipmentInspector({
  card,
  props,
  onClose,
  initialMode = 'inspect',
  onRun,
  where = 'Entry board',
}: {
  card: EquipmentCardModel;
  props: StageProps;
  onClose: () => void;
  initialMode?: 'inspect' | 'manual' | 'research';
  /** Saves and recalculates equipment with Python. */
  onRun: () => void;
  where?: string;
}) {
  const { hook, equipment } = props;
  const [mode, setMode] = useState(initialMode),
    [focus, setFocus] = useState('');
  const state = hook.state;
  const mapping = equipmentMapping(equipment.value, card.key);
  const matching = obj(mapping.matching_attempt || mapping.matching);
  const models = hook.catalogue as unknown as Model[];
  const drafts = list(state?.research_drafts).filter((d) => text(d.target_id) === card.key || text(obj(d.subject).tag) === card.tag);
  const job = obj(state?.research_job);
  const researching = Boolean(state?.running) && job.status === 'running' && job.target_id === card.key;
  const change = (patch: Row) => equipment.set(patchEquipment(equipment.value, card.key, patch));
  const resolution = list(obj(obj(obj(obj(state?.results).stages).equipment).result).input_resolution)
    .filter((r) => r.equipment_key === card.key)
    .at(-1);
  async function save() {
    await hook.action(() => equipment.save(`User reviewed ${card.tag} parameters on the guided ${where}`));
  }
  return (
    <Panel
      title={`${card.tag} · ${card.name}`}
      kicker={`EQUIPMENT · ${card.type.toUpperCase()}`}
      onClose={onClose}
      wide={mode === 'manual'}
      footer={
        <>
          <span className="gf-muted">{equipment.dirty ? 'Unsaved edits on this board' : 'All edits saved'}</span>
          <button type="button" className="gf-secondary" disabled={!equipment.dirty || hook.busy} onClick={() => equipment.reset()}>
            Discard
          </button>
          <button type="button" className="gf-primary" disabled={!equipment.dirty || hook.busy || Boolean(state?.running)} onClick={() => void save()}>
            Save changes
          </button>
        </>
      }
    >
      <div className="gf-inspector-actions" role="group" aria-label="How to fill this equipment's parameters">
        <button type="button" aria-pressed={mode === 'research'} onClick={() => setMode('research')}>
          <strong>✦ Research parameters with AI</strong>
          <small>Provisional drafts with sources. Never overwrites your inputs.</small>
        </button>
        <button type="button" aria-pressed={mode === 'manual'} onClick={() => setMode('manual')}>
          <strong>✎ Edit parameters manually</strong>
          <small>Choose the cost model, size, units and design inputs.</small>
        </button>
      </div>

      <section className="gf-block" aria-labelledby="gf-model-h">
        <h3 id="gf-model-h">Matched cost model</h3>
        <p className="gf-big">
          {card.model} <OriginChip origin={card.modelOrigin === 'ai' ? 'AI · provisional' : originLabel[card.modelOrigin]} />
        </p>
        <p className="gf-muted">{card.rationale}</p>
        {list(matching.candidate_models).length > 0 && (
          <p className="gf-muted">
            Other candidates: {list(matching.candidate_models).map((m) => text(m.equipment_name || m.model_id || m.id)).filter(Boolean).join(', ')}
          </p>
        )}
      </section>

      <section className="gf-block" aria-labelledby="gf-req-h">
        <h3 id="gf-req-h">Required inputs & units</h3>
        {card.requiredInputs.length ? (
          <InputTable rows={card.requiredInputs.map((r) => ({ ...r, label: `${words(r.name)}${r.required ? '' : ' (optional)'}`, hint: r.role }))} />
        ) : (
          <p className="gf-muted">{card.status === 'unmatched' ? 'Choose a cost model to see the inputs it needs.' : 'This model has no separately listed design inputs, or they are not prepared yet.'}</p>
        )}
        {card.sizing && (
          <>
            <h3>Sizing method · {words(card.sizing.method)}</h3>
            <InputTable rows={card.sizing.inputs.map((r) => ({ ...r, label: words(r.name), hint: '' }))} />
          </>
        )}
      </section>

      <section className="gf-block" aria-labelledby="gf-assume-h">
        <h3 id="gf-assume-h">Assumptions</h3>
        <dl className="gf-dl">
          <div>
            <dt>Quantity</dt>
            <dd>
              {text(mapping.quantity ?? card.quantity ?? 'Not set')}
              {mapping.quantity_rationale ? <small>{text(mapping.quantity_rationale)}</small> : null}
            </dd>
          </div>
          <div>
            <dt>Design size</dt>
            <dd>{card.size}</dd>
          </div>
          <div>
            <dt>Price basis</dt>
            <dd>
              {obj(mapping.manual_price).amount
                ? `Your price ${text(obj(mapping.manual_price).amount)} ${text(obj(mapping.manual_price).currency)} (${text(obj(mapping.manual_price).price_period)})`
                : card.cost === null
                  ? 'Unpriced — never treated as zero'
                  : 'Calculated by the selected cost model'}
            </dd>
          </div>
        </dl>
        {card.issues.length > 0 && (
          <ul className="gf-issue-list">
            {card.issues.map((issue) => (
              <li key={issue}>{issue}</li>
            ))}
          </ul>
        )}
      </section>

      {mode === 'research' && (
        <section className="gf-block gf-ai" aria-labelledby="gf-ai-h">
          <h3 id="gf-ai-h">Research parameters with AI</h3>
          <p>
            FlowValue sends this item&apos;s extracted workbook data and catalogue to the AI provider, which searches published correlations and comparable prices.
            Results arrive as a <strong>provisional draft</strong> with sources. Nothing is applied until you choose it, and your own edits are never overwritten.
          </p>
          {!hook.aiEnabled && <p className="gf-warn">AI is switched off on this server, so research is unavailable. Use manual editing instead.</p>}
          <label className="gf-field">
            <span>Optional focus</span>
            <input value={focus} maxLength={300} placeholder="e.g. stainless steel, 10 bar design pressure" onChange={(e) => setFocus(e.target.value)} />
          </label>
          <button
            type="button"
            className="gf-primary"
            disabled={!hook.aiEnabled || hook.busy || Boolean(state?.running) || equipment.dirty || !state}
            onClick={() =>
              void hook.action(() =>
                api(`assessments/${hook.id}/research`, post({ revision: state!.revision, kind: 'equipment', target_id: card.key, focus, consent: true })),
              )
            }
          >
            I agree — research with AI (usage charges apply)
          </button>
          {equipment.dirty && <small>Save or discard board edits before starting research.</small>}
          {researching && <p role="status">Researching… the draft appears here when finished.</p>}
          {job.status === 'failed' && job.target_id === card.key && <p className="gf-warn">Research failed: {text(job.notice)}</p>}
        </section>
      )}

      {drafts.length > 0 && (
        <section className="gf-block gf-ai" aria-labelledby="gf-drafts-h">
          <h3 id="gf-drafts-h">AI research drafts · provisional</h3>
          {drafts.map((d, i) => (
            <details key={i} open={i === drafts.length - 1}>
              <summary>
                {text(d.retrieved_at) || 'Research draft'} · <OriginChip origin="AI · provisional" />
              </summary>
              <p>{text(d.summary)}</p>
              {list(d.candidates).map((c, j) => (
                <div className="gf-candidate" key={j}>
                  <div>
                    <strong>{text(c.name) || 'Candidate'}</strong>
                    <small>
                      {text(c.price) || 'No price'} {text(c.currency)}
                      {c.quantity_unit ? '/' + text(c.quantity_unit) : ''} · {text(c.price_period) || 'undated'} · {text(c.scope)}
                    </small>
                    {c.source_url ? (
                      <a href={text(c.source_url)} target="_blank" rel="noreferrer">
                        Inspect source ↗
                      </a>
                    ) : null}
                  </div>
                  <button
                    type="button"
                    className="gf-secondary"
                    disabled={!(Number(c.price) > 0) || !/^[A-Z]{3}$/.test(text(c.currency)) || !/^\d{4}/.test(text(c.price_period))}
                    onClick={() =>
                      change({
                        manual_price: {
                          amount: Number(c.price),
                          currency: text(c.currency),
                          price_period: text(c.price_period).slice(0, 4),
                          cost_scope: 'purchased_equipment',
                          source: 'AI research candidate selected by user: ' + text(c.name),
                          source_url: text(c.source_url),
                          notes: 'Provisional AI-researched comparable; selected explicitly by the user. Not a vendor quotation.',
                          approved: true,
                          approval_requested: true,
                          locked: true,
                        },
                      })
                    }
                  >
                    Use this price
                  </button>
                </div>
              ))}
              {text(d.notice) && <small>{text(d.notice)}</small>}
            </details>
          ))}
        </section>
      )}

      {mode === 'manual' && (
        <section className="gf-block" aria-labelledby="gf-manual-h">
          <h3 id="gf-manual-h">Edit parameters manually</h3>
          <div className="gf-grid-2">
            <label className="gf-field">
              <span>Cost model</span>
              <select
                value={text(mapping.curve_id)}
                disabled={Boolean(obj(mapping.manual_price).amount)}
                onChange={(e) => {
                  const model = models.find((m) => m.id === e.target.value);
                  change({ ...userModelSelection(model?.id || null), source: model?.source || 'garrett', size_unit: model?.size_unit || text(mapping.size_unit), rationale: `User selected costing model on the ${where}` });
                }}
              >
                <option value="">Unpriced / no model selected</option>
                {models.map((m) => (
                  <option key={m.id} value={m.id} disabled={m.availability === 'disabled'}>
                    {m.equipment} · {m.configuration} ({m.id})
                  </option>
                ))}
              </select>
            </label>
            <label className="gf-field">
              <span>Quantity (identical units)</span>
              <input
                type="number"
                min="1"
                step="1"
                value={text(mapping.quantity)}
                onChange={(e) => change({ quantity: e.target.value === '' ? null : Number(e.target.value), quantity_origin: 'user', quantity_rationale: `User-entered on the ${where}` })}
              />
            </label>
            <label className="gf-field">
              <span>Design size</span>
              <input
                type="number"
                step="any"
                value={text(mapping.size)}
                onChange={(e) =>
                  change({ size: e.target.value === '' ? null : Number(e.target.value), sizing: null, unit_conversion: { ...obj(mapping.unit_conversion), enabled: false } })
                }
              />
            </label>
            <label className="gf-field">
              <span>Size unit</span>
              <input value={text(mapping.size_unit)} onChange={(e) => change({ size_unit: e.target.value })} />
            </label>
          </div>
          {obj(mapping.manual_price).amount ? (
            <p className="gf-muted">
              A price override is active, so the cost model is not used.{' '}
              <button type="button" className="gf-link" onClick={() => change({ manual_price: null })}>
                Remove price override
              </button>
            </p>
          ) : null}
          <details className="gf-details">
            <summary>Design inputs & unit conversion</summary>
            <UnitConversionAssumptions
              key={card.key}
              assessmentId={hook.id}
              equipmentKey={card.key}
              value={mapping as never}
              models={models}
              resolution={resolution as never}
              saving={hook.busy || Boolean(state?.running)}
              dirty={equipment.dirty}
              onChange={(patch) => change(patch as Row)}
              onSave={() => void save()}
              onRun={onRun}
            />
          </details>
        </section>
      )}
    </Panel>
  );
}

function InputTable({ rows }: { rows: { name: string; label: string; hint: string; unit: string; value: unknown; origin: keyof typeof originLabel }[] }) {
  return (
    <table className="gf-table">
      <thead>
        <tr>
          <th scope="col">Input</th>
          <th scope="col">Value</th>
          <th scope="col">Unit</th>
          <th scope="col">Basis</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r, i) => (
          <tr key={r.name + i}>
            <td>
              {r.label}
              {r.hint && <small>{r.hint}</small>}
            </td>
            <td>{r.value === null || r.value === undefined || r.value === '' ? <em className="gf-missing">Missing</em> : text(r.value)}</td>
            <td>{r.unit || '—'}</td>
            <td>
              <OriginChip origin={originLabel[r.origin]} />
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
