/**
 * Guided-flow presentation helpers.
 *
 * Everything here only reads, labels and routes saved backend output. No
 * economics are calculated in the browser: amounts are always the values the
 * Python stages returned, and missing values stay missing (never zero).
 */
export type Json = null | string | number | boolean | Json[] | { [key: string]: Json };
export type Row = Record<string, unknown>;

export const obj = (v: unknown): Row => (v !== null && typeof v === 'object' && !Array.isArray(v) ? (v as Row) : {});
export const list = (v: unknown): Row[] => (Array.isArray(v) ? v.map(obj) : []);
/** Plain text items of a backend array (issues, warnings); non-text entries are rendered as JSON. */
export const strings = (v: unknown): string[] =>
  (Array.isArray(v) ? v : []).map((x) => (typeof x === 'string' ? x : x === null || x === undefined ? '' : typeof x === 'object' ? JSON.stringify(x) : String(x))).filter(Boolean);
export const num = (v: unknown): number | null =>
  v === null || v === undefined || v === '' || typeof v === 'boolean' || !Number.isFinite(Number(v)) ? null : Number(v);
export const text = (v: unknown): string => (v === null || v === undefined ? '' : String(v));
export const words = (v: unknown): string =>
  text(v)
    .replaceAll('_', ' ')
    .replace(/^\w/, (c) => c.toUpperCase());

/** Formats a backend amount for display. Missing values are shown as missing, never as 0. */
export function money(v: unknown, missing = 'Not calculated'): string {
  const n = num(v);
  return n === null ? missing : new Intl.NumberFormat('en-GB', { maximumFractionDigits: 0 }).format(n);
}
export function compact(v: unknown, missing = '—'): string {
  const n = num(v);
  return n === null ? missing : new Intl.NumberFormat('en-GB', { notation: 'compact', maximumFractionDigits: 2 }).format(n);
}
export function percent(v: unknown, missing = '—', digits = 1): string {
  const n = num(v);
  return n === null ? missing : `${(n * 100).toFixed(digits)}%`;
}

/* ------------------------------------------------------------------ stages */

export const guidedStages = [
  { id: 'entry', label: 'Entry', title: 'Board', run: 'Run equipment', backend: 'equipment' },
  { id: 'equipment', label: 'Equipment', title: 'Equipment', run: 'Run CAPEX', backend: 'capex' },
  { id: 'capex', label: 'CAPEX', title: 'CAPEX playground', run: 'Run OPEX', backend: 'opex' },
  { id: 'opex', label: 'OPEX', title: 'OPEX playground', run: 'Run Revenue', backend: 'revenue' },
  { id: 'revenue', label: 'Revenue', title: 'Revenue playground', run: 'Run Financial', backend: 'financial' },
  { id: 'financial', label: 'Financial', title: 'Financial playground', run: '', backend: '' },
] as const;
export type StageId = (typeof guidedStages)[number]['id'];
export const stageIds = guidedStages.map((s) => s.id) as StageId[];
export const isStage = (v: unknown): v is StageId => typeof v === 'string' && (stageIds as string[]).includes(v);
export const stageIndex = (id: StageId) => stageIds.indexOf(id);
export function nextStage(id: StageId): StageId | null {
  const i = stageIndex(id);
  return i >= 0 && i < stageIds.length - 1 ? stageIds[i + 1] : null;
}
/** Direction used to choose the swipe animation. */
export function direction(from: StageId, to: StageId): 'forward' | 'back' {
  return stageIndex(to) >= stageIndex(from) ? 'forward' : 'back';
}
/** The backend stage a forward run button executes (CAPEX, OPEX and Revenue run together server-side). */
export function forwardRun(id: StageId): string | null {
  return guidedStages.find((s) => s.id === id)?.backend || null;
}
export const economicsGroup = new Set(['capex', 'opex', 'revenue']);

