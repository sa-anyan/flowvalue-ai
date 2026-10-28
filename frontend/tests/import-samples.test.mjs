import { test } from "node:test";
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";
import { getImportSample } from "../src/lib/import-samples.ts";
import { importMethods } from "../src/lib/import-methods.ts";

test("every supported Entry source offers a sample, with an explicit fallback label for simulator exports", () => {
  assert.equal(importMethods.length, 17);
  for (const method of importMethods) {
    const sample = getImportSample(method.id);
    if (method.mode === "unavailable") {
      assert.equal(sample, null, method.id);
      continue;
    }
    assert.ok(sample, method.id + " should offer a format example");
    assert.ok(sample.downloadUrl.startsWith("/examples/"), method.id);
    assert.ok(sample.columns.length > 0 && sample.previewRows.length > 0, method.id);
    assert.ok(existsSync(new URL("../public" + sample.downloadUrl, import.meta.url)), method.id + ": sample must exist");
    if (method.mode === "excel" && method.id !== "excel") {
      assert.equal(sample.kind, "generic-example", method.id);
      assert.match(sample.notes, /NOT|not/i);
    }
  }
});

test("Entry upload requires Lock in and selecting a different source unlocks it", () => {
  const component = readFileSync(new URL("../src/components/dashboard/balance-import.tsx", import.meta.url), "utf8");
  const guide = readFileSync(new URL("../src/components/dashboard/import-sample-guide.tsx", import.meta.url), "utf8");
  assert.match(component, /lockedMethodId === methodId/);
  assert.match(component, /if \(!isLocked \|\| method\.mode === "unavailable"\)/);
  assert.match(component, /setLockedMethodId\(null\)/);
  assert.match(component, /sessionStorage\.removeItem\("flowvalue-import-locked"\)/);
  assert.match(component, /disabled=\{!isLocked \|\| method\.mode === "unavailable"\}/);
  assert.match(component, /isLocked && method\.mode !== "unavailable"/);
  assert.match(component, /<ImportSampleGuide/);
  assert.match(guide, /Download sample/);
  assert.match(guide, /Preview sample/);
  assert.match(guide, /Lock in selected source/);
});

test("JSON example is canonical and includes all required stream fields", () => {
  const data = JSON.parse(readFileSync(new URL("../public/examples/sample-streams.json", import.meta.url), "utf8"));
  assert.ok(Array.isArray(data.streams) && data.streams.length > 0);
  for (const stream of data.streams) {
    for (const key of ["stream_id", "mass_flow_kg_h", "temperature_c", "pressure_bar_abs", "phase"]) {
      assert.ok(Object.hasOwn(stream, key), key);
    }
  }
});
