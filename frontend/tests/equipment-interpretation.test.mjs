import { test } from "node:test";
import assert from "node:assert/strict";
import { isInterpretationDraft, isSavedInterpretation, interpretationRecords, interpretationContextVersion } from "../src/lib/equipment-interpretation.ts";
const data = {
  schema_version: "equipment-interpretation-v1", input_digest: "a".repeat(64), equipment_key: "u1", model: "test", generated_at: "2026-10-29", notice: "Draft", costing_blockers: ["Unvalidated curve"],
  draft: { interpreted_identity: "Bioreactor", observations: [{ evidence_id: "v1", quote: "Bioreactor" }], candidates: [{ catalog_id: "reactor", rationale: "Hypothesis", differences: ["Aeration"], missing_inputs: ["Volume"] }], engineering_hypotheses: [], clarification_questions: [], uncertainty_drivers: ["Method scope"] },
  candidate_sources: [{ id: "reactor", name: "Reactors", source_refs: [{ source_id: "garrett", printed_page: 299, pdf_page: 49 }] }], observation_sources: [{ id: "v1", sheet: "Balance", cell: "B2" }],
};
test("interpretation records retain reviewed draft and source lineage", () => {
  const stored = JSON.parse(JSON.stringify({ stamp: "input-fingerprint", data, review: "Engineer acknowledged draft" }));
  assert.equal(isSavedInterpretation(stored), true);
  assert.equal(stored.data.candidate_sources[0].source_refs[0].printed_page, 299);
});
test("damaged and incompatible interpretation records cannot render as valid drafts", () => {
  for (const value of [null, {}, { ...data, draft: null }, { ...data, candidate_sources: [{}] }, { ...data, observation_sources: [null] }, { ...data, schema_version: "old-version" }]) assert.equal(isInterpretationDraft(value), false);
  assert.equal(isSavedInterpretation({ stamp: "ok", data, review: null }), false);
});

test("equipment draft cache preserves separate units and drops corrupt entries", () => {
  const a = { stamp: "context:unit-a", data, review: "" };
  const b = { stamp: "context:unit-b", data: { ...data, equipment_key: "u2" }, review: "" };
  assert.deepEqual(interpretationRecords([a, null, {}, b]), [a, b]);
  assert.equal(interpretationRecords(null).length, 0);
  assert.equal(interpretationContextVersion, "equipment-process-context-v2");
});