export type StageStatus = { label: string; tone: 'ready' | 'stale' | 'blocked' | 'idle' | 'running' };
export function stageStatus(receipt: unknown, stage: unknown): StageStatus {
  const r = obj(receipt),
    s = obj(stage),
    status = text(r.status || s.status);
  if (status === 'running' || status === 'queued') return { label: 'Calculating', tone: 'running' };
  if (r.status === 'stale' || s.result_is_stale === true) return { label: 'Needs rerun', tone: 'stale' };
  if (status === 'ready' || status.startsWith('calculated')) return { label: r.complete === false ? 'Partial' : 'Ready', tone: 'ready' };
  if (['data_required', 'pending_user_input', 'needs_review', 'failed', 'partial'].includes(status))
    return { label: words(status), tone: 'blocked' };
  return { label: 'Not run', tone: 'idle' };
}

/* --------------------------------------------------------------- equipment */

export type Entity = { key: string; identifier: string; kind: string; values?: Row[]; stream_keys?: string[] };
export type ValueOrigin = 'user' | 'ai' | 'source' | 'derived' | 'unknown';
export type EquipmentCardModel = {
  key: string;
  tag: string;
  name: string;
  type: string;
  model: string;
  modelOrigin: ValueOrigin;
  rationale: string;
  status: 'priced' | 'user_priced' | 'needs_inputs' | 'unmatched' | 'alias';
  statusLabel: string;
  cost: number | null;
  currency: string;
  size: string;
  quantity: number | null;
  requiredInputs: { name: string; unit: string; value: unknown; origin: ValueOrigin; required: boolean; role: string }[];
  sizing: { method: string; inputs: { name: string; unit: string; value: unknown; origin: ValueOrigin }[] } | null;
  /** Sizing assumptions behind the size (proposed by the AI, from the M&E balance, or yours). */
  assumptions: { name: string; unit: string; value: unknown; origin: ValueOrigin; rationale: string }[];
  issues: string[];
};

/** Finds the plan row for an equipment key, including user-confirmed physical sub-assets ("parent::asset"). */
export function equipmentMapping(rows: unknown, key: string): Row {
  const plan = list(rows);
  const direct = plan.find((r) => r.equipment_key === key);
  if (direct) return direct;
  for (const parent of plan) {
    const child = list(parent.physical_assets).find((c) => `${text(parent.equipment_key)}::${text(c.asset_id)}` === key);
    if (child) return { ...child, equipment_key: key };
  }
  return {};
}

/** Returns a new plan with `changes` merged into the row for `key` (never mutates the input). */
export function patchEquipment(rows: unknown, key: string, changes: Row): Row[] {
  const plan = list(rows);
  const parent = plan.find((r) => list(r.physical_assets).some((c) => `${text(r.equipment_key)}::${text(c.asset_id)}` === key));
  if (parent) {
    const { equipment_key: _ignored, ...patch } = changes;
    void _ignored;
    return plan.map((r) =>
      r === parent
        ? { ...r, physical_assets: list(r.physical_assets).map((c) => (`${text(r.equipment_key)}::${text(c.asset_id)}` === key ? { ...c, ...patch } : c)) }
        : r,
    );
  }
  const original = plan.find((r) => r.equipment_key === key) || { equipment_key: key, curve_id: null, size: null, size_unit: '', rationale: '' };
  return [...plan.filter((r) => r.equipment_key !== key), { ...original, ...changes }];
}

/** Records a user's cost-model choice so AI reruns never replace it. */
export function userModelSelection(curveId: string | null): Row {
  return { curve_id: curveId, model_selection: curveId ? { origin: 'user', curve_id: curveId } : null };
}

export function originOf(status: unknown, source?: unknown): ValueOrigin {
  const s = `${text(status)} ${text(source)}`.toLowerCase();
  if (/user/.test(s)) return 'user';
  if (/(ai|llm|estimate|propos)/.test(s)) return 'ai';
  if (/(meb|derived|workbook)/.test(s)) return 'derived';
  if (/(synthetic|test)/.test(s)) return 'source';
  return 'unknown';
}
export const originLabel: Record<ValueOrigin, string> = {
  user: 'Your input',
  ai: 'AI · provisional',
  source: 'Supplied assumption',
  derived: 'From M&E balance',
  unknown: 'Unreviewed',
};

