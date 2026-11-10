'use client';

import {useRef,type ReactNode} from 'react';
import type {Parameter} from '@/lib/monte-carlo';
import './variation-scope.css';

export const variationCategories = ['Equipment', 'CAPEX', 'OPEX', 'Revenue', 'Other assumptions'] as const;
type Category = typeof variationCategories[number];

export function variationGroup(parameter: Parameter): [Category, string] {
  const [section, group] = parameter.targets[0] ?? [];
  if (section === 'equipment') {
    const label = parameter.label.split(' · ')[0];
    return ['Equipment', label];
  }
  if (section === 'capex') return ['CAPEX', 'Capital factors'];
  if (section === 'operating_economics') {
    if (group === 'sales') return ['Revenue', 'Product sales'];
    if (group === 'commercial_lines') return ['Revenue', 'Commercial payments'];
    if (group === 'garrett_factors') return ['OPEX', 'Operating factors'];
    if (group === 'materials') return ['OPEX', 'Materials'];
    if (group === 'energy') return ['OPEX', 'Utilities & energy'];
    if (group === 'labour') return ['OPEX', 'Labour'];
    if (group === 'additional_expenses') return ['OPEX', 'Additional expenses'];
  }
  return ['Other assumptions', group === 'financial' ? 'Financial assumptions' : 'Shared operating schedule'];
}

export function canSample(parameter: Parameter) {
  if(parameter.review_required)return false;
  const {minimum, mode, maximum, hard_min, hard_max, distribution, stddev, choices, probabilities, source, rationale} = parameter;
  if (!source.trim() || !rationale.trim()) return false;
  if (distribution === 'discrete') {
    return choices.length > 0 && choices.length === probabilities.length &&
      new Set(choices).size === choices.length && probabilities.every(p => p >= 0) &&
      Math.abs(probabilities.reduce((sum, p) => sum + p, 0) - 1) <= 1e-9 &&
      (parameter.kind === 'configuration' || choices.every(value => typeof value === 'number' &&
        (hard_min === null || (parameter.strictly_positive ? value > hard_min : value >= hard_min)) &&
        (hard_max === null || value <= hard_max)));
  }
  if (minimum === null || maximum === null || !Number.isFinite(minimum) || !Number.isFinite(maximum) || minimum >= maximum) return false;
  if (hard_min !== null && (parameter.strictly_positive ? minimum <= hard_min : minimum < hard_min)) return false;
  if (hard_max !== null && maximum > hard_max) return false;
  if (distribution === 'uniform') return true;
  if (mode === null || !Number.isFinite(mode) || mode < minimum || mode > maximum) return false;
  return distribution === 'triangular' || (stddev !== null && Number.isFinite(stddev) && stddev > 0 &&
    (distribution !== 'lognormal' || minimum > 0));
}

export function ScopeCheck({label, parameters, disabled, onToggle}: {
  label: string; parameters: Parameter[]; disabled: boolean; onToggle: (parameters: Parameter[], enabled: boolean) => void;
}) {
  const eligible = parameters.filter(p => p.enabled || (p.kind !== 'configuration' && canSample(p)));
  const selected = parameters.filter(p => p.enabled).length;
  const checked = eligible.length > 0 && selected === eligible.length;
  return <label className="mc-scope-check">
    <input type="checkbox" aria-label={label} checked={checked} disabled={disabled || !eligible.length}
      ref={input => {if (input) input.indeterminate = selected > 0 && !checked;}}
      onChange={event => onToggle(eligible, event.target.checked)}/>
    <span><strong>{label}</strong><small>{selected} selected · {parameters.length} registered{!eligible.length && parameters.length > 0 ? ' · review bounds' : ''}</small></span>
  </label>;
}

export function VariationScope({parameters, disabled, onToggle, children}: {
  parameters: Parameter[]; disabled: boolean; onToggle: (parameters: Parameter[], enabled: boolean) => void; children: ReactNode;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  return <section className="mc-card">
    <div className="mc-card-head"><h2>What should vary?</h2>
      <button type="button" className="secondary" aria-haspopup="dialog" onClick={() => dialog.current?.showModal()}>Explore more</button>
    </div>
    <div className="mc-scope-grid">{variationCategories.slice(0, 4).map(category =>
      <ScopeCheck key={category} label={category} parameters={parameters.filter(p => variationGroup(p)[0] === category)}
        disabled={disabled} onToggle={onToggle}/>)}</div>
    <p className="muted">Select categories to sample inputs with usable bounds. Use Explore more to choose individual inputs or supply missing ranges. The seed reproduces the same draws for the same setup.</p>
    <dialog ref={dialog} className="mc-scope-drawer" aria-labelledby="mc-scope-drawer-title"
      onClick={event => {if(event.target === event.currentTarget) dialog.current?.close();}}>
      <div className="mc-scope-drawer-content">
        <div className="mc-card-head"><h2 id="mc-scope-drawer-title">Explore sampling inputs</h2>
          <button type="button" className="secondary" aria-label="Close sampling inputs" onClick={() => dialog.current?.close()}>✕</button>
        </div>
        <p className="muted">Review saved bounds and sources. A range without a validated probability model is a planning assumption.</p>
        {children}
      </div>
    </dialog>
  </section>;
}
