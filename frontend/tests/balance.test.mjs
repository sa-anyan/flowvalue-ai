import { test } from "node:test";
import assert from "node:assert/strict";
import { emptyDescription, descriptionIsCurrent } from "../src/lib/balance.ts";
import { isBalanceAttachment, readWorkspace } from "../src/lib/workspace.ts";

test("description edits and workbook replacements invalidate comparison", () => {
  const value = {
    description: {
      ...emptyDescription,
      text: "Water enters P-1",
      reviewed_text: "Water enters P-1",
      reviewed_at: "2026-10-28",
    },
  };
  assert.equal(descriptionIsCurrent(value), true);
  value.description.text = "Water leaves P-1";
  assert.equal(descriptionIsCurrent(value), false);
  value.description = { ...emptyDescription, text: "Water enters P-1" };
  assert.equal(descriptionIsCurrent(value), false);
});
test("engineering attachment is distinct from existing financial and native data", () => {
  const balance = {
    report: {
      schema_version: "flowvalue-balance-v1",
      filename: "process.xlsx",
      entities: [],
      tables: [],
      issues: [],
      checks: [],
      sheets: [],
      declarations: [],
      limitations: [],
    },
    description: { ...emptyDescription },
  };
  assert.equal(isBalanceAttachment(balance), true);
  const project = {
    costing: { equipment: [] },
    financial: { discount_rate: 0.1 },
  };
  let stored = JSON.stringify({
    project,
    streams: [],
    native_import: null,
    balance_import: balance,
  });
  Object.defineProperty(globalThis, "sessionStorage", {
    value: { getItem: () => stored },
    configurable: true,
  });
  assert.deepEqual(readWorkspace().project, project);
  assert.equal(readWorkspace().balance_import.report.filename, "process.xlsx");
  stored = JSON.stringify({
    project,
    streams: [],
    balance_import: { report: { schema_version: "unknown" } },
  });
  assert.equal(readWorkspace(), null);
});

test("empty-first storage does not restore the archived legacy workspace, and new engineering uploads persist independently", async () => {
  const { workspaceKey, balanceDraftKey, readBalanceDraft, writeBalanceDraft } =
    await import("../src/lib/workspace.ts");
  const stored = new Map([
    [
      "flowvalue-workspace-v1",
      JSON.stringify({
        project: {
          costing: { equipment: [{ unit_id: "LEGACY" }] },
          financial: {},
        },
        streams: [],
      }),
    ],
  ]);
  Object.defineProperty(globalThis, "sessionStorage", {
    value: {
      getItem: (key) => stored.get(key) ?? null,
      setItem: (key, value) => stored.set(key, value),
      removeItem: (key) => stored.delete(key),
    },
    configurable: true,
  });
  assert.notEqual(workspaceKey, "flowvalue-workspace-v1");
  assert.equal(readWorkspace(), null);
  assert.equal(readBalanceDraft(), null);
  const attachment = {
    report: {
      schema_version: "flowvalue-balance-v1",
      filename: "new.xlsx",
      entities: [],
      tables: [],
      issues: [],
      checks: [],
      sheets: [],
      declarations: [],
      limitations: [],
    },
    description: { ...emptyDescription, text: "New process" },
  };
  writeBalanceDraft(attachment);
  assert.deepEqual(readBalanceDraft(), attachment);
  assert.ok(stored.has(balanceDraftKey));
  assert.equal(readWorkspace(), null);
  writeBalanceDraft(null);
  assert.equal(readBalanceDraft(), null);
  assert.ok(stored.has("flowvalue-workspace-v1"));
});