function entityValue(e: Entity | undefined, property: string): string {
  const values = [...(e?.values || [])].reverse();
  return text(values.find((v) => v.property === property)?.normalized_value);
}

/**
 * Builds the card model for each piece of equipment from the saved register and,
 * when available, the saved equipment-stage result. Costs are copied from Python.
 */
export function equipmentCards(state: Row | null, plan: unknown, catalogue: Row[] = []): EquipmentCardModel[] {
  if (!state) return [];
  const report = obj(state.scoped_report || state.effective_report || obj(state.parsed).report);
  const entities = list(report.entities).filter((e) => e.kind === 'equipment') as unknown as Entity[];
  const result = obj(obj(obj(obj(state.results).stages).equipment).result);
  const lines = list(result.equipment);
  const lineFor = (key: string, tag: string) =>
    lines.find((l) => obj(l.parsed_source).equipment_key === key) || lines.find((l) => text(l.equipment_tag) === tag);
  return entities.map((e) => {
    const mapping = equipmentMapping(plan, e.key);
    const line = lineFor(e.key, e.identifier) || {};
    const matching = obj(mapping.matching_attempt || mapping.matching);
    const conversion = obj(mapping.unit_conversion);
    const provenance = obj(conversion.input_provenance);
    const curve = text(line.curve_id || mapping.curve_id || matching.selected_model_id);
    const model = catalogue.find((m) => m.id === curve);
    const manual = obj(mapping.manual_price);
    const userPriced = text(line.curve_id) === 'manual:user-price' || Boolean(manual.amount);
    const capital =
      line.cost_scope === 'unit_capital' ||
      (obj(obj(line.calculation).evidence).source === 'openpytea' && ['installed_equipment', 'module_estimate'].includes(text(line.cost_scope)));
    const cost = num(capital ? line.amount : line.equipment_cost);
    const alias = line.cost_status === 'alias_reference';
    const selection = obj(mapping.model_selection);
    const modelOrigin: ValueOrigin = selection.origin === 'user' || userPriced ? 'user' : curve ? (matching.match_method === 'none' ? 'unknown' : 'ai') : 'unknown';
    const requirements = list(model?.input_requirements);
    const inputs = obj(conversion.inputs);
    const estimate = obj(obj(line.calculation).estimate);
    const size = num(estimate.size ?? mapping.size);
    const requiredInputs = requirements.length
      ? requirements.map((r, i) => {
          const name = text(r.name || r.quantity);
          // The first required input is the model's size coordinate (e.g. volume, area, power).
          const isSize = name === 'size' || i === 0;
          const typedSize = mapping.size !== null && mapping.size !== undefined && conversion.enabled !== true;
          const value = isSize ? (size ?? inputs[name] ?? null) : (inputs[name] ?? null);
          const origin: ValueOrigin =
            isSize && typedSize ? 'user' : isSize && size !== null && estimate.size !== undefined ? 'derived' : originOf(obj(provenance[name]).status, obj(provenance[name]).source);
          return { name, unit: text(r.target_unit || r.unit), value, origin, required: r.required !== false, role: text(r.role) };
        })
      : Object.entries(inputs).map(([name, value]) => ({ name, unit: '', value, origin: originOf(obj(provenance[name]).status, obj(provenance[name]).source), required: true, role: '' }));
    const sizingPlan = obj(mapping.sizing);
    const sizing = sizingPlan.method
      ? {
          method: text(sizingPlan.method),
          inputs: Object.entries(obj(sizingPlan.parameters)).map(([name, p]) => ({
            name,
            unit: text(obj(p).unit),
            value: obj(p).value ?? null,
            origin: originOf(obj(p).status, obj(p).source),
          })),
        }
      : null;
    const status: EquipmentCardModel['status'] = alias
      ? 'alias'
      : userPriced && cost !== null
        ? 'user_priced'
        : cost !== null
          ? 'priced'
          : curve
            ? 'needs_inputs'
            : 'unmatched';
    return {
      key: e.key,
      tag: e.identifier,
      name: entityValue(e, 'name') || entityValue(e, 'type') || text(matching.equipment_function) || 'Equipment',
      type: entityValue(e, 'type') || text(line.equipment_type) || 'Type not specified',
      model: alias ? `Alias of ${text(obj(line.reference_cost).equipment_tag)}` : userPriced ? 'Your price override' : curve ? text(model?.equipment ? `${model.equipment} · ${model.configuration}` : curve) : 'No cost model matched',
      modelOrigin,
      rationale: text(selection.rationale || matching.reason || mapping.rationale || obj(obj(line.decision).conceptual_matching).reason) || 'No model-selection rationale recorded yet.',
      status,
      statusLabel: { priced: 'Priced', user_priced: 'Your price', needs_inputs: 'Needs inputs', unmatched: 'No model', alias: 'Alias' }[status],
      cost,
      currency: text(estimate.currency || manual.currency || 'USD'),
      size: size === null ? 'Size not set' : `${size.toLocaleString('en-GB', { maximumSignificantDigits: 4 })} ${text(estimate.size_unit ?? mapping.size_unit)}`.trim(),
      quantity: num(line.quantity ?? mapping.quantity),
      requiredInputs,
      sizing,
      assumptions: Object.entries(inputs).map(([name, value]) => ({
        name,
        unit: text(obj(provenance[name]).unit),
        value,
        origin: originOf(obj(provenance[name]).status, obj(provenance[name]).source),
        rationale: text(obj(provenance[name]).rationale),
      })),
      issues: (Array.isArray(line.issues) ? line.issues : []).map(text).filter(Boolean),
    };
  });
}

