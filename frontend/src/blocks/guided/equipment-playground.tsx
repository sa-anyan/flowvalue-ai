'use client';
import {withCurrency} from '@/lib/display-currency';
import { useMemo, useState } from 'react';
import {PremiumEquipmentWorkspace} from '@/blocks/equipment/view';
import {UnitConversionAssumptions} from '@/blocks/equipment/unit-conversion';
import {equipmentWorkspaceCards} from '@/lib/equipment-workspace-cards';
import { QuickPriceOverride } from '@/blocks/equipment/quick-price-override';
import { compact, decideHeld, heldEstimates, equipmentCards, equipmentMapping, money, num, obj, list, patchEquipment, text, type EquipmentCardModel, type Row } from '@/lib/guided-flow';
import { EquipmentCostBreakdown } from './equipment-cost-breakdown';
import { EquipmentInspector } from './equipment-inspector';
import { Issues, RunBar, StageHeading, type StageProps } from './flow';
import { AnalystCard } from './analyst-card';
import {EquipmentDriverAnalysis} from './analyst-cost-explorer';
import {EconomicsComposition} from './economics-dashboard';
import {api, post} from './use-assessment';

/**
 * Equipment playground: every item's Python-calculated cost, with price,
 * units and the design inputs that drive it editable in place. After
 * "Save & recalculate" the comparison retains the previous purchased/package prices.
 */
