export type Draft = {
  schema_version: string; input_digest: string; equipment_key: string; model: string; generated_at: string;
  draft: { interpreted_identity: string; observations: { evidence_id: string; quote: string }[];
    candidates: { catalog_id: string; rationale: string; differences: string[]; missing_inputs: string[] }[];
    engineering_hypotheses: string[]; clarification_questions: string[]; uncertainty_drivers: string[] };
  candidate_sources: { id: string; name: string; source_refs: { source_id: string; label?: string; printed_page: number; pdf_page: number }[] }[];
  observation_sources: { id: string; sheet: string; cell: string }[];
  costing_blockers: string[]; notice: string;
};
export type Saved = { stamp: string; data: Draft; review: string };

const object = (v: unknown): v is Record<string, unknown> => !!v && typeof v === "object" && !Array.isArray(v);
const strings = (v: unknown): v is string[] => Array.isArray(v) && v.every(x => typeof x === "string");
export function isInterpretationDraft(value: unknown): value is Draft {
  if (!object(value) || value.schema_version !== "equipment-interpretation-v1" ||
      ![value.input_digest, value.equipment_key, value.model, value.generated_at, value.notice].every(x => typeof x === "string") ||
      !strings(value.costing_blockers) || !object(value.draft)) return false;
  const d = value.draft;
  return typeof d.interpreted_identity === "string" &&
    [d.engineering_hypotheses, d.clarification_questions, d.uncertainty_drivers].every(strings) &&
    Array.isArray(d.observations) && d.observations.every(o => object(o) && typeof o.evidence_id === "string" && typeof o.quote === "string") &&
    Array.isArray(d.candidates) && d.candidates.every(c => object(c) && typeof c.catalog_id === "string" && typeof c.rationale === "string" && strings(c.differences) && strings(c.missing_inputs)) &&
    Array.isArray(value.candidate_sources) && value.candidate_sources.every(c => object(c) && typeof c.id === "string" && typeof c.name === "string" && Array.isArray(c.source_refs) && c.source_refs.every(r => object(r) && typeof r.source_id === "string" && Number.isInteger(r.printed_page) && Number.isInteger(r.pdf_page))) &&
    Array.isArray(value.observation_sources) && value.observation_sources.every(o => object(o) && typeof o.id === "string" && typeof o.sheet === "string" && typeof o.cell === "string");
}
export function isSavedInterpretation(value: unknown): value is Saved {
  return object(value) && typeof value.stamp === "string" && typeof value.review === "string" && isInterpretationDraft(value.data);
}

export const interpretationContextVersion = "equipment-process-context-v2";
export const interpretationStorageKey = "flowvalue-equipment-interpretation-v2";
export function interpretationRecords(value: unknown): Saved[] {
  return Array.isArray(value) ? value.filter(isSavedInterpretation).slice(-20) : [];
}