/* ------------------------------------------------------------------- CAPEX */

export type CapexLine = {
  id: string;
  label: string;
  amount: number | null;
  fraction: number | null;
  base: string;
  status: string;
  rationale: string;
  min: number | null;
  max: number | null;
  origin: string;
  editable: boolean;
  excluded: boolean;
};

/** Labels where each CAPEX line's value came from, using the saved assumption register. */
export function capexLines(result: unknown, plan: unknown, factors: Row[] = [], register: Row[] = []): CapexLine[] {
  const config = obj(plan),
    overrides = obj(config.overrides),
    selected = obj(config.selected_factors),
    exclusions = obj(config.exclusions);
  const registerOrigin = (path: string) => register.find((r) => text(r.path) === path);
  return list(obj(result).lines).map((line) => {
    const id = text(line.id),
      factor = factors.find((f) => f.id === id) || {};
    const entry = registerOrigin(`capex.overrides.${id}`) || registerOrigin(`capex.selected_factors.${id}`);
    const origin =
      id in exclusions
        ? 'Removed by you'
        : id in overrides
          ? 'Your override'
          : id in selected
            ? entry && /ai|llm|propos/i.test(text(entry.origin))
              ? 'Selected by AI · provisional'
              : 'Selected by you'
            : line.status === 'source_factor'
              ? `Source range · ${words(config.factor_selection || 'selection')}`
              : words(line.status);
    return {
      id,
      label: words(id),
      amount: num(line.amount),
      fraction: num(line.fraction),
      base: words(line.base),
      status: text(line.status),
      rationale: text(line.rationale),
      min: num(factor.minimum),
      max: num(factor.maximum),
      origin,
      editable: factor.additive !== false && !['embedded', 'not_separately_published'].includes(text(line.status)),
      excluded: id in exclusions,
    };
  });
}

/* --------------------------------------------------------------- financial */

export const financialMetricKeys = [
  ['Project NPV', 'project_npv', 'money'],
  ['Project IRR', 'project_irr', 'percent'],
  ['Discounted payback', 'project_discounted_payback', 'years'],
  ['Simple payback', 'project_payback', 'years'],
  ['Profitability index', 'project_profitability_index', 'ratio'],
] as const;

export function metricMap(result: unknown): Map<string, Row> {
  const metrics = obj(result).metrics;
  return new Map<string, Row>(Array.isArray(metrics) ? (metrics as [string, Row][]).filter((m) => Array.isArray(m)).map(([k, v]) => [k, obj(v)]) : []);
}
export function metricText(metric: Row | undefined, kind: string): string {
  const n = num(metric?.value);
  if (n === null) return metric?.status === 'not_recovered' ? 'Not reached' : metric?.status === 'undefined' ? 'Not defined' : 'Pending';
  if (kind === 'percent') return percent(n);
  if (kind === 'years') return `${n.toFixed(1)} yr`;
  if (kind === 'ratio') return n.toFixed(2);
  return compact(n);
}

