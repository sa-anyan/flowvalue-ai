'use client';
import { useMemo, useState } from 'react';
import { QuickPriceOverride } from '@/blocks/equipment/quick-price-override';
import { compact, decideHeld, heldEstimates, equipmentCards, equipmentMapping, money, num, obj, patchEquipment, text, type EquipmentCardModel, type Row } from '@/lib/guided-flow';
import { EquipmentInspector } from './equipment-inspector';
import { Issues, OriginChip, RunBar, StageHeading, type StageProps } from './flow';
import { AnalystCard } from './analyst-card';

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
  const summary = obj(result.priced_summary);
  const amounts = Array.isArray(summary.amounts) ? summary.amounts as Row[] : [];
  const unpriced = num(summary.unpriced_count) ?? cards.length - priced;
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
      <AnalystCard stage="equipment" hook={props.hook} />
      <div className="gf-kpis">
        <div>
          <small>Equipment estimate · priced items</small>
          <strong>{amounts.length ? amounts.map((amount) => `${amounts.length > 1 ? text(amount.currency) + ' ' : ''}${compact(amount.amount)}`).join(' · ')
            : num(result.equipment_total_with_packages) !== null ? compact(result.equipment_total_with_packages) : 'Awaiting prices'}</strong>
          <span>{amounts.length === 1 ? text(amounts[0].currency) : currency} · excludes {unpriced} item{unpriced === 1 ? '' : 's'} not priced</span>
        </div>
        <div>
          <small>Items not priced</small>
          <strong>{unpriced}</strong>
          <span>{unpriced ? 'Excluded from the estimate above' : 'All equipment has a price'}</span>
        </div>
        <div>
          <small>Priced items</small>
          <strong>
            {priced} / {cards.length}
          </strong>
          <span>{unpriced ? `${unpriced} awaiting price` : 'All items priced'}</span>
        </div>
      </div>
      <Issues items={(Array.isArray(result.issues) ? result.issues : []).filter((issue) => !text(issue).startsWith('Unresolved equipment: subtotals are partial; complete total unavailable'))} title="Cost scope notes" />
      {heldEstimates(equipment.value).length > 0 && (
        <section className="gf-card-block gf-held" aria-labelledby="gf-held-h">
          <h2 id="gf-held-h">AI estimate check</h2>
          <p className="gf-muted">
            A new AI estimate jumped by more than 25% for the same M&amp;E, so the earlier (anchored) estimate is still used. Choose which one to keep.
          </p>
          <ul className="gf-lines">
            {heldEstimates(equipment.value).map((h) => {
              const tag = cards.find((c) => c.key === h.key)?.tag || h.key;
              const decide = (d: 'use' | 'keep') =>
                void hook.action(async () => {
                  const rows = decideHeld(equipment.value, h.key, d);
                  equipment.set(rows);
                  await hook.saveSection('equipment', rows, d === 'use' ? `User accepted the new AI estimate for ${tag}` : `User kept the anchored AI estimate for ${tag}`);
                  if (d === 'use') await hook.runStage('equipment');
                });
              return (
                <li key={h.key} className="gf-line">
                  <div className="gf-line-main">
                    <div>
                      <strong>{tag}</strong>
                      <small>
                        Used: {compact(h.anchorSize)} {h.unit} · New AI estimate: {compact(h.newSize)} {h.unit} ({h.newSize > h.anchorSize ? '+' : '−'}
                        {Math.round(Math.abs(h.drift) * 100)}%)
                        {h.assumptions.length > 0 && ` · new assumptions: ${h.assumptions.map((a) => `${a.name.replaceAll('_', ' ')} ${a.value} ${a.unit}`).join(', ')}`}
                      </small>
                    </div>
                  </div>
                  <div className="gf-line-actions">
                    <button type="button" className="gf-secondary" disabled={hook.busy} onClick={() => decide('keep')}>
                      Keep {compact(h.anchorSize)} {h.unit}
                    </button>
                    <button type="button" className="gf-link" disabled={hook.busy} onClick={() => decide('use')}>
                      Use {compact(h.newSize)} {h.unit}
                    </button>
                  </div>
                </li>
              );
            })}
          </ul>
        </section>
      )}
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
