import { test } from "node:test";
import assert from "node:assert/strict";
import {
  importScopeNotes,
  scenarioScopeNotes,
  readWorkspace,
} from "../src/lib/workspace.ts";

const equipment = [{ unit_id: "E-101", kind: "heat_exchanger" }];
const native = {
  units: [
    { unit_id: "E-101", warnings: [] },
    { unit_id: "R-101", warnings: ["Volume missing"] },
  ],
  warnings: [],
};

test("native scope flags excluded units and unrelated retained equipment", () => {
  const notes = importScopeNotes(native, [{ unit_id: "DEMO", kind: "pump" }]);
  assert.ok(notes.some((n) => n.startsWith("MIXED EQUIPMENT SCOPE: DEMO")));
  assert.ok(
    notes.some((n) => n.startsWith("INCOMPLETE EQUIPMENT SCOPE: E-101, R-101")),
  );
});

test("scope is recomputed after equipment edits without dropping operator notes", () => {
  const p = {
    costing: { equipment: [...equipment] },
    engineering_notes: [
      "Operator review required",
      "INCOMPLETE EQUIPMENT SCOPE: OLD",
    ],
  };
  const notes = scenarioScopeNotes(p, native);
  assert.ok(notes.includes("Operator review required"));
  assert.ok(
    notes.some((n) => n.startsWith("INCOMPLETE EQUIPMENT SCOPE: R-101")),
  );
  assert.ok(!notes.some((n) => n.includes("OLD")));
  p.costing.equipment.push({ unit_id: "R-101", kind: "reactor" });
  assert.ok(
    !scenarioScopeNotes(p, native).some((n) => n.startsWith("INCOMPLETE")),
  );
});

test("damaged browser drafts fail safely, while valid drafts survive", () => {
  let stored = "{}";
  Object.defineProperty(globalThis, "sessionStorage", {
    value: { getItem: () => stored },
    configurable: true,
  });
  assert.equal(readWorkspace(), null);
  stored = "{broken";
  assert.equal(readWorkspace(), null);
  stored = JSON.stringify({
    project: { costing: { equipment: [...equipment] }, financial: {} },
    streams: [],
    native_import: null,
  });
  assert.equal(readWorkspace()?.project.costing.equipment[0].unit_id, "E-101");
  stored = JSON.stringify({
    project: { costing: { equipment: [...equipment] }, financial: {} },
    streams: [],
    native_import: {},
  });
  assert.equal(readWorkspace(), null);
});

test("critical scope warnings cannot be displaced by long operator notes", () => {
  const project = {
    costing: { equipment: [...equipment] },
    engineering_notes: Array.from(
      { length: 100 },
      (_, i) => `Operator note ${i}`,
    ),
  };
  const notes = scenarioScopeNotes(project, native);
  assert.equal(notes.length, 100);
  assert.ok(notes.some((n) => n.startsWith("INCOMPLETE EQUIPMENT SCOPE:")));
});