/** Financial policy fields exposed as sliders. Ranges are UI bounds only; Python validates. */
export const financialLevers = [
  { key: 'discount_rate', label: 'Discount rate', min: 0, max: 0.3, step: 0.005, percent: true },
  { key: 'tax_rate', label: 'Tax rate', min: 0, max: 0.5, step: 0.01, percent: true },
  { key: 'depreciation_years', label: 'Depreciation life', min: 1, max: 40, step: 1, percent: false, unit: 'years' },
  { key: 'salvage_fraction', label: 'Salvage value', min: 0, max: 0.5, step: 0.01, percent: true },
  { key: 'working_capital_recovery_fraction', label: 'Working capital recovered', min: 0, max: 1, step: 0.05, percent: true },
] as const;

/* ------------------------------------------------------------- Monte Carlo */

export type Band = { year: string; p10: number | null; p50: number | null; p90: number | null };
/** Reads the backend's pointwise cash-flow percentiles; it never derives new quantiles. */
export function cashBands(summary: unknown, field = 'fcff'): Band[] {
  return list(obj(summary).cash_flow).map((d) => {
    const v = obj(d[field]);
    return { year: text(d.year), p10: num(v.p10), p50: num(v.p50), p90: num(v.p90) };
  });
}
/** Percentile keys the Monte Carlo summary actually provides for a metric. */
export function availablePercentiles(metric: unknown): string[] {
  return Object.keys(obj(metric)).filter((k) => /^p\d+$/.test(k) && num(obj(metric)[k]) !== null);
}

/* ------------------------------------------------------------------ OPEX review */

/** Categories with a calculated line out of the required categories (never "0 of nothing"). */
export function opexProgress(lines: unknown, factors: unknown): { priced: number; total: number } {
  const required = list(factors)
    .filter((f) => f.required !== false)
    .map((f) => text(f.id));
  const priced = new Set(
    list(lines)
      .filter((l) => num(l.amount) !== null)
      .map((l) => text(l.category)),
  );
  return { priced: required.filter((id) => priced.has(id)).length, total: required.length };
}

/** Year-1 headline: the full total when complete, otherwise pending with a labelled partial subtotal. */
export function opexHeadline(result: Row, progress: { priced: number; total: number }): { label: string; value: string; note: string } {
  const full = num(result.first_year_cash_opex);
  if (result.complete !== false && full !== null) return { label: 'Annual cash OPEX · year 1', value: compact(full), note: '' };
  const partial = num(result.known_cash_opex_subtotal);
  return {
    label: `Pending — ${progress.priced} of ${progress.total} categories priced`,
    value: partial !== null && partial > 0 ? compact(partial) : 'Pending',
    note: partial !== null && partial > 0 ? 'Partial subtotal of priced lines only' : 'No category priced yet',
  };
}

export type OpexProposal = {
  root: 'garrett_factors' | 'energy' | 'materials' | 'labour' | 'additional_expenses';
  id: string;
  label: string;
  value: string;
  source: string;
  detail: string;
  by: 'reference' | 'ai';
  /** The input the edit box writes (fraction, tariff, price, headcount or amount). */
  editKey: string;
  /** Edit-box label with its unit, e.g. "Price per kg". */
  editLabel: string;
  /** Yearly quantity the price applies to (from Python), when known. */
  quantity: { amount: number; unit: string } | null;
  /** Current price/tariff, for the live yearly-cost preview. */
  price: number | null;
};

export type Quantities = Record<string, { amount: number; unit: string }>;