export function EquipmentPlayground(props: StageProps) {
  const { hook, equipment } = props;
  const state = hook.state;
  const cards = useMemo(() => equipmentCards(state, equipment.value, hook.catalogue), [state, equipment.value, hook.catalogue]);
  const result = obj(obj(obj(obj(state?.results).stages).equipment).result);
  const capexResult = obj(obj(obj(obj(state?.results).stages).capex).result);
  const [selectedKey, setSelectedKey] = useState(''),
    [before, setBefore] = useState<Record<string, string> | null>(null);
  const lines = Array.isArray(result.equipment) ? (result.equipment as Row[]) : [];
  const priced = cards.filter((c) => c.cost !== null).length;
  const summary = obj(result.priced_summary);
  async function recalculate() {
    setBefore(Object.fromEntries(cards.map((c) => [c.key, c.cost === null ? 'Unpriced' : money(c.cost)])));
    await hook.action(async () => {
      await equipment.save('User adjusted equipment price, units or design inputs in the Equipment playground');
      await hook.runStage('equipment');
    });
  }
  const lineFor = (key: string) => lines.find((l) => obj(l.parsed_source).equipment_key === key) || {};
  const workspaceCards = useMemo(() => equipmentWorkspaceCards(state, equipment.value), [state, equipment.value]);
  const current = workspaceCards.find(c => c.key === selectedKey) || workspaceCards[0];
  const currentKey = current?.key || '';
  const currentCard = cards.find(c => c.key === currentKey) || (current ? {
    key: currentKey, tag: current.tag, name: current.name, type: current.type, model: current.model,
    modelOrigin: 'unknown', rationale: current.rationale, status: 'needs_inputs', statusLabel: current.status,
    cost: current.knownCost ?? null, currency: current.costCurrency || '', size: current.size, quantity: null,
    requiredInputs: [], sizing: null, assumptions: [], issues: [],
  } as EquipmentCardModel : null);
  const line = lineFor(currentKey), calculation = obj(line.calculation), estimate = obj(calculation.estimate), installation = obj(calculation.installation);
  const mapping = equipmentMapping(equipment.value, currentKey);
  const count = num(line.quantity ?? obj(line.parsed_source).equipment_count ?? mapping.quantity) ?? 1;
  const perUnit = num(installation.equipment_cost) ?? (num(line.equipment_cost) !== null && count > 0 ? num(line.equipment_cost)! / count : null);
  const targetPeriod = text(obj(obj(state?.plan).cost_translation).target_period || new Date().getFullYear());
  const pricePeriod = /^\d{4}(?:-\d{2})?$/.test(text(estimate.period)) ? text(estimate.period) : targetPeriod;
  const busy = hook.busy || Boolean(state?.running);
  const matching = obj(obj(result.matching_register).summary);
  return (
    <div className="gf-play">
      <div className="gf-economics-split gf-equipment-split">
        <div className="gf-economics-results" role="region" aria-label="Equipment visual analysis" tabIndex={0}>
      <StageHeading kicker="STAGE 02 · EQUIPMENT" title="Equipment costs">
        Every item priced by Python from its saved model. Adjust the price, the units or the design inputs behind it, then recalculate to see the effect.
      </StageHeading>
      <div className="gf-kpis" aria-label="Equipment summary">
        {list(summary.amounts).map((basis,i)=><div key={i} className={i===0?'gf-kpi-hero':undefined}><small>Known equipment cost · {text(basis.currency)}</small><strong>{withCurrency(money(basis.amount),basis.currency)}</strong><span>{text(basis.period)} · priced scope; incomplete scope stays explicit</span></div>)}
        <div><small>Priced equipment</small><strong>{priced} <span>/ {cards.length}</span></strong><span>Saved prices and source-defined packages</span></div>
      </div>
          <h2 className="gf-pane-heading">Visual analysis</h2>
          {list(summary.amounts).map((basis,i)=><EconomicsComposition key={i} title={`Equipment cost composition · ${text(basis.currency)} ${text(basis.period)}`} currency={text(basis.currency)} values={list(basis.components).map(part=>[text(part.cost_scope).replaceAll('_',' '),part.amount])}/>)}
      <EquipmentDriverAnalysis result={result} revision={text(state?.revision)} assessmentId={text(state?.id)}/>
      <details className="gf-details"><summary>Background analyst briefing</summary><AnalystCard stage="equipment" hook={props.hook} /></details>
      <details className="gf-details"><summary>Equipment cost composition</summary><EquipmentCostBreakdown summary={summary} installation={list(capexResult.lines).find(line => line.id === 'equipment_installation')}/></details>
        </div>
        <div className="gf-economics-inputs" role="region" aria-label="Equipment figures and inputs" tabIndex={0}>
          <h2 className="gf-pane-heading">Equipment figures &amp; inputs</h2>

      <details className="gf-details"><summary>Cost scope notes</summary>
      <Issues items={(Array.isArray(result.issues) ? result.issues : []).filter((issue) => !text(issue).startsWith('Unresolved equipment: subtotals are partial; complete total unavailable')).map((issue) => text(issue).replace(/: priced as unit capital \(([^)]+)\), kept separate from purchased equipment; CAPEX adds it once$/, ': system price ($1), included in equipment cost and counted once in CAPEX.'))} title="Cost scope notes" />
      </details>
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
      <div className="gf-equipment-workspace">
        <PremiumEquipmentWorkspace
          items={workspaceCards}
          selectedKey={currentKey}
          onSelect={setSelectedKey}
          dirty={equipment.dirty}
          researching={busy || equipment.dirty}
          matchingSummary={matching.equipment_count !== undefined ? `${text(matching.matched)} / ${text(matching.equipment_count)} conceptual matches · sizing and pricing tracked separately` : undefined}
          onResearch={key => void hook.action(async () => {
            if (!state || busy || equipment.dirty) return;
            await api(`assessments/${hook.id}/research`, post({revision: state.revision, kind: 'equipment', target_id: key, consent: true}));
          })}
          priceOverrideContent={currentKey ? <QuickPriceOverride
            key={currentKey + text(state?.revision)}
            value={mapping as never}
            unitPrice={perUnit}
            currency={text(estimate.currency || 'USD')}
            period={pricePeriod}
            quantity={count}
            installationFactor={num(installation.installation_factor)}
            busy={busy}
            dirty={equipment.dirty}
            onOverride={price => equipment.set(patchEquipment(equipment.value, currentKey, {manual_price: price as Row | null}))}
            onSave={() => void hook.action(() => equipment.save('User reviewed equipment price in the guided Equipment directory'))}
            onRun={() => void recalculate()}
          /> : null}
          conversionContent={currentKey ? <UnitConversionAssumptions
            key={currentKey}
            assessmentId={hook.id}
            equipmentKey={currentKey}
            value={mapping as never}
            models={hook.catalogue as never}
            resolution={list(result.input_resolution).filter(r => r.equipment_key === currentKey).at(-1) as never}
            saving={busy}
            dirty={equipment.dirty}
            onChange={patch => equipment.set(patchEquipment(equipment.value, currentKey, patch as Row))}
            onSave={() => void hook.action(() => equipment.save('User reviewed unit conversion and sizing assumptions in the guided Equipment directory'))}
            onRun={() => void recalculate()}
          /> : null}
        >
          {currentCard && <EquipmentInspector key={currentKey} card={currentCard} props={props} embedded initialMode="manual" where="Equipment directory" onClose={() => {}} onRun={() => void recalculate()}/>}
        </PremiumEquipmentWorkspace>
      </div>
      <div className="gf-inline-actions">
        <span className="gf-muted">{equipment.dirty ? 'You have unsaved equipment changes.' : before ? 'Previous prices remain available in the comparison below.' : 'Changes are saved with a rationale and recalculated by Python.'}</span>
        <button type="button" className="gf-secondary" disabled={!equipment.dirty || hook.busy} onClick={() => equipment.reset()}>
          Discard changes
        </button>
        <button type="button" className="gf-primary" disabled={hook.busy || Boolean(state?.running)} onClick={() => void recalculate()}>
          Save & recalculate equipment
        </button>
      </div>
      {before && <details className="gf-details"><summary>Previous vs current purchased / package prices</summary><div className="gf-table-wrap"><table className="gf-table"><thead><tr><th>Equipment</th><th>Before recalculation</th><th>Current saved price</th></tr></thead><tbody>{cards.map(c => <tr key={c.key}><th>{c.tag}</th><td>{before[c.key] ?? 'Not established'}</td><td>{c.cost === null ? 'Unpriced' : money(c.cost)} {c.currency}</td></tr>)}</tbody></table></div></details>}
        </div>
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
    </div>
  );
}
