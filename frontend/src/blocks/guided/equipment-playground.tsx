'use client';
import { useMemo, useState } from 'react';
import { QuickPriceOverride } from '@/blocks/equipment/quick-price-override';
import { compact, equipmentCards, equipmentMapping, money, num, obj, patchEquipment, text, type EquipmentCardModel, type Row } from '@/lib/guided-flow';
import { EquipmentInspector } from './equipment-inspector';
import { Issues, OriginChip, RunBar, StageHeading, type StageProps } from './flow';

/**
 * Equipment playground: every item's Python-calculated cost, with price,
 * units and the design inputs that drive it editable in place. After
 * "Save & recalculate" each row shows its previous cost beside the new one.
 */
export function EquipmentPlayground(props: StageProps) {
  const { hook, equipment } = props;
  const state = hook.state;
  const cards = useMemo(() => equipmentCards(state, equipment.value, hook.catalogue), [state, equipment.value, hook.catalogue]);
  const result = obj(obj(obj(obj(state?.results).stages).equipment).result);
  const [open, setOpen] = useState(''),
    [inspect, setInspect] = useState<EquipmentCardModel | null>(null),
    [before, setBefore] = useState<Record<string, string> | null>(null),
    [query, setQuery] = useState(''),
    [filter, setFilter] = useState<'all' | 'priced' | 'open'>('all');
  const lines = Array.isArray(result.equipment) ? (result.equipment as Row[]) : [];
  const currency = text(obj(obj(lines.find((l) => obj(obj(l.calculation).estimate).currency)?.calculation).estimate).currency || 'USD');
  const shown = cards
    .filter((c) => !query || `${c.tag} ${c.name} ${c.model}`.toLowerCase().includes(query.toLowerCase()))
    .filter((c) => filter === 'all' || (filter === 'priced' ? c.cost !== null : c.cost === null));
  const priced = cards.filter((c) => c.cost !== null).length;
  async function recalculate() {
    setBefore(Object.fromEntries(cards.map((c) => [c.key, c.cost === null ? 'Unpriced' : money(c.cost)])));
    await hook.action(async () => {
      await equipment.save('User adjusted equipment price, units or design inputs in the Equipment playground');
      await hook.runStage('equipment');
    });
  }
  const lineFor = (key: string) => lines.find((l) => obj(l.parsed_source).equipment_key === key) || {};
  return (
    <div className="gf-play">
      <StageHeading kicker="STAGE 02 · EQUIPMENT" title="Equipment costs">
        Every item priced by Python from its saved model. Adjust the price, the units or the design inputs behind it, then recalculate to see the effect.
      </StageHeading>
      <div className="gf-kpis">
        <div>
          <small>Purchased equipment</small>
          <strong>{num(result.equipment_cost_total) === null ? (cards.length - priced > 0 ? 'Incomplete' : 'Not combined') : compact(result.equipment_cost_total)}</strong>
          <span>{num(result.equipment_cost_total) !== null ? currency : totalReason(result.issues, cards.length - priced)}</span>
        </div>
        <div>
          <small>Total equipment cost</small>
          <strong>{num(result.equipment_total_with_packages) === null ? '—' : compact(result.equipment_total_with_packages)}</strong>
          <span>
            {num(result.packages_total) ? `${currency} · includes ${compact(result.packages_total)} installed packages` : `${currency} · installation is added in CAPEX`}
          </span>
        </div>
        <div>
          <small>Priced items</small>
          <strong>
            {priced} / {cards.length}
          </strong>
          <span>{text(result.status).replaceAll('_', ' ') || 'Not run yet'}</span>
        </div>
      </div>
      <Issues items={result.issues} title="Equipment notes from Python" />
      <div className="gf-toolbar">
        <input type="search" aria-label="Find equipment" placeholder="Find equipment…" value={query} onChange={(e) => setQuery(e.target.value)} />
        <div role="group" aria-label="Filter equipment" className="gf-segment">
          {(['all', 'priced', 'open'] as const).map((f) => (
            <button key={f} type="button" aria-pressed={filter === f} onClick={() => setFilter(f)}>
              {{ all: 'All', priced: 'Priced', open: 'Unpriced' }[f]}
            </button>
          ))}
        </div>
      </div>
      <div className="gf-table-wrap">
        <table className="gf-table gf-equipment-table">
          <thead>
            <tr>
              <th scope="col">Equipment</th>
              <th scope="col">Cost model</th>
              <th scope="col">Size</th>
              <th scope="col">Qty</th>
              <th scope="col" className="gf-num">
                Purchased cost
              </th>
              {before && (
                <th scope="col" className="gf-num">
                  Before your change
                </th>
              )}
              <th scope="col">
                <span className="gf-sr-only">Actions</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {shown.map((c) => {
              const line = lineFor(c.key),
                calc = obj(line.calculation),
                estimate = obj(calc.estimate),
                installation = obj(calc.installation);
              const mapping = equipmentMapping(equipment.value, c.key);
              const count = num(line.quantity ?? mapping.quantity) ?? 1;
              // Per-unit price as reported by Python (no browser arithmetic); blank when not reported.
              const perUnit = num(installation.equipment_cost ?? obj(mapping.manual_price).amount);
              const now = c.cost === null ? 'Unpriced' : money(c.cost);
              const changed = before && before[c.key] !== undefined && before[c.key] !== now;
              const expanded = open === c.key;
              return (
                <FragmentRow key={c.key}>
                  <tr className={changed ? 'gf-changed' : undefined}>
                    <th scope="row">
                      <strong>{c.tag}</strong>
                      <small>{c.name}</small>
                    </th>
                    <td>
                      {c.model}
                      <br />
                      <OriginChip origin={c.modelOrigin === 'ai' ? 'AI · provisional' : c.modelOrigin === 'user' ? 'Your input' : 'Unreviewed'} />
                    </td>
                    <td>{c.size}</td>
                    <td>{c.quantity ?? '—'}</td>
                    <td className="gf-num">
                      {c.cost === null ? <em className="gf-missing">Unpriced</em> : money(c.cost)}
                      {c.cost !== null && <small>{c.currency}</small>}
                    </td>
                    {before && <td className="gf-num gf-muted">{changed ? before[c.key] : '—'}</td>}
                    <td className="gf-row-actions">
                      <button type="button" className="gf-secondary" aria-expanded={expanded} aria-controls={`gf-eq-${c.key}`} onClick={() => setOpen(expanded ? '' : c.key)}>
                        {expanded ? 'Close' : 'Adjust'}
                      </button>
                    </td>
                  </tr>
                  {expanded && (
                    <tr className="gf-expand">
                      <td colSpan={before ? 7 : 6} id={`gf-eq-${c.key}`}>
                        <div className="gf-adjust">
                          <div>
                            <h3>Price</h3>
                            <QuickPriceOverride
                              key={c.key + text(state?.revision)}
                              value={mapping as never}
                              unitPrice={perUnit}
                              currency={text(estimate.currency || 'USD')}
                              period={/^\d{4}(?:-\d{2})?$/.test(text(estimate.period)) ? text(estimate.period) : String(new Date().getFullYear())}
                              quantity={count}
                              installationFactor={num(installation.installation_factor)}
                              busy={hook.busy || Boolean(state?.running)}
                              dirty={equipment.dirty}
                              onOverride={(price) => equipment.set(patchEquipment(equipment.value, c.key, { manual_price: price as Row | null }))}
                              onSave={() => void hook.action(() => equipment.save(`User overrode ${c.tag} price in the Equipment playground`))}
                              onRun={() => void recalculate()}
                            />
                          </div>
                          <div>
                            <h3>Units & design inputs</h3>
                            <p className="gf-muted">Size {c.size}. {c.requiredInputs.length ? `${c.requiredInputs.length} model inputs.` : ''}</p>
                            <button type="button" className="gf-secondary" onClick={() => setInspect(c)}>
                              Edit model, units & design inputs
                            </button>
                            {c.issues.length > 0 && (
                              <ul className="gf-issue-list">
                                {c.issues.slice(0, 4).map((issue) => (
                                  <li key={issue}>{issue}</li>
                                ))}
                              </ul>
                            )}
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </FragmentRow>
              );
            })}
          </tbody>
        </table>
      </div>
      <div className="gf-inline-actions">
        <span className="gf-muted">{equipment.dirty ? 'You have unsaved equipment changes.' : before ? 'Rows with a previous value changed in the last recalculation.' : 'Changes are saved with a rationale and recalculated by Python.'}</span>
        <button type="button" className="gf-secondary" disabled={!equipment.dirty || hook.busy} onClick={() => equipment.reset()}>
          Discard changes
        </button>
        <button type="button" className="gf-primary" disabled={hook.busy || Boolean(state?.running)} onClick={() => void recalculate()}>
          Save & recalculate equipment
        </button>
      </div>
      <RunBar
        label="Run CAPEX"
        busy={hook.busy}
        disabled={Boolean(state?.running) || !priced}
        back={{ label: 'Board', onClick: () => props.go('entry') }}
        status={<strong>{priced ? `${priced} priced items feed CAPEX` : 'Price at least one item to run CAPEX'}</strong>}
        note="CAPEX, OPEX and Revenue are calculated together by Python."
        onRun={() => void props.advance(() => equipment.save('User reviewed equipment in the Equipment playground'))}
      />
      {inspect && (
        <EquipmentInspector
          card={cards.find((c) => c.key === inspect.key) || inspect}
          props={props}
          initialMode="manual"
          where="Equipment playground"
          onClose={() => setInspect(null)}
          onRun={() => {
            setInspect(null);
            void recalculate();
          }}
        />
      )}
    </div>
  );
}

function FragmentRow({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}

/** Why the purchased total is not shown, in one line the user can act on. */
function totalReason(issues: unknown, unpriced: number): string {
  if (unpriced > 0) return `${unpriced} items still unpriced — not counted as zero`;
  const first = Array.isArray(issues) && issues.length ? String(issues[0]) : '';
  const dates = first.match(/\(([^)]*)\)\. Date typed prices/);
  if (dates) return `Items on different dates (${dates[1]}). Open the odd item and set its price date to the study date.`;
  return first || 'Recalculate equipment';
}