/** Yearly quantities per OPEX item id, from Python's lines and pending price questions. */
export function opexQuantities(lines: Row[], pending: Row[]): Quantities {
  const out: Quantities = {};
  for (const l of lines) {
    const [kind, ...rest] = text(l.id).split(':');
    const q = num(l.quantity);
    if ((kind === 'feed' || kind === 'energy') && q !== null) out[rest.join(':')] = { amount: q, unit: text(l.unit) || (kind === 'energy' ? 'kWh' : '') };
  }
  for (const p of pending) {
    const q = num(p.annual_quantity);
    if (q !== null) out[text(p.id)] = { amount: q, unit: text(p.unit) };
  }
  return out;
}

const proposedBy = (origin: unknown): 'reference' | 'ai' | null => (origin === 'reference_default' ? 'reference' : origin === 'ai' ? 'ai' : null);

/** Reference-default and AI-proposed values still awaiting the user's review. */
export function opexProposals(config: Row, quantities: Quantities = {}): OpexProposal[] {
  const out: OpexProposal[] = [];
  for (const [id, raw] of Object.entries(obj(config.garrett_factors))) {
    const e = obj(raw),
      by = proposedBy(e.origin);
    if (!by) continue;
    out.push({
      root: 'garrett_factors',
      id,
      label: words(id),
      value: percent(e.fraction),
      source: by === 'reference' ? `${text(e.source)}, ${text(e.page)}` : 'AI proposal',
      detail: by === 'reference' ? `${text(e.value_basis) || 'value'} of ${percent(e.low)}–${percent(e.high)}` : text(e.rationale),
      by,
      editKey: 'fraction',
      editLabel: 'Edit (fraction)',
      quantity: null,
      price: null,
    });
  }
  for (const root of ['energy', 'materials', 'labour', 'additional_expenses'] as const) {
    for (const item of list(config[root])) {
      const by = proposedBy(item.origin);
      if (!by) continue;
      let value: string, editKey: string, editLabel: string;
      if (root === 'labour') {
        editKey = 'headcount_fte';
        editLabel = 'Headcount (FTE)';
        value = `${text(item.headcount_fte) || '?'} FTE${num(item.annual_base_salary) === null ? '' : ` × ${money(item.annual_base_salary)}/yr`}`;
      } else if (root === 'additional_expenses') {
        editKey = item.annual_amount !== undefined ? 'annual_amount' : item.amount !== undefined ? 'amount' : 'unit_price';
        editLabel = editKey === 'unit_price' ? 'Price per unit' : 'Annual amount';
        value = num(item[editKey]) === null ? 'amount needed' : money(item[editKey]);
      } else {
        editKey = root === 'energy' ? 'tariff_per_kwh' : 'unit_price';
        editLabel = root === 'energy' ? 'Tariff per kWh' : `Price per ${text(item.quantity_unit) || 'unit'}`;
        const price = item[editKey];
        value = num(price) === null ? 'price needed' : `${text(price)} per ${root === 'energy' ? 'kWh' : text(item.quantity_unit)}`;
      }
      out.push({
        root,
        id: text(item.id),
        label: text(item.name || item.role || item.id),
        value,
        source: by === 'reference' ? 'Study data' : 'AI proposal',
        detail: text(item.rationale),
        by,
        editKey,
        editLabel,
        quantity: root === 'energy' || root === 'materials' ? (quantities[text(item.id)] ?? null) : null,
        price: root === 'energy' || root === 'materials' ? num(item[editKey]) : null,
      });
    }
  }
  return out;
}

/** What the background AI brainstorm is doing, for a one-line notice. */
export function brainstormNotice(record: unknown, aiEnabled: boolean): { tone: 'running' | 'ready' | 'failed' | 'off'; text: string } | null {
  const r = obj(record);
  if (!aiEnabled) return null;
  if (r.status === 'running') return { tone: 'running', text: 'AI is researching OPEX assumptions in the background (labour, utilities, materials). Reference defaults are shown meanwhile.' };
  if (r.status === 'failed') return { tone: 'failed', text: `AI research did not finish (${text(r.error) || 'unknown error'}). Reference defaults still apply.` };
  if (r.status === 'ready') {
    const n = list(r.added).length;
    return { tone: 'ready', text: n ? `AI added ${n} proposal${n === 1 ? '' : 's'} to review below.` : 'AI research finished; nothing new to add beyond your values.' };
  }
  return null;
}
